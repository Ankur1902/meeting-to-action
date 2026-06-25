"""
Gemini integration service.

Encapsulates everything related to talking to the Gemini API: building the
model client, sending the extraction prompt, and — critically — defensively
parsing the response into the JSON shape the rest of the app expects.
LLMs occasionally wrap JSON in markdown fences or add stray whitespace/
prose even when instructed not to, so parsing here is deliberately
tolerant before giving up and raising a clear error.
"""

import json
import logging
import re
from typing import Any, Dict

from google import genai
from google.genai import types
from google.genai.errors import APIError
from fastapi import HTTPException

from app.core.config import Settings
from app.core.prompts import build_extraction_prompt

logger = logging.getLogger("app.gemini")

_JSON_FENCE_PATTERN = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")


def _strip_code_fences(text: str) -> str:
    """Strips ```json ... ``` or ``` ... ``` fences if the model added them."""
    match = _JSON_FENCE_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def _parse_gemini_json(raw_text: str) -> Dict[str, Any]:
    cleaned = _strip_code_fences(raw_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        # Last resort: try to find the outermost {...} block in case there's
        # leading/trailing prose the model added despite instructions.
        brace_match = re.search(r"\{[\s\S]*\}", cleaned)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass
        logger.error("Failed to parse Gemini response as JSON: %s", raw_text[:500])
        raise HTTPException(
            status_code=502,
            detail="AI response could not be parsed. Please try again.",
        ) from exc


def _normalize_response(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fills in safe defaults for any missing keys so a partially-formed
    Gemini response still produces a usable result instead of a 500 error.
    """
    executive_summary = parsed.get("executiveSummary") or "No summary available."
    key_decisions = parsed.get("keyDecisions") or []
    raw_tasks = parsed.get("tasks") or []

    normalized_tasks = []
    valid_priorities = {"High", "Medium", "Low"}
    for raw_task in raw_tasks:
        if not isinstance(raw_task, dict):
            continue
        priority = raw_task.get("priority")
        if priority not in valid_priorities:
            priority = "Medium"
        normalized_tasks.append(
            {
                "task": str(raw_task.get("task", "")).strip() or "Untitled task",
                "owner": str(raw_task.get("owner", "")).strip() or "Unassigned",
                "deadline": str(raw_task.get("deadline", "")).strip() or "No deadline",
                "priority": priority,
                "status": "todo",
            }
        )

    return {
        "summary": {
            "executiveSummary": executive_summary,
            "keyDecisions": key_decisions,
        },
        "tasks": normalized_tasks,
    }


class GeminiService:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def extract_summary_and_tasks(self, source_text: str) -> Dict[str, Any]:
        """
        Sends meeting text to Gemini and returns a normalized dict:
        { summary: { executiveSummary, keyDecisions }, tasks: [...] }
        """
        prompt = build_extraction_prompt(source_text)

        try:
            response = await self._client.aio.models.generate_content(
                model=self._settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )
        except APIError as exc:
            # Raised for invalid/missing API keys, unknown model names, quota
            # errors, etc. — exc.message is the API's own explanation.
            logger.exception("Gemini API call failed: %s", exc.message)
            raise HTTPException(
                status_code=502,
                detail=f"AI service error: {exc.message}",
            ) from exc
        except Exception as exc:  # noqa: BLE001 — network errors, timeouts, etc.
            logger.exception("Gemini API call failed")
            raise HTTPException(
                status_code=502,
                detail="Failed to reach the AI service. Please check your API key and try again.",
            ) from exc

        try:
            raw_text = (response.text or "").strip()
        except Exception as exc:  # noqa: BLE001 — the SDK's .text accessor raises if
            # the response has no plain-text part (e.g. blocked by safety
            # filters, or the model returned only a function call/empty
            # candidate). Surface a clear, actionable message instead of a
            # raw 500.
            logger.exception("Could not read text from Gemini response")
            raise HTTPException(
                status_code=502,
                detail=(
                    "The AI couldn't produce a usable response for this input "
                    "(it may have been flagged by safety filters). Try rephrasing "
                    "your notes."
                ),
            ) from exc

        if not raw_text:
            raise HTTPException(
                status_code=502,
                detail="AI service returned an empty response. Please try again.",
            )

        parsed = _parse_gemini_json(raw_text)
        return _normalize_response(parsed)
