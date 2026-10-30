"""
FastAPI application entrypoint.

Run with: uvicorn app.main:app --reload --port 8000
"""

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.security import RateLimiter
from app.observability.metrics import log_request, metrics, new_request_id
from app.routes import actions, extract, memory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.main")

settings = get_settings()

app = FastAPI(
    title="Minutes → Action API",
    description="Grounded meeting intelligence: cited task extraction, cross-meeting memory and approval-gated agent actions.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

_limiter = RateLimiter(settings.rate_limit_per_minute)


@app.middleware("http")
async def guard_and_observe(request: Request, call_next):
    request_id = new_request_id()
    started = time.perf_counter()
    path = request.url.path

    if path.startswith("/api/") and request.method != "OPTIONS":
        s = request.app.dependency_overrides.get(get_settings, get_settings)()
        if s.api_key and request.headers.get("x-api-key") != s.api_key:
            response = JSONResponse(status_code=401, content={"detail": "Invalid or missing API key."})
        elif not _limiter.allow(request.client.host if request.client else "unknown"):
            metrics.rate_limited += 1
            response = JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again shortly."})
        else:
            response = await call_next(request)
    else:
        response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    route = request.scope.get("route")
    ms = log_request(request_id, request.method, path, response.status_code, started)
    metrics.observe(getattr(route, "path", path), response.status_code, ms)
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred. Please try again."})


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok"}


@app.get("/api/metrics", tags=["health"])
async def get_metrics() -> dict:
    return metrics.snapshot()


app.include_router(extract.router)
app.include_router(memory.router)
app.include_router(actions.router)
