"""Cross-meeting memory routes: list meetings, ask questions, insights, task status."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.deps import get_memory
from app.memory.service import MemoryService
from app.pipeline.errors import PipelineError
from app.schemas.task import TaskStatus

router = APIRouter(prefix="/api/memory", tags=["memory"])


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    top_k: int = Field(default=5, ge=1, le=10, alias="topK")

    model_config = {"populate_by_name": True}


class StatusUpdate(BaseModel):
    status: TaskStatus


@router.get("/meetings")
async def list_meetings(memory: MemoryService = Depends(get_memory)):
    return memory.store.list_meetings()


@router.get("/meetings/{meeting_id}")
async def get_meeting(meeting_id: str, memory: MemoryService = Depends(get_memory)):
    meeting = memory.store.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(404, "Meeting not found.")
    return meeting


@router.delete("/meetings/{meeting_id}", status_code=204)
async def delete_meeting(meeting_id: str, memory: MemoryService = Depends(get_memory)):
    if not memory.store.delete_meeting(meeting_id):
        raise HTTPException(404, "Meeting not found.")


@router.post("/ask")
async def ask(payload: AskRequest, memory: MemoryService = Depends(get_memory)):
    """Answer a question over all stored meetings, with numbered source citations."""
    try:
        return await memory.ask(payload.question, payload.top_k)
    except PipelineError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc


@router.get("/tasks")
async def list_tasks(status: Optional[TaskStatus] = Query(default=None), memory: MemoryService = Depends(get_memory)):
    return memory.store.list_tasks(status=status.value if status else None)


@router.patch("/tasks/{task_id}")
async def update_task(task_id: str, payload: StatusUpdate, memory: MemoryService = Depends(get_memory)):
    if not memory.store.update_task_status(task_id, payload.status.value):
        raise HTTPException(404, "Task not found.")
    return {"id": task_id, "status": payload.status.value}


@router.get("/insights")
async def insights(today: Optional[date] = None, memory: MemoryService = Depends(get_memory)):
    """Overdue carry-overs, duplicate tasks and conflicting tasks across meetings."""
    return memory.insights(today)
