"""
Offline demo server: the real API with an in-memory database and a rule-based
stand-in for Gemini, so the full product (grounding, memory, insights,
approval-gated actions) can be shown without an API key.

    uvicorn demo_server:app --port 8000
"""

import json
import re

from app import deps
from app.llm.base import LLMResult
from app.main import app
from app.memory.store import MemoryStore
from evals.baseline import RuleBasedLLM


class DemoLLM(RuleBasedLLM):
    model = "demo-rules"

    async def generate(self, prompt: str, *, json_mode: bool = False) -> LLMResult:
        if "using ONLY the numbered sources" in prompt:
            first = re.search(r"\[1\] \(([^)]*)\) (.*)", prompt)
            meta, text = (first.group(1), first.group(2)) if first else ("", "")
            text = re.sub(r"^[A-Z][A-Za-z]+:\s*", "", text)
            return LLMResult(text=f"In {meta.split(',')[0]}: \"{text}\" [1]")
        if "follow-up email" in prompt:
            return LLMResult(text=json.dumps({
                "subject": "Follow-up: 4.2 release sync",
                "body": "Hi all,\n\nThanks for the sync. The feature list is frozen for 4.2. Please see the action items on the board and shout if anything is blocked.\n\nBest",
            }))
        return await super().generate(prompt, json_mode=json_mode)


_store = MemoryStore(":memory:")
_llm = DemoLLM()
app.dependency_overrides[deps.get_store] = lambda: _store
app.dependency_overrides[deps.get_llm] = lambda: _llm
