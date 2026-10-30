"""
Extraction routes.

- POST /api/extract         — JSON body for pasted notes
- POST /api/extract/upload  — multipart TXT/PDF upload
- POST /api/extract/stream  — same as /api/extract but streams pipeline steps (SSE)

All run the traced, grounded pipeline and (unless ``persist`` is false) store
the meeting in cross-meeting memory.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.deps import get_memory, get_pipeline
from app.memory.service import MemoryService
from app.pipeline.errors import PipelineError
from app.pipeline.runner import ExtractionPipeline
from app.schemas.extract import ExtractRequest, ExtractResponse
from app.services.file_service import extract_text_from_upload

logger = logging.getLogger("app.routes.extract")

router = APIRouter(prefix="/api", tags=["extract"])


def _http(exc: PipelineError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


async def _run_and_store(
    pipeline: ExtractionPipeline,
    memory: MemoryService,
    text: str,
    title: Optional[str],
    meeting_date: Optional[str],
    persist: bool,
) -> ExtractResponse:
    try:
        final = await pipeline.run(text, meeting_date)
        response: ExtractResponse = final["data"]
        if persist:
            response.meeting_id = await memory.ingest(
                title=title or "Untitled meeting",
                meeting_date=final["meetingDate"],
                transcript=final["transcript"],
                response=response,
            )
    except PipelineError as exc:
        raise _http(exc) from exc
    return response


@router.post("/extract", response_model=ExtractResponse, response_model_by_alias=True)
async def extract_from_text(
    payload: ExtractRequest,
    pipeline: ExtractionPipeline = Depends(get_pipeline),
    memory: MemoryService = Depends(get_memory),
) -> ExtractResponse:
    """Generate a grounded summary and task list from pasted meeting notes."""
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Meeting notes text cannot be empty.")
    return await _run_and_store(pipeline, memory, payload.text, payload.title, payload.meeting_date, payload.persist)


@router.post("/extract/upload", response_model=ExtractResponse, response_model_by_alias=True)
async def extract_from_upload(
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    meeting_date: Optional[str] = Form(default=None),
    settings: Settings = Depends(get_settings),
    pipeline: ExtractionPipeline = Depends(get_pipeline),
    memory: MemoryService = Depends(get_memory),
) -> ExtractResponse:
    """Generate a grounded summary and task list from an uploaded TXT/PDF transcript."""
    extracted_text = await extract_text_from_upload(file, settings.max_upload_size_bytes)
    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from this file.")
    return await _run_and_store(pipeline, memory, extracted_text, title or file.filename, meeting_date, True)


@router.post("/extract/stream")
async def extract_stream(
    payload: ExtractRequest,
    pipeline: ExtractionPipeline = Depends(get_pipeline),
    memory: MemoryService = Depends(get_memory),
) -> StreamingResponse:
    """Server-sent events: one `step` event per pipeline stage, then `result` (or `error`)."""
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Meeting notes text cannot be empty.")

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    async def gen():
        try:
            async for ev in pipeline.run_stream(payload.text, payload.meeting_date):
                if ev["event"] == "step":
                    yield sse("step", ev["data"])
                else:
                    response: ExtractResponse = ev["data"]
                    if payload.persist:
                        response.meeting_id = await memory.ingest(
                            title=payload.title or "Untitled meeting",
                            meeting_date=ev["meetingDate"],
                            transcript=ev["transcript"],
                            response=response,
                        )
                    yield sse("result", response.model_dump(by_alias=True, mode="json"))
        except PipelineError as exc:
            yield sse("error", {"detail": exc.message, "status": exc.status_code})

    return StreamingResponse(gen(), media_type="text/event-stream")
