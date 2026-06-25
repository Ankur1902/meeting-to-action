"""
FastAPI application entrypoint.

Run with: uvicorn app.main:app --reload --port 8000
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.routes import extract

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.main")

settings = get_settings()

app = FastAPI(
    title="AI Meeting-to-Action Board API",
    description="Transforms meeting notes and transcripts into summaries and actionable tasks.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches anything that wasn't already turned into an HTTPException so
    the client always gets a clean JSON error instead of a raw traceback.
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok"}


app.include_router(extract.router)
