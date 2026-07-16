# Syntax

An un-themed, utilitarian mobile browser game that fights developer skill
atrophy with daily, touch-native micro-challenges. See
[`docs/GDD.md`](docs/GDD.md) and [`docs/STYLE_GUIDE.md`](docs/STYLE_GUIDE.md).

This repo currently implements **Phase 0 (Foundation)** and **Phase 1 (MVP —
playable daily loop)** from the roadmap, and runs **entirely locally with no
Firebase project**. When you're ready for real auth/hosting, follow
[`docs/FIREBASE_SETUP.md`](docs/FIREBASE_SETUP.md).

---

## What's here

```
backend/     FastAPI — the server-authoritative brain (answers, scoring, streaks)
frontend/    Vite + TypeScript PWA — the touch-native client
firebase/    Firestore rules + hosting config (for later)
docs/        GDD, style guide, Firebase setup guide
.github/     CI (backend pytest + frontend build)
```

Design assumption from GDD §8: **the client is hostile.** Correct answers, the
score clock, and attempt limits live only in the backend and never ship to the
browser.

### Phase 1 feature checklist

- ✅ Two tracks: Python + JavaScript
- ✅ Three question types: Bug Spotting, Parsons Problems, Time Complexity Match
- ✅ Universal daily stack (same seed for everyone, keyed by local date)
- ✅ Server-side answer validation, timing, and two-attempt cap
- ✅ Scoring + XP/levels, streaks with a weekly Streak Freeze
- ✅ Global daily leaderboard
- ✅ Emoji share card (copy to clipboard)
- ✅ PWA shell (installable, offline app-shell cache)
- ✅ Light/dark chrome, always-dark IDE code surface, tap-first + keyboard a11y

---

## Run it locally

You need **Python 3.10+** and **Node 18+**. No Firebase, no cloud, no keys.

### 1. Backend (the "background service")

**PowerShell:**

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
uvicorn app.main:app --reload
```

**bash / macOS / Linux:**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The API is now on <http://localhost:8000> (interactive docs at `/docs`,
health at `/health`). It defaults to `AUTH_MODE=dev` + `STORE_MODE=memory`, so
state persists to `backend/.data/store.json`.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local        # (copy on Windows)
npm run dev
```

Open <http://localhost:5173>. You're playing as an anonymous local user — no
sign-in needed. Play the stack, submit answers, complete the day, copy your
emoji grid, check the leaderboard.

> To see the leaderboard populated with more than one row, open the app in a
> second browser profile / incognito window (each gets its own anonymous uid),
> or clear `localStorage`'s `syntax.anonUid` to become a new player.

---

## Tests

```bash
# backend — unit + full API flow (also validates all challenge JSON)
cd backend && pytest

# frontend — typecheck + production build (enforces the bundle budget)
cd frontend && npm run build
```

CI runs both on every push/PR (`.github/workflows/ci.yml`).

---

## API surface (v1)

All endpoints require `Authorization: Bearer <token>` (in dev mode: `dev:<uid>`).

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/daily/{date}?track=` | Today's stack — payloads **without** answers |
| `POST` | `/submit` | Grade one attempt server-side |
| `POST` | `/complete` | Finalize the run: XP, streak, leaderboard write |
| `GET`  | `/leaderboard/{date}?track=&scope=` | Global daily board |
| `GET`  | `/me` | Profile, streak, per-track XP |
| `GET`  | `/health` | Liveness + active auth/store mode |

---

## Authoring new challenges

Challenges are JSON files in `backend/content/challenges/`, validated against
`backend/schema/challenge.schema.json` at startup **and** in CI (a broken
"correct answer" fails the build — GDD §2). Drop in a new file, restart the
backend, and it's automatically eligible for the daily seed. This is the
intended "author with Claude Code as we go" workflow (GDD §9 open questions).

Each file: `id`, `type` (`bug-spot` | `parsons` | `big-o`), `track`,
`difficulty` (1–5), `skillNodes`, a type-specific `payload`, the server-only
`answer`, and an `explanation`. Copy an existing file as a template.

---

## Configuration reference

| Where | Var | Default | Meaning |
|---|---|---|---|
| backend | `AUTH_MODE` | `dev` | `dev` (bearer `dev:<uid>`) or `firebase` |
| backend | `STORE_MODE` | `memory` | `memory` (JSON file) or `firestore` |
| backend | `DATA_FILE` | `./.data/store.json` | memory-store path |
| backend | `CORS_ORIGINS` | localhost:5173 | allowed frontend origins |
| backend | `SYNTAX_NOW` | (unset) | freeze the server clock (testing) |
| frontend | `VITE_API_BASE` | `http://localhost:8000` | backend URL |
| frontend | `VITE_AUTH_MODE` | `dev` | `dev` or `firebase` |

Going to production? → [`docs/FIREBASE_SETUP.md`](docs/FIREBASE_SETUP.md).
