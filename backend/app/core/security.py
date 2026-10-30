"""Optional API-key auth and a per-IP sliding-window rate limiter."""

import time
from collections import defaultdict, deque
from typing import Deque, Dict


class RateLimiter:
    def __init__(self, per_minute: int):
        self._limit = per_minute
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        if self._limit <= 0:
            return True
        now = time.monotonic() if now is None else now
        window = self._hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self._limit:
            return False
        window.append(now)
        return True
