# Game Design Document: "Syntax"

> **Mission Statement:** An un-themed, utilitarian mobile browser game designed to combat developer skill atrophy. In an era of LLM-generated code, "Syntax" tests and reinforces raw logic, syntax memory, and algorithmic understanding using touch-native, daily micro-challenges.

**Status:** Living document — supersedes `Syntax_Game_Design_Document.pdf`
**Last updated:** 2026-07-16

---

## 1. Core Gameplay Loop

The game relies on habit formation through a synchronized daily reset, completely independent of complex fictional narratives. The player's motivation is self-improvement and peer competition.

1. **Login:** User opens the browser app. No heavy loads, instant access — target **< 2s to interactive** on mid-range mobile over 4G (see §7 Performance Budget).
2. **The Daily Stack:** Player is presented with 3 to 5 micro-challenges for the day.
3. **Execution:** Player solves the challenges using tap, drag-and-drop, and swipe mechanics (zero manual typing required).
4. **Resolution:** The daily score is generated based on accuracy and time. **Answers are validated server-side only** — the client never receives the correct answer until the challenge is resolved (see §8 Anti-Cheat).
5. **Progression:** Experience points (XP) are allocated to specific language skill trees based on the day's challenge stack.

### Enhancements to the loop

- **Streaks:** A visible daily streak counter (Wordle/Duolingo-style) with one earnable **Streak Freeze** per week to reduce churn from a single missed day.
- **Warm-up round (optional):** A single untimed practice question before the scored stack, drawn from the player's weakest skill node. Doesn't affect score; primes engagement.
- **Post-round explanation:** After resolution, each challenge shows a concise "why" — the fixed line, the correct ordering with reasoning, the missed edge case. The learning payoff is the retention hook, not just the score.
- **Session length target:** 2–4 minutes total. If a stack routinely exceeds 5 minutes, difficulty tuning is wrong.
- **Anti-frustration:** Two attempts per challenge. First-try success scores full points; second try scores partial. Failure reveals the explanation and scores zero — the player still learns something.

---

## 2. Game Mechanics & Question Styles

Challenges are designed to test real programming knowledge without the friction of mobile keyboards. The system is modular, allowing for continuous expansion of question types — each question type is a self-contained frontend component plus a server-side validator, registered against a shared challenge schema.

### Current Scope (Launch Set)

- **Bug Spotting:** A 10–15 line snippet is displayed. The player must tap the exact line containing a logic error, memory leak, or syntax fault.
- **Parsons Problems:** Code blocks are provided in a scrambled list. The player drags and drops them into the correct logical order and indentation level (e.g., assembling a Binary Search or a custom array sort).
- **The LLM Auditor:** A prompt and its AI-generated code response are shown. The player selects from multiple-choice options detailing the specific edge case the AI failed to account for.
- **Time Complexity Match:** An algorithm is shown, and the user must assign its Big O notation (time or space) from a pre-defined set of buttons.

### Future Expansion Scope

- **Architecture Assembly:** Dragging and dropping cloud/infrastructure components (Load Balancers, DBs, Caches) to satisfy a high-level system design requirement.
- **Regex Crosswords:** A visual grid where rows and columns are defined by regular expressions, testing pattern matching skills.
- **State Prediction:** Showing a snippet with a complex state change (e.g., nested loops or asynchronous callbacks) and asking the user to select the final value of a specific variable from options (kept tap-only — no free-text input).
- **Refactor Pick:** Two or three semantically equivalent snippets shown side by side; player taps the most idiomatic/performant one. Cheap to author, tests taste as well as correctness.

### Content pipeline (new)

- Challenges are authored as structured JSON documents (snippet, distractors, correct answer, explanation, difficulty rating, skill-tree tags) validated against a schema in CI.
- **LLM-assisted authoring, human-verified:** Draft challenges can be generated at scale, but every published challenge is reviewed and its code actually executed/tested before entering the pool. A broken "correct answer" is the fastest way to lose trust with a developer audience.
- Each challenge tracks live stats (solve rate, average time, first-try rate) to feed difficulty calibration and retire bad questions.

