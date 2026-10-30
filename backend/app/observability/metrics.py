"""
Request logging + in-memory metrics.

Every request gets an X-Request-ID, a structured log line with latency, and
is counted in a tiny Prometheus-style registry exposed at /api/metrics. This
is deliberately dependency-free; point an OTLP/Langfuse exporter at the same
pipeline trace data if you need hosted tracing.
"""

import logging
import time
import uuid
from collections import defaultdict
from typing import Dict, List

logger = logging.getLogger("app.request")


class Metrics:
    def __init__(self) -> None:
        self.requests: Dict[str, int] = defaultdict(int)
        self.latencies_ms: Dict[str, List[float]] = defaultdict(list)
        self.rate_limited = 0

    def observe(self, route: str, status: int, ms: float) -> None:
        self.requests[f"{route}|{status}"] += 1
        bucket = self.latencies_ms[route]
        bucket.append(ms)
        if len(bucket) > 1000:
            del bucket[:500]

    def snapshot(self) -> Dict:
        def pct(vals: List[float], p: float) -> float:
            if not vals:
                return 0.0
            vals = sorted(vals)
            return round(vals[min(len(vals) - 1, int(p * len(vals)))], 2)

        return {
            "requests": dict(self.requests),
            "latencyMs": {r: {"p50": pct(v, 0.5), "p95": pct(v, 0.95), "count": len(v)} for r, v in self.latencies_ms.items()},
            "rateLimited": self.rate_limited,
        }


metrics = Metrics()


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def log_request(request_id: str, method: str, path: str, status: int, started: float) -> float:
    ms = (time.perf_counter() - started) * 1000
    logger.info("request_id=%s method=%s path=%s status=%s latency_ms=%.1f", request_id, method, path, status, ms)
    return ms
