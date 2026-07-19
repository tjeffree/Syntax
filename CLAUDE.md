# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Syntax is a mobile browser game of daily developer micro-challenges (see [`docs/GDD.md`](docs/GDD.md) and [`docs/STYLE_GUIDE.md`](docs/STYLE_GUIDE.md)). Two parts:

- [`backend/`](backend/) — FastAPI, the **server-authoritative** brain (answers, scoring, timing, streaks).
- [`frontend/`](frontend/) — Vite + TypeScript PWA, a thin touch-native client.
- [`firebase/`](firebase/) — Firestore rules + hosting config for production.

**The client is hostile (GDD §8).** Correct answers, the score clock, and attempt limits live *only* in the backend and never ship to the browser. `GET /daily` returns challenge payloads with `answer` stripped; grading happens in [`backend/app/content.py`](backend/app/content.py) `grade()`, the single place correctness is decided.

## Commands

```bash
# Backend (from backend/) — needs Python 3.10+
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\Activate.ps1 on Windows
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload            # API on :8000, docs at /docs, health at /health

pytest                                    # all tests (also validates every challenge JSON)
pytest tests/test_scoring.py             # one file
pytest tests/test_api.py::test_name -q   # one test

# Frontend (from frontend/) — needs Node 18+
npm install
cp .env.example .env.local
npm run dev                               # :5173, plays as an anonymous local user
npm run build                             # tsc --noEmit + vite build — this is the CI gate
npm run typecheck                         # tsc --noEmit only
```

CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs `pytest` and `npm run build` on every push/PR. There is no separate lint step or frontend test runner — `npm run build` (typecheck) is the frontend gate.

## Architecture

### Backend request flow

Routers ([`backend/app/routers/`](backend/app/routers/)) are thin HTTP shells; domain logic lives in [`service.py`](backend/app/service.py) (user/run bootstrap, ranking) and [`scoring.py`](backend/app/scoring.py) (pure functions: points, speed bonus, XP/levels, streaks, plausibility). The five endpoints:

- `GET /daily/{date}?track=` → today's stack, answers stripped.
- `POST /submit` → grade one attempt; the server times each challenge from `run["last_activity_ms"]` (client-reported elapsed is ignored for scoring). Two attempts per challenge (`attempts_per_challenge`).
- `POST /complete` → finalize the run: XP into the track, streak update, leaderboard write. **Idempotent** — a completed run returns its stored `completion` verbatim. Implausibly-fast runs are quarantined and kept off the leaderboard.
- `GET /leaderboard/{date}` and `GET /me`.

A **run** is keyed by `(uid, date, track)` and accumulates per-challenge answer state. Everything is plain JSON-serialisable dicts so the same shapes round-trip through both stores.

### Two swappable axes, chosen by config, cached as singletons

- **Auth** ([`auth.py`](backend/app/auth.py)) — `AUTH_MODE=dev` accepts `Authorization: Bearer dev:<uid>` and trusts the uid (powers local anonymous play, no Firebase needed); `firebase` verifies an ID token via the Admin SDK (imported lazily). Everything downstream sees a uniform `AuthedUser`.
- **Store** ([`store/`](backend/app/store/)) — `STORE_MODE=memory` is a JSON file on disk (`DATA_FILE`, default `backend/.data/store.json`); `firestore` is Cloud Firestore. Both implement the abstract [`store/base.py`](backend/app/store/base.py) `Store` interface.

Add `SYNTAX_NOW` (ISO-8601) to freeze the server clock — all time flows through [`time_source.py`](backend/app/time_source.py), never `datetime.now()` directly.

### Content: two modes (seed vs. generated)

Challenges are validated against [`backend/schema/challenge.schema.json`](backend/schema/challenge.schema.json) plus cross-field `_semantic_checks` in [`content.py`](backend/app/content.py) — a broken "correct answer" fails at load time and in CI (GDD §2). Types: `bug-spot`, `parsons`, `big-o`; tracks: `python`, `javascript`.

[`content_repository.py`](backend/app/content_repository.py) chooses the source by `CONTENT_MODE`:

- **`seed`** (default) — serves the checked-in JSON in [`backend/content/challenges/`](backend/content/challenges/). The daily stack is a *deterministic hash* of `(date, track, type)` ([`seed.py`](backend/app/seed.py)) — everyone gets the same stack, no stored schedule. **To author a challenge**: drop a new JSON file in that dir (copy an existing one), restart the backend, done.
- **`firestore`** — serves only generated, published daily stacks. [`generation.py`](backend/app/generation.py) calls OpenAI to produce a 6-challenge stack (one of each type × track), runs it through the *same* local validation gates, derives ids deterministically, and self-heals by regenerating on rejection (`generate_valid_stack`, up to 3 attempts). Published atomically in a Firestore transaction by the [`jobs/generate_daily.py`](backend/app/jobs/generate_daily.py) Cloud Run job. Stacks and challenges are immutable once published; [`jobs/cleanup_expired_content.py`](backend/app/jobs/cleanup_expired_content.py) enforces `DAILY_STACK_RETENTION_DAYS`.

When touching validation, keep the gates in `validate_daily_stack` (generation path) and `load_all`/`grade` (seed path) consistent — both funnel through `validate_raw_challenge`.

### Frontend

Vanilla TS, no framework. [`app.ts`](frontend/src/app.ts) is the state machine driving the daily loop; challenge UIs are registered by type in [`challenges/registry.ts`](frontend/src/challenges/registry.ts) (additive — one factory per type). [`api.ts`](frontend/src/api.ts) wraps fetch with the bearer token from [`auth.ts`](frontend/src/auth.ts). Styling is CSS custom properties in [`styles/tokens.css`](frontend/src/styles/tokens.css); light/dark chrome, always-dark code surface. PWA shell via [`public/service-worker.js`](frontend/public/service-worker.js) + [`public/manifest.webmanifest`](frontend/public/manifest.webmanifest). `vite.config.ts` uses a relative `base` so the build works under any hosting path.

## Deployment

Production is Firebase (hosting + Firestore) with the backend and generator/cleanup as Cloud Run jobs. [`running.info.sh`](running.info.sh) has the concrete `gcloud`/`firebase` commands (project `syntax-game`, region `europe-west2`); [`docs/GOOGLE_CLOUD_RUN_DEPLOYMENT.md`](docs/GOOGLE_CLOUD_RUN_DEPLOYMENT.md) and [`docs/FIREBASE_SETUP.md`](docs/FIREBASE_SETUP.md) are the full guides. `docs/DAILY_GENERATED_CHALLENGES_PLAN.md` covers the generation pipeline design.

## Config reference

| Where | Var | Default | Meaning |
|---|---|---|---|
| backend | `AUTH_MODE` | `dev` | `dev` (bearer `dev:<uid>`) or `firebase` |
| backend | `STORE_MODE` | `memory` | `memory` (JSON file) or `firestore` |
| backend | `CONTENT_MODE` | `seed` | `seed` (checked-in JSON) or `firestore` (generated) |
| backend | `DATA_FILE` | `./.data/store.json` | memory-store path |
| backend | `CORS_ORIGINS` | localhost:5173 | allowed frontend origins |
| backend | `SYNTAX_NOW` | (unset) | freeze the server clock (testing) |
| backend | `OPENAI_API_KEY` / `OPENAI_MODEL` | — / `gpt-5.6-luna` | daily generation |
| frontend | `VITE_API_BASE` | `http://localhost:8000` | backend URL |
| frontend | `VITE_AUTH_MODE` | `dev` | `dev` or `firebase` |
