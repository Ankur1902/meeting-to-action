"""Small lexical-similarity helpers shared by dedupe, insights and evals."""

import re
from typing import Set

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "is", "are", "we", "will",
    "be", "it", "that", "this", "by", "with", "at", "as", "from", "needs", "need", "should",
}


def tokens(text: str) -> Set[str]:
    return {t for t in _TOKEN.findall(text.lower()) if t not in _STOP}


def jaccard(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)
