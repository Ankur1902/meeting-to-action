"""Tolerant JSON parsing for LLM output (fences, stray prose)."""

import json
import re
from typing import Any, Dict

_JSON_FENCE_PATTERN = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")


def strip_code_fences(text: str) -> str:
    match = _JSON_FENCE_PATTERN.search(text)
    return match.group(1).strip() if match else text.strip()


def parse_json_object(raw_text: str) -> Dict[str, Any]:
    """Parse a JSON object or raise ValueError."""
    cleaned = strip_code_fences(raw_text)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        brace = re.search(r"\{[\s\S]*\}", cleaned)
        if not brace:
            raise ValueError("no JSON object found in model output") from None
        try:
            value = json.loads(brace.group(0))
        except json.JSONDecodeError as exc:
            raise ValueError(str(exc)) from exc
    if not isinstance(value, dict):
        raise ValueError("model output is not a JSON object")
    return value