---

## 3. Meta-Game: Skill Trees & Progression

Instead of arbitrary levels, the progression system mirrors professional development. Players earn nodes on specific language and framework trees.

- **Base Trees:** The game will initially support distinct tracks. For example, a player might focus their profile on *Python*, *JavaScript*, or *Flutter/Dart*. **Launch recommendation: ship Python + JavaScript only** — two deep trees beat four shallow ones, and both map directly to the initial audience.
- **Nodes & Unlocks:** Accumulating XP in Python might unlock challenges involving specific advanced libraries (e.g., Pandas logic) or deeper language features (e.g., metaclasses, generators).
- **Proficiency Badge:** A player's visual rank is directly tied to their skill tree density, serving as a realistic indicator of their daily retention efforts.

### Enhancements

- **Decay (gentle):** Node proficiency slowly fades if a skill isn't exercised for weeks, visually dimming rather than un-unlocking. This is the "skill atrophy" premise made mechanical — and it motivates the daily return without punishing holidays (decay pauses while a Streak Freeze is active).
- **Placement calibration:** A first-run optional 5-question placement quiz seeds starting difficulty per track, so senior devs aren't bored by `off-by-one 101` on day one.
- **Weekly recap:** Every Monday, a summary card — XP gained, weakest node, sharpest node, percentile vs. the player's league.

---

## 4. Social & Competitive (Wordle Mechanics)

To drive daily retention without requiring traditional multiplayer infrastructure, the game utilizes asynchronous, standardized sharing.

> **Universal Daily Seed:** Every player receives the exact same "Daily Stack" at midnight local time. The shared struggle is the community hook.

### Shareable Results

Upon completing the Daily Stack, players can copy an emoji grid to the clipboard. The grid obfuscates the answers while bragging about performance. Colors represent first-try success, multiple attempts, or failure.

```text
Syntax Daily #142
Python Track: Lvl 12
⏱ 02:14
1️⃣ 🟩 (Spot the Bug)
2️⃣ 🟩 (Parsons Problem)
3️⃣ 🟨 (LLM Audit)
```

### Leaderboards (new)

- **Global daily leaderboard:** Ranked by score, then time, for today's stack. Resets with the daily seed.
- **Friends leaderboard:** Follow other players by handle; a small persistent list of the people you actually care about beating. No chat, no DMs — zero moderation surface at launch.
- **Leagues (post-launch):** Weekly cohorts of ~30 players of similar skill (Duolingo model), with promotion/demotion. Drives mid-tier competition where a global board demotivates.
- **All-time stats:** Longest streak, total solves, per-track percentile on the player profile.

### Daily seed & time zones (clarification)

"Midnight local time" is the player experience; implementation-wise the daily challenge is keyed by the player's **local calendar date** (e.g., stack ID `2026-07-16`). All players on the same calendar date get the same stack, and the leaderboard for a stack closes 48h after that date first begins anywhere on Earth. Late-finishers can still play and score XP, but past-day results don't enter the closed leaderboard.

---

## 5. Visual & Audio Style

> Full specification: [STYLE_GUIDE.md](STYLE_GUIDE.md) — early-2010s developer-tool aesthetic (clean lines, 1px borders, tame radii, blue-on-grey).

- **Aesthetic:** Early-2010s dev tool. Light grey/blue chrome by default (GitHub/Stack Overflow circa 2013), with a dark chrome variant. **Code surfaces are always dark IDE-styled** with high-contrast syntax highlighting matching VS Code — the "Dark Mode IDE" identity lives in the challenge surface itself.
- **UI Framework:** Minimalist interfaces. Large touch targets for drag-and-drop (minimum 44×44px). Haptic feedback on mobile (vibrations on snapping a block into place, via the Vibration API where supported).
- **Audio:** No background music. Subtle, mechanical sound effects — like mechanical keyboard clicks when a correct answer is locked in. Muted by default until the player opts in (mobile browsers require a user gesture for audio anyway).
- **Accessibility (new):** Emoji-grid colors are paired with distinct shapes for color-blind players; all challenges completable via keyboard on desktop; drag-and-drop has a tap-to-select/tap-to-place fallback; `prefers-reduced-motion` respected.

