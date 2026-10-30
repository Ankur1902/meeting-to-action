"""Human-in-the-loop agent action routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.actions.service import ActionService
from app.deps import get_actions, get_store
from app.memory.store import MemoryStore
from app.pipeline.errors import PipelineError

router = APIRouter(prefix="/api/actions", tags=["actions"])


def _http(exc: PipelineError) -> HTTPException:
    return HTTPException(exc.status_code, exc.message)


@router.post("/propose/{meeting_id}", status_code=201)
async def propose(meeting_id: str, actions: ActionService = Depends(get_actions)):
    """Agent drafts follow-up actions for a meeting. Nothing is executed yet."""
    try:
        return await actions.propose(meeting_id)
    except PipelineError as exc:
        raise _http(exc) from exc


@router.get("")
async def list_actions(status: Optional[str] = Query(default=None), store: MemoryStore = Depends(get_store)):
    return store.list_actions(status)


@router.post("/{action_id}/approve")
async def approve(action_id: str, actions: ActionService = Depends(get_actions)):
    try:
        return await actions.approve(action_id)
    except PipelineError as exc:
        raise _http(exc) from exc


@router.post("/{action_id}/reject")
async def reject(action_id: str, actions: ActionService = Depends(get_actions)):
    try:
        return actions.reject(action_id)
    except PipelineError as exc:
        raise _http(exc) from exc
