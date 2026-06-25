"""
Application configuration.

Centralizes all environment-driven settings so the rest of the codebase
never touches os.environ directly. Settings are validated at startup —
if GEMINI_API_KEY is missing, the app fails fast with a clear error
instead of failing later on the first request.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    allowed_origins: str = "http://localhost:3000"
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10MB

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings accessor. Using lru_cache means Settings() is only
    constructed once per process, and FastAPI's dependency injection
    can call get_settings() cheaply from any route.
    """
    return Settings()
