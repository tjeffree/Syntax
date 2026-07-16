"""Syntax API entrypoint.

Run locally:  uvicorn app.main:app --reload  (from the backend/ directory)
Docs:         http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .content import get_content
from .routers import complete, daily, leaderboard, profile, submit


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load + validate all challenge content at startup so broken JSON or a wrong
    # "correct answer" fails fast rather than at first request (GDD §2).
    index = get_content()
    print(f"[syntax] loaded {len(index.by_id)} challenges")
    yield


app = FastAPI(title="Syntax API", version=__version__, lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(daily.router, tags=["daily"])
app.include_router(submit.router, tags=["submit"])
app.include_router(complete.router, tags=["complete"])
app.include_router(leaderboard.router, tags=["leaderboard"])
app.include_router(profile.router, tags=["profile"])


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "auth_mode": settings.auth_mode,
        "store_mode": settings.store_mode,
        "challenges": len(get_content().by_id),
    }
