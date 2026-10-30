"""
Input guardrails: PII redaction and prompt-injection detection.

Transcripts are untrusted input that gets pasted into an LLM prompt and, later,
into the prompts that answer questions over memory. We (1) delimit them in the
prompt, and (2) flag instruction-like text so the UI can warn the user and the
extractor can be told to treat it as data.
"""

import re
from typing import List, Tuple

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d{1,2}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\w)")

_INJECTION_PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above) (instructions|prompts?)",
    r"disregard (all |any )?(the )?(previous|prior|above)",
    r"you are now\b",
    r"(reveal|print|show|output) (your )?(system )?prompt",
    r"new instructions?:",
    r"\bsystem prompt\b",
    r"act as (an? )?(?!project)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def redact_pii(text: str) -> Tuple[str, int]:
    count = 0

    def _sub(label: str):
        def inner(_m):
            nonlocal count
            count += 1
            return f"[{label}]"

        return inner

    text = _EMAIL.sub(_sub("EMAIL"), text)
    text = _PHONE.sub(_sub("PHONE"), text)
    return text, count


def detect_injection(text: str) -> List[str]:
    """Return the matched suspicious snippets (empty list = clean)."""
    return [m.group(0) for m in _INJECTION_RE.finditer(text)]


def clean_text(text: str) -> str:
    """Normalize line endings and strip control characters (keeps newlines/tabs)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "".join(ch for ch in text if ch in "\n\t" or ord(ch) >= 32).strip()
