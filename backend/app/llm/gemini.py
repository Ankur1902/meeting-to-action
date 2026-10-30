"""Gemini implementation of the LLMClient protocol."""

import logging
from typing import List

from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.llm.base import LLMResult, LLMUnavailable

logger = logging.getLogger("app.llm.gemini")


class GeminiClient:
    def __init__(self, api_key: str, model: str, embedding_model: str):
        if not api_key:
            raise LLMUnavailable("GEMINI_API_KEY is not configured.")
        self.model = model
        self._embedding_model = embedding_model
        self._client = genai.Client(api_key=api_key)

    async def generate(self, prompt: str, *, json_mode: bool = False) -> LLMResult:
        config = types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json" if json_mode else None,
        )
        try:
            response = await self._client.aio.models.generate_content(
                model=self.model, contents=prompt, config=config
            )
        except APIError as exc:
            logger.exception("Gemini API call failed: %s", exc.message)
            raise LLMUnavailable(f"AI service error: {exc.message}") from exc
        except Exception as exc:  # noqa: BLE001 — network errors, timeouts, etc.
            logger.exception("Gemini API call failed")
            raise LLMUnavailable(
                "Failed to reach the AI service. Please check your API key and try again."
            ) from exc

        try:
            text = (response.text or "").strip()
        except Exception as exc:  # noqa: BLE001 — .text raises on blocked/empty candidates
            raise LLMUnavailable(
                "The AI couldn't produce a usable response for this input "
                "(it may have been flagged by safety filters)."
            ) from exc

        usage = getattr(response, "usage_metadata", None)
        return LLMResult(
            text=text,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
        )

    async def embed(self, texts: List[str]) -> List[List[float]]:
        try:
            response = await self._client.aio.models.embed_content(
                model=self._embedding_model, contents=texts
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Gemini embedding call failed")
            raise LLMUnavailable("Embedding service failed.") from exc
        return [list(e.values) for e in response.embeddings]
