"""Test fixtures: isolated memory store + freezable server clock."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

AUTH = {"Authorization": "Bearer dev:tester"}


def _clear_caches() -> None:
    from app.config import get_settings
    from app.content import get_content
    from app.store import get_store

    get_settings.cache_clear()
    get_store.cache_clear()
    get_content.cache_clear()


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Configure a fresh dev/memory environment for each test."""
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("STORE_MODE", "memory")
    monkeypatch.setenv("DATA_FILE", str(tmp_path / "store.json"))
    monkeypatch.setenv("SYNTAX_NOW", "2026-07-16T09:00:00Z")

    def set_now(iso: str) -> None:
        # Only the settings cache holds the frozen clock; the store persists to
        # disk so it survives a cache clear.
        monkeypatch.setenv("SYNTAX_NOW", iso)
        from app.config import get_settings

        get_settings.cache_clear()

    _clear_caches()
    return set_now


@pytest.fixture
def client(env):
    from app.main import app

    with TestClient(app) as c:
        yield c
