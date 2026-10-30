"""
Offline rule-based baseline implementing the LLMClient protocol.

It reads the transcript out of the extraction prompt and applies regex rules
("<Name> will ... by <day>"), emitting JSON in the same schema as the real
model. It exists to (1) give the eval harness something deterministic to score
in CI without an API key and (2) set a floor that LLMs should clearly beat.
"""

import json
import re
from datetime import date, timedelta
from typing import List

from app.llm.base import LLMResult

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_NOT_NAMES = {"We", "I", "It", "The", "This", "That", "There", "Everyone", "Someone", "Team", "And", "Also", "Lastly", "Now", "So", "Okay", "Yes", "Great", "Sure", "Tomorrow", "Today", "To"}
_VERB = r"(?:will|to|should|needs to|need to|has to|is going to|can you|please|'ll)"
_OWNER_RE = re.compile(rf"\b([A-Z][a-z]+),? (?:{_VERB}) (.+)")
_SELF_RE = re.compile(r"\bI(?:'ll| will) (.+)")
_DEADLINE_RE = re.compile(
    r"\b(?:by|before|on|until)?\s*((?:next |this )?(?:monday|tuesday|wednesday|thursday|friday)|tomorrow|next week|this week|end of (?:the )?(?:day|month|week)|end of day|immediately|Q[1-4])\b",
    re.IGNORECASE,
)
_HIGH = re.compile(r"urgent|asap|critical|immediately|blocking|blocker", re.IGNORECASE)
_LOW = re.compile(r"low priority|nice to have|whenever|eventually", re.IGNORECASE)
_DECISION = re.compile(r"\b(?:we decided|decided to|we agreed|agreed to)\b", re.IGNORECASE)
_SPEAKER = re.compile(r"^([A-Z][A-Za-z ]{0,20}):\s*")
_INJECT = re.compile(r"ignore (?:all )?previous instructions|you are now|system prompt", re.IGNORECASE)
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _resolve_due(deadline: str, meeting_date: date):
    d = deadline.lower().strip()
    if d == "tomorrow":
        return (meeting_date + timedelta(days=1)).isoformat()
    for i, name in enumerate(_WEEKDAYS):
        if name in d:
            delta = (i - meeting_date.weekday()) % 7 or 7
            if d.startswith("next "):
                delta += 7 if delta < 7 else 0
            return (meeting_date + timedelta(days=delta)).isoformat()
    return None


class RuleBasedLLM:
    model = "baseline-rules"

    async def generate(self, prompt: str, *, json_mode: bool = False) -> LLMResult:
        m = re.search(r"<transcript>\n(.*)\n</transcript>", prompt, re.DOTALL)
        text = m.group(1) if m else prompt
        dm = re.search(r"meeting date\) is (\d{4}-\d{2}-\d{2})", prompt)
        meeting_date = date.fromisoformat(dm.group(1)) if dm else date.today()

        tasks, decisions = [], []
        for line in text.split("\n"):
            speaker_m = _SPEAKER.match(line)
            speaker = speaker_m.group(1).strip() if speaker_m else None
            body = line[speaker_m.end():] if speaker_m else line
            for sentence in _SENT_SPLIT.split(body):
                sentence = sentence.strip()
                if not sentence or _INJECT.search(sentence):
                    continue
                if _DECISION.search(sentence):
                    decisions.append({"text": sentence.rstrip("."), "quote": sentence})
                    continue
                owner, action = None, None
                mo = _OWNER_RE.search(sentence)
                if mo and mo.group(1) not in _NOT_NAMES:
                    owner, action = mo.group(1), mo.group(2)
                else:
                    ms = _SELF_RE.search(sentence)
                    if ms and speaker:
                        owner, action = speaker, ms.group(1)
                if not action:
                    continue
                dl = _DEADLINE_RE.search(sentence)
                deadline = dl.group(1) if dl else "No deadline"
                clean = _DEADLINE_RE.sub("", action).strip(" ,.")
                clean = re.split(r",\s*(?:it'?s|this is|but)\b", clean)[0].strip(" ,.")
                tasks.append({
                    "task": clean,
                    "owner": owner,
                    "deadline": deadline,
                    "dueDate": _resolve_due(deadline, meeting_date) if dl else None,
                    "priority": "High" if _HIGH.search(sentence) else "Low" if _LOW.search(sentence) else "Medium",
                    "quote": sentence,
                })
        out = {
            "executiveSummary": f"Meeting with {len(tasks)} action item(s) and {len(decisions)} decision(s).",
            "decisions": decisions,
            "tasks": tasks,
        }
        return LLMResult(text=json.dumps(out), input_tokens=len(prompt) // 4, output_tokens=len(json.dumps(out)) // 4)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        from app.llm import hashing

        return hashing.embed_many(texts)
