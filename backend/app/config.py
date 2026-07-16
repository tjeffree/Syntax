"""Runtime configuration, loaded from environment / .env file."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # "dev" | "firebase"
    auth_mode: str = "dev"
    # "memory" | "firestore"
    store_mode: str = "memory"

    data_file: str = "./.data/store.json"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    firebase_credentials: str | None = None
    firebase_project_id: str | None = None

    # Deterministic clock override for tests (ISO-8601). Read via time_source.
    syntax_now: str | None = None

    # Gameplay constants (see GDD §1, §8).
    attempts_per_challenge: int = 2
    # Content directory holding authored challenge JSON.
    content_dir: str = str(Path(__file__).resolve().parent.parent / "content" / "challenges")
    schema_file: str = str(Path(__file__).resolve().parent.parent / "schema" / "challenge.schema.json")

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
