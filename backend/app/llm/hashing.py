"""
Deterministic, dependency-free text embedder (feature hashing of word
unigrams + bigrams). Used as the offline/test fallback and when no Gemini key
is configured, so cross-meeting memory still works (lexical rather than
semantic similarity).
"""

import hashlib
import math
import re
from typing import List

DIM = 512
_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "is", "are", "we", "will", "be", "it", "that", "this", "by"}


def embed_one(text: str) -> List[float]:
    tokens = [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]
    feats = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
    vec = [0.0] * DIM
    for f in feats:
        h = int(hashlib.md5(f.encode()).hexdigest(), 16)
        vec[h % DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed_many(texts: List[str]) -> List[List[float]]:
    return [embed_one(t) for t in texts]