---

## 6. Technical Architecture

### Stack overview

| Layer | Technology | Rationale |
|---|---|---|
| Frontend | TypeScript + Vite (PWA) | Minimal bundle, instant dev feedback, sub-2s cold loads for quick daily rounds |
| Auth | Firebase Authentication (Google + GitHub providers) | Zero password handling; GitHub is the natural identity for a developer audience |
| Player data | Cloud Firestore | User progress, XP/skill trees, streaks, top scores, leaderboards |
| Backend | Python — FastAPI (containerized) or Firebase Cloud Functions (Python runtime) | Server-side answer validation, scoring, leaderboard writes |
| Static hosting | Firebase Hosting (or any CDN) | Pairs naturally with the Firebase SDK setup |

### Frontend

- **Vite + TypeScript**, deliberately framework-light. The UI is a handful of screens and four challenge components; **Preact or vanilla TS with lit-html** keeps the bundle in the tens of KB. If team velocity favors React, use it — but the performance budget (§7) is the contract either way.
- **PWA:** installable, service-worker cache for the app shell so repeat visits are near-instant, offline notice when there's no connectivity. (The daily stack itself requires the network — answers live server-side.)
- Each question type = one component implementing a shared `Challenge` interface: `render(payload)`, `getAnswerPayload()`. New question types are additive.
- Firebase JS SDK loaded modularly (tree-shaken `firebase/auth`, `firebase/firestore`) to protect the bundle budget.

### Backend — server-authoritative answers

A small Python API is the **only** component that knows correct answers. Two deployment candidates:

1. **FastAPI in a container** — portable across hosts, easy local dev (`uvicorn`), full framework ergonomics (Pydantic validation, dependency injection, OpenAPI docs for free). **Recommended.**
2. **Firebase Cloud Functions (Python)** — tightest Firebase integration and zero infra, but cold starts and weaker local-dev ergonomics.

**Hosting (to be decided).** Shortlist, all of which run the same FastAPI container:

| Option | Pros | Cons |
|---|---|---|
| **Google Cloud Run** (front-runner) | Same GCP project as Firebase — IAM, Firestore, and Firebase Admin SDK are native; scales to zero; generous free tier | Cold starts (mitigable with min-instances = 1 for pennies) |
| Fly.io | Cheap always-on small VMs, no cold starts | Separate platform from Firebase; secrets/IAM managed separately |
| Railway / Render | Simplest DX | Costlier at always-on tier; separate platform |

Given Firebase is already the platform for auth + data, **Cloud Run is the path of least resistance** — but the code should stay host-agnostic (plain container, config via env vars).

#### API surface (v1)

```text
GET  /daily/{date}?track=python     → today's stack (challenge payloads WITHOUT answers)
POST /submit                        → {challengeId, attempt, answerPayload, clientElapsedMs}
                                      ← {correct, attemptsRemaining, explanation?, score?}
POST /complete                      → finalize the day's run → XP allocation, leaderboard write
GET  /leaderboard/{date}?scope=global|friends
```

- All endpoints require a **Firebase ID token** (`Authorization: Bearer`), verified server-side with the Firebase Admin SDK.
- The server writes scores/XP/leaderboard entries to Firestore itself. **Clients have no write access to score-bearing collections** — enforced by Firestore Security Rules.

### Data model (Firestore, first cut)

