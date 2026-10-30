"""Dependency providers (overridable in tests via app.dependency_overrides)."""

from functools import lru_cache

from fastapi import Depends

from app.actions.service import ActionService
from app.core.config import Settings, get_settings
from app.llm.base import LLMClient
from app.llm.factory import build_llm
from app.memory.service import MemoryService
from app.memory.store import MemoryStore
from app.pipeline.runner import ExtractionPipeline


@lru_cache
def get_store() -> MemoryStore:
    return MemoryStore(get_settings().database_path)


@lru_cache
def get_llm() -> LLMClient:
    return build_llm(get_settings())


def get_pipeline(settings: Settings = Depends(get_settings), llm: LLMClient = Depends(get_llm)) -> ExtractionPipeline:
    return ExtractionPipeline(llm, settings)


def get_memory(store: MemoryStore = Depends(get_store), llm: LLMClient = Depends(get_llm)) -> MemoryService:
    return MemoryService(store, llm)


def get_actions(
    store: MemoryStore = Depends(get_store),
    llm: LLMClient = Depends(get_llm),
    settings: Settings = Depends(get_settings),
) -> ActionService:
    return ActionService(store, llm, settings)
