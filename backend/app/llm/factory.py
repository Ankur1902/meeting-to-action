"""Builds the configured LLMClient; falls back to hashing embeddings when needed."""

from typing import List, Optional

from app.core.config import Settings
from app.llm import hashing
from app.llm.base import LLMClient, LLMResult, LLMUnavailable
from app.llm.gemini import GeminiClient


class NoLLMClient:
    """Placeholder used when no API key is set: generation fails clearly,
    embeddings still work through the offline hashing embedder."""

    model = "none"

    async def generate(self, prompt: str, *, json_mode: bool = False) -> LLMResult:
        raise LLMUnavailable("GEMINI_API_KEY is not configured on the server.")

    async def embed(self, texts: List[str]) -> List[List[float]]:
        return hashing.embed_many(texts)


def build_llm(settings: Settings, model: Optional[str] = None) -> LLMClient:
    if not settings.gemini_api_key:
        return NoLLMClient()
    return GeminiClient(settings.gemini_api_key, model or settings.gemini_model, settings.embedding_model)
