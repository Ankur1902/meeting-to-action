"""
Multi-step, traced extraction pipeline:

    clean -> extract -> ground -> verify -> resolve

Each step is timed and emitted as an event, so the same code powers the
blocking endpoint (collect everything) and the SSE endpoint (stream steps as
they finish). Quotes returned by the model are located in the transcript
(``grounding``); items whose quote cannot be found are flagged, not silently
trusted.
"""

import logging
import time
from datetime import date
from typing import Any, AsyncIterator, Dict, List, Optional

from app.core.config import Settings
from app.llm.base import LLMClient, LLMUnavailable
from app.pipeline import grounding, guardrails
from app.pipeline.errors import PipelineError
from app.pipeline.parsing import parse_json_object
from app.pipeline.prompts import EXTRACTION_PROMPT, REPAIR_PROMPT, VERIFIER_PROMPT
from app.pipeline.textsim import jaccard
from app.schemas.extract import Decision, ExtractResponse, Summary, TraceStep
from app.schemas.task import Evidence, Priority, Task

logger = logging.getLogger("app.pipeline")

_VALID_PRIORITIES = {p.value for p in Priority}
_DEDUPE_THRESHOLD = 0.8


def _iso_or_none(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip()).isoformat()
    except ValueError:
        return None


class ExtractionPipeline:
    def __init__(self, llm: LLMClient, settings: Settings):
        self._llm = llm
        self._settings = settings

    # -- steps ---------------------------------------------------------

    async def _extract(self, transcript: str, meeting_date: str) -> Dict[str, Any]:
        prompt = EXTRACTION_PROMPT.format(meeting_date=meeting_date, transcript=transcript)
        try:
            result = await self._llm.generate(prompt, json_mode=True)
            if not result.text:
                raise PipelineError("AI service returned an empty response. Please try again.")
            try:
                return parse_json_object(result.text)
            except ValueError as first_error:
                logger.warning("Extraction JSON invalid (%s); attempting repair", first_error)
                repaired = await self._llm.generate(
                    REPAIR_PROMPT.format(error=first_error, raw=result.text[:6000]), json_mode=True
                )
                try:
                    return parse_json_object(repaired.text)
                except ValueError as exc:
                    raise PipelineError("AI response could not be parsed. Please try again.") from exc
        except LLMUnavailable as exc:
            raise PipelineError(str(exc), 503 if "not configured" in str(exc) else 502) from exc

    def _build_tasks(self, parsed: Dict[str, Any], transcript: str) -> List[Task]:
        tasks: List[Task] = []
        for raw in parsed.get("tasks") or []:
            if not isinstance(raw, dict):
                continue
            priority = raw.get("priority")
            evidence = grounding.locate_quote(
                transcript, str(raw.get("quote") or ""), self._settings.grounding_threshold
            )
            owner = str(raw.get("owner", "")).strip() or "Unassigned"
            tasks.append(
                Task(
                    task=str(raw.get("task", "")).strip() or "Untitled task",
                    owner=owner,
                    deadline=str(raw.get("deadline", "")).strip() or "No deadline",
                    due_date=_iso_or_none(raw.get("dueDate")),
                    priority=priority if priority in _VALID_PRIORITIES else Priority.MEDIUM,
                    evidence=evidence,
                    supported=evidence.verified,
                )
            )
        return tasks

    async def _verify(self, tasks: List[Task], transcript: str) -> int:
        """Owner check (deterministic) + optional LLM entailment check. Returns #flagged."""
        flagged = 0
        for t in tasks:
            if not grounding.owner_in_transcript(t.owner, transcript):
                t.supported = False
            if self._settings.enable_llm_verifier and t.supported and t.evidence:
                try:
                    res = await self._llm.generate(
                        VERIFIER_PROMPT.format(task=t.task, owner=t.owner, quote=t.evidence.quote),
                        json_mode=True,
                    )
                    verdict = parse_json_object(res.text)
                    if verdict.get("supported") is False:
                        t.supported = False
                except (LLMUnavailable, ValueError):
                    logger.warning("LLM verifier failed for task %s; keeping deterministic result", t.id)
            ev_score = t.evidence.score if t.evidence else 0.0
            t.confidence = round(ev_score if t.supported else min(ev_score, 0.4), 3)
            if not t.supported:
                flagged += 1
        return flagged

    @staticmethod
    def _resolve(tasks: List[Task]) -> List[Task]:
        """Drop near-duplicate tasks within one meeting (same owner, very similar text)."""
        kept: List[Task] = []
        for t in tasks:
            dup = any(
                k.owner.lower() == t.owner.lower() and jaccard(k.task, t.task) >= _DEDUPE_THRESHOLD
                for k in kept
            )
            if not dup:
                kept.append(t)
        return kept

    # -- orchestration -------------------------------------------------

    async def run_stream(
        self, text: str, meeting_date: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        steps: List[TraceStep] = []
        warnings: List[str] = []

        def step_event(name: str, started: float, detail: str = "") -> Dict[str, Any]:
            step = TraceStep(step=name, duration_ms=round((time.perf_counter() - started) * 1000, 2), detail=detail)
            steps.append(step)
            return {"event": "step", "data": step.model_dump(by_alias=True)}

        # 1. clean
        t0 = time.perf_counter()
        transcript = guardrails.clean_text(text)
        if not transcript:
            raise PipelineError("Meeting notes text cannot be empty.", 400)
        injections = guardrails.detect_injection(transcript)
        if injections:
            warnings.append(
                "Possible prompt-injection text detected in the transcript; it was treated as data only."
            )
        redacted = 0
        if self._settings.redact_pii:
            transcript, redacted = guardrails.redact_pii(transcript)
        if redacted:
            warnings.append(f"Redacted {redacted} email/phone value(s) before processing.")
        yield step_event("clean", t0, f"{len(transcript)} chars, {redacted} redacted, {len(injections)} injection flags")

        # 2. extract
        iso_date = _iso_or_none(meeting_date) or date.today().isoformat()
        t0 = time.perf_counter()
        parsed = await self._extract(transcript, iso_date)
        yield step_event("extract", t0, f"model={self._llm.model}")

        # 3. ground
        t0 = time.perf_counter()
        tasks = self._build_tasks(parsed, transcript)
        decisions: List[Decision] = []
        for raw in parsed.get("decisions") or []:
            if isinstance(raw, dict) and str(raw.get("text", "")).strip():
                ev = grounding.locate_quote(transcript, str(raw.get("quote") or ""), self._settings.grounding_threshold)
                decisions.append(Decision(text=str(raw["text"]).strip(), evidence=ev))
            elif isinstance(raw, str) and raw.strip():
                decisions.append(Decision(text=raw.strip()))
        grounded = sum(1 for t in tasks if t.supported)
        yield step_event("ground", t0, f"{grounded}/{len(tasks)} tasks have verified quotes")

        # 4. verify
        t0 = time.perf_counter()
        flagged = await self._verify(tasks, transcript)
        yield step_event("verify", t0, f"{flagged} flagged")

        # 5. resolve
        t0 = time.perf_counter()
        before = len(tasks)
        tasks = self._resolve(tasks)
        yield step_event("resolve", t0, f"{before - len(tasks)} duplicate(s) removed")

        if flagged:
            warnings.append(f"{flagged} task(s) could not be verified against the transcript.")

        summary = Summary(
            executive_summary=str(parsed.get("executiveSummary") or "No summary available."),
            key_decisions=[d.text for d in decisions],
            decisions=decisions,
        )
        response = ExtractResponse(summary=summary, tasks=tasks, warnings=warnings, trace=steps)
        yield {"event": "result", "data": response, "transcript": transcript, "meetingDate": iso_date}

    async def run(self, text: str, meeting_date: Optional[str] = None) -> Dict[str, Any]:
        """Run to completion; returns the final 'result' event."""
        final: Dict[str, Any] = {}
        async for event in self.run_stream(text, meeting_date):
            if event["event"] == "result":
                final = event
        return final
