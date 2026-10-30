"""
Application configuration.

Centralizes all environment-driven settings so the rest of the codebase
never touches os.environ directly. The Gemini key is optional at startup so
the app (and the offline eval/test suites) can run without one; any code
path that actually needs the LLM raises a clear 503 instead.
"""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True)

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "gemini-embedding-001"
    allowed_origins: str = "http://localhost:3000"
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10MB

    # Persistence (SQLite file; ":memory:" is used by tests)
    database_path: str = "data/meetings.db"

    # Grounding / verification
    grounding_threshold: float = 0.8  # min fuzzy-match score for a quote to count as found
    enable_llm_verifier: bool = False  # extra LLM pass that checks quote supports the task
    redact_pii: bool = True  # redact emails/phones before text is stored or embedded

    # Security / abuse protection
    api_key: str = ""  # if set, /api/* requires header X-API-Key
    rate_limit_per_minute: int = 60  # per client IP; 0 disables

    # Agent actions (all executed only after explicit human approval)
    # Namespaced env vars so an ambient GITHUB_TOKEN is never picked up by accident.
    github_token: str = Field(default="", validation_alias="ACTIONS_GITHUB_TOKEN")
    github_repo: str = Field(default="", validation_alias="ACTIONS_GITHUB_REPO")  # "owner/repo"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor; FastAPI dependencies can call it cheaply."""
    return Settings()
