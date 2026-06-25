"""
/api/extract routes.

Two entry points, both producing the same ExtractResponse shape:
- POST /api/extract        — JSON body { "text": "..." } for pasted notes
- POST /api/extract/upload — multipart file upload for TXT/PDF transcripts

Keeping them as separate endpoints (rather than one polymorphic endpoint)
keeps each handler simple and keeps the OpenAPI schema honest about what
each one accepts.
"""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.schemas.extract import ExtractRequest, ExtractResponse
from app.services.file_service import extract_text_from_upload
from app.services.gemini_service import GeminiService

logger = logging.getLogger("app.routes.extract")

router = APIRouter(prefix="/api", tags=["extract"])


def get_gemini_service(settings: Settings = Depends(get_settings)) -> GeminiService:
    return GeminiService(settings)


def _validate_extract_response(result: dict) -> ExtractResponse:
    """
    Validates the Gemini service's output against the response schema.
    Wrapped separately so a malformed AI response (e.g. a key decision
    that isn't a plain string) surfaces as a clean 502 instead of an
    unhandled 500 — the shape of LLM output isn't fully guaranteed even
    after our own normalization.
    """
    try:
        return ExtractResponse.model_validate(result)
    except ValidationError as exc:
        logger.error("AI response failed schema validation: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="AI returned data in an unexpected format. Please try again.",
        ) from exc


@router.post("/extract", response_model=ExtractResponse)
async def extract_from_text(
    payload: ExtractRequest,
    gemini_service: GeminiService = Depends(get_gemini_service),
) -> ExtractResponse:
    """Generate a summary and task list from pasted meeting notes."""
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Meeting notes text cannot be empty.")

    result = await gemini_service.extract_summary_and_tasks(text)
    return _validate_extract_response(result)


@router.post("/extract/upload", response_model=ExtractResponse)
async def extract_from_upload(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    gemini_service: GeminiService = Depends(get_gemini_service),
) -> ExtractResponse:
    """Generate a summary and task list from an uploaded TXT/PDF transcript."""
    extracted_text = await extract_text_from_upload(file, settings.max_upload_size_bytes)

    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from this file.")

    result = await gemini_service.extract_summary_and_tasks(extracted_text)
    return _validate_extract_response(result)
