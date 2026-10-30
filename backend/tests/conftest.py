import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import Settings  # noqa: E402
from app.llm import hashing  # noqa: E402
from app.llm.base import LLMResult  # noqa: E402


class FakeLLM:
    """Scripted LLM: returns queued responses (or a callable's output) in order."""

    model = "fake"

    def __init__(self, responses=None, default=None):
        self.responses = list(responses or [])
        self.default = default
        self.prompts = []

    async def generate(self, prompt, *, json_mode=False):
        self.prompts.append(prompt)
        if self.responses:
            item = self.responses.pop(0)
        elif self.default is not None:
            item = self.default
        else:
            raise AssertionError("FakeLLM ran out of responses")
        if callable(item):
            item = item(prompt)
        if not isinstance(item, str):
            item = json.dumps(item)
        return LLMResult(text=item, input_tokens=10, output_tokens=5)

    async def embed(self, texts):
        return hashing.embed_many(texts)


@pytest.fixture
def settings():
    return Settings(gemini_api_key="x", database_path=":memory:", rate_limit_per_minute=0)


TRANSCRIPT = (
    "Priya: Thanks everyone. First item is the checkout bug.\n"
    "Marcus: I'll fix the checkout bug by Wednesday, it's blocking the release.\n"
    "Priya: We decided to freeze the feature list.\n"
    "Dana: I'll update the release notes by Thursday."
)

GOOD_RESPONSE = {
    "executiveSummary": "Sprint sync.",
    "decisions": [{"text": "Freeze the feature list", "quote": "We decided to freeze the feature list."}],
    "tasks": [
        {"task": "Fix the checkout bug", "owner": "Marcus", "deadline": "Wednesday", "dueDate": "2026-03-04",
         "priority": "High", "quote": "I'll fix the checkout bug by Wednesday"},
        {"task": "Update the release notes", "owner": "Dana", "deadline": "Thursday", "dueDate": None,
         "priority": "Medium", "quote": "I'll update the release notes by Thursday."},
    ],
}
