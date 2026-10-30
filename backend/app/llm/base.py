"""
Provider-agnostic LLM interface.

The pipeline, Q&A and action drafting only depend on this protocol, which
keeps them unit-testable with a fake and lets the eval harness swap models
(or an offline baseline) without touching application code.
"""

from dataclasses import dataclass
from typing import List, Protocol


@dataclass
class LLMResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMClient(Protocol):
    model: str

    async def generate(self, prompt: str, *, json_mode: bool = False) -> LLMResult: ...

    async def embed(self, texts: List[str]) -> List[List[float]]: ...


class LLMUnavailable(RuntimeError):
    """Raised when the LLM is not configured or the provider call failed."""
