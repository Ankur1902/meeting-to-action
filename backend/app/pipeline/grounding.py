"""
Deterministic evidence grounding.

Given a transcript and a quote the model claims to have copied from it,
locate the quote and score how faithful it is. Matching is whitespace- and
case-insensitive; if there is no exact hit we slide a window over the
transcript and take the best fuzzy ratio. A quote that cannot be found with
score >= threshold is treated as unsupported (a likely hallucination).
"""

import re
from difflib import SequenceMatcher
from typing import List, Tuple

from app.schemas.task import Evidence

_WS = re.compile(r"\s+")


def _normalize_with_map(text: str) -> Tuple[str, List[int]]:
    """Lowercase + collapse whitespace, keeping a map from normalized index to original index."""
    out: List[str] = []
    index_map: List[int] = []
    prev_space = True
    for i, ch in enumerate(text):
        if ch.isspace():
            if not prev_space:
                out.append(" ")
                index_map.append(i)
            prev_space = True
        else:
            out.append(ch.lower())
            index_map.append(i)
            prev_space = False
    return "".join(out).rstrip(), index_map


def locate_quote(transcript: str, quote: str, threshold: float = 0.8) -> Evidence:
    quote = (quote or "").strip()
    if not quote or not transcript:
        return Evidence(quote=quote, verified=False)

    norm_t, imap = _normalize_with_map(transcript)
    norm_q = _WS.sub(" ", quote.lower()).strip()
    if not norm_q:
        return Evidence(quote=quote, verified=False)

    idx = norm_t.find(norm_q)
    if idx != -1:
        end_norm = idx + len(norm_q) - 1
        return Evidence(
            quote=quote, start=imap[idx], end=imap[end_norm] + 1, score=1.0, verified=True
        )

    # Fuzzy: compare against windows of roughly the quote's length (a few length
    # variants, so insertions/deletions don't misalign the window).
    qlen = len(norm_q)
    step = max(1, qlen // 8)
    best_score, best_start, best_len = 0.0, -1, qlen
    for wlen in {max(1, int(qlen * f)) for f in (0.85, 1.0, 1.15)}:
        wlen = min(wlen, len(norm_t))
        for s in range(0, max(1, len(norm_t) - wlen + 1), step):
            score = SequenceMatcher(None, norm_q, norm_t[s : s + wlen], autojunk=False).ratio()
            if score > best_score:
                best_score, best_start, best_len = score, s, wlen
    if best_start == -1:
        return Evidence(quote=quote, verified=False)

    end_norm = min(best_start + best_len, len(norm_t)) - 1
    verified = best_score >= threshold
    return Evidence(
        quote=quote,
        start=imap[best_start] if verified else -1,
        end=imap[end_norm] + 1 if verified else -1,
        score=round(best_score, 3),
        verified=verified,
    )


_NAME_TOKEN = re.compile(r"[A-Za-z][A-Za-z'-]+")


def owner_in_transcript(owner: str, transcript: str) -> bool:
    """True if the owner (or any name token of it) is actually mentioned."""
    if not owner or owner.strip().lower() in {"unassigned", "everyone", "team", "all"}:
        return True
    lowered = transcript.lower()
    return any(tok.lower() in lowered for tok in _NAME_TOKEN.findall(owner) if len(tok) > 1)