```text
users/{uid}
  displayName, handle, photoURL, createdAt
  streak: { current, longest, freezesAvailable, lastPlayedDate }
  tracks: { python: { xp, level }, javascript: { xp, level } }

users/{uid}/skillNodes/{nodeId}
  xp, unlockedAt, lastExercisedAt        # decay computed from lastExercisedAt

challenges/{challengeId}                  # server/admin read only — answers live here
  type, track, difficulty, payload, answer, explanation, stats

dailyStacks/{date}                        # e.g. 2026-07-16
  challengeIds: [...], track variants

runs/{uid}_{date}                         # one run per user per day (idempotency key)
  answers: [{challengeId, attempts, correct, elapsedMs}]
  score, completedAt

leaderboards/{date}/entries/{uid}
  score, totalMs, track, handle           # written by backend only

follows/{uid}/following/{targetUid}       # friends leaderboard source
```

**Security Rules sketch:** users can read/write only cosmetic fields of their own `users/{uid}` doc; `challenges`, `runs`, and `leaderboards` are backend-only writes (Admin SDK bypasses rules); leaderboard entries are world-readable.

---

## 7. Performance Budget

The "instant access" promise from §1, made measurable:

- **≤ 100 KB** gzipped JS for the initial route (Firebase SDK included — this is why modular imports matter).
- **< 2s** time-to-interactive on a mid-range Android phone over 4G; **< 1s** on repeat visits (service-worker shell).
- Challenge payloads fetched in one request; syntax highlighting done with a lightweight tokenizer (e.g., Shiki at build time for static content, or a ~5 KB highlighter at runtime) — not a full editor dependency.
- No blocking web fonts: system monospace stack (`ui-monospace, 'Cascadia Code', 'SF Mono', Menlo, Consolas, monospace`).

---

## 8. Anti-Cheat & Integrity

The audience is developers — the people *most* capable of opening DevTools. Design assumption: **the client is hostile.**

1. **Answers never ship to the client.** The `/daily` payload contains the question and options only. Correctness is determined exclusively by `POST /submit`.
2. **Server-side timing.** The score clock is server-side: it starts when the stack is first fetched and each submit is timestamped on the server. `clientElapsedMs` is accepted only as a sanity signal, never as the scoring input.
3. **Attempt enforcement server-side.** The run document tracks attempts; a third submit for a challenge is rejected regardless of what the client shows.
4. **Idempotent runs.** One `runs/{uid}_{date}` document per player per day. Replays don't rewrite the leaderboard.
5. **Plausibility checks.** Sub-human solve times (e.g., a Parsons problem "solved" in 400ms) are flagged, scored but quarantined from the leaderboard pending review.
6. **Rate limiting** on `/submit` per uid to blunt brute-forcing multiple-choice answers; combined with the two-attempt cap, brute force yields nothing anyway.
7. **Accepted residual risk:** shared answers between friends on the same daily seed. Wordle has the same property; the 48h leaderboard close and per-day seed keep the damage bounded. Not worth heavier countermeasures at launch.

---

## 9. Roadmap

### Phase 0 — Foundation
Vite/TS scaffold, Firebase project (Auth with Google + GitHub, Firestore), FastAPI skeleton with token verification, challenge JSON schema, CI.

### Phase 1 — MVP (playable daily loop)
Two tracks (Python, JavaScript). Bug Spotting + Parsons Problems + Time Complexity Match. Daily stack, server-side scoring, streaks, emoji share card, global daily leaderboard. PWA shell.

### Phase 2 — Retention
LLM Auditor question type. Skill trees with decay, placement quiz, weekly recap, friends leaderboard, streak freezes.

### Phase 3 — Depth
Leagues, additional tracks, expansion question types (Refactor Pick, State Prediction), challenge-stats-driven difficulty calibration, light theme polish.

### Open questions
- Backend hosting decision (Cloud Run front-runner — see §6).
  - Will look at using Google Cloud Run. But at least we can test locally with Python during dev
- Anonymous play before sign-in? (Recommend: yes — play first, auth-gate the leaderboard/streak persistence. Firebase anonymous auth can later be linked to Google/GitHub without losing progress.)
  - Yes agreed - anonymouse play before sign-in
- Challenge authoring tooling: internal CLI vs. simple admin web UI.
  - Will probably just use Claude Code to auther new challenges as we go along
