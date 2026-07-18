# Daily generated challenges — implementation plan

## Decision

Replace runtime selection from the packaged challenge bank with one **published
daily stack per date and track** held in Cloud Firestore. Every player who opens
the same calendar date and track receives exactly that stack.

The JSON challenges committed under `backend/content/challenges/` remain in the
repository as:

- local-development and demo fixtures;
- a safe fallback only when `CONTENT_MODE=seed` is explicitly selected; and
- regression-test inputs.

They must not be silently mixed into production daily stacks. In production,
if a date has no published stack, the API returns a clear `503 daily stack is
not ready` response rather than serving stale generated or demo content.

## Scope and assumptions

Syntax currently has two tracks (`python` and `javascript`) and presents one
challenge of each type (`bug-spot`, `parsons`, and `big-o`) in a stack. To
preserve this product behaviour, each game date produces **six challenges**:

| Track | Stack contents | Count |
|---|---|---:|
| Python | one bug spot, one Parsons, one Big-O | 3 |
| JavaScript | one bug spot, one Parsons, one Big-O | 3 |

If the intended product is only three challenges across both languages, that
is a separate product/API change: a user would need to choose a shared mixed
track or the current `track` parameter would need to be removed.

`game_date` remains the existing `YYYY-MM-DD` local calendar date. A stack for
game date **D** is generated and published before any player can enter D: at
09:45 UTC on D-1 (midnight in UTC+14). This preserves the GDD's local-date
experience while keeping every player on the same game date on the same stack.

## Target architecture

```text
Cloud Scheduler (09:45 UTC daily, authenticated)
        |
        v
Cloud Run Job: generate game date D
        |-- OpenAI Responses API (structured JSON)
        |-- schema + semantic validation
        |-- duplicate and quality checks
        v
Firestore: dailyStacks/{D} + challenges/{challengeId}
        |
        v
Existing Cloud Run FastAPI service
        |
        v
All players receive the immutable published stack for D
```

Use a **Cloud Run Job**, rather than a public FastAPI endpoint, for generation.
It has no player-facing attack surface, completes independently of API traffic,
and can be retried by the scheduler. It may share the backend image and Python
code, with a command such as `python -m app.jobs.generate_daily`.

The existing FastAPI Cloud Run service continues to serve `/daily`, `/submit`,
and `/complete`. It reads only the published stack; it never calls OpenAI on a
player request.

## Firestore data model

### `challenges/{challenge_id}` (private)

Store the existing complete challenge JSON, including `answer`, plus service
metadata:

```json
{
  "id": "2026-07-19-python-bug-spot",
  "type": "bug-spot",
  "track": "python",
  "difficulty": 2,
  "skillNodes": ["control-flow"],
  "payload": { "language": "python", "code": "..." },
  "answer": { "line": 4 },
  "explanation": "...",
  "game_date": "2026-07-19",
  "status": "approved",
  "created_at": "<server timestamp>",
  "generator": { "model": "<configured model>", "prompt_version": "v1" }
}
```

This collection is never readable by browser clients. It supplies both the
public question and server-only grading answer.

### `dailyStacks/{game_date}` (private)

One immutable manifest for the date:

```json
{
  "game_date": "2026-07-19",
  "status": "published",
  "published_at": "<server timestamp>",
  "tracks": {
    "python": ["2026-07-19-python-bug-spot", "...-parsons", "...-big-o"],
    "javascript": ["2026-07-19-javascript-bug-spot", "...-parsons", "...-big-o"]
  },
  "generation_id": "2026-07-19",
  "schema_version": 1
}
```

The manifest contains IDs only. Keeping both collections private is the safest
option and is consistent with the existing Firestore rules.

### Retention

Start with **seven days** of completed stacks and challenge documents. This is
only roughly 42 small JSON documents at any one time and is not a meaningful
storage cost. Seven days also leaves room for late completions, support checks,
and scheduler recovery.

After launch, reduce to a minimum of **four days** only if the product
explicitly disallows opening older stacks. Do not delete a challenge while an
open run can still submit it; `POST /submit` needs its answer. A nightly cleanup
job deletes expired manifests and only their referenced challenge documents,
after the retention window. It must be idempotent and never delete the current
or next published date.

## Generation flow

1. Scheduler starts the job for target date D-1's next game date.
2. The job reads `dailyStacks/D`.
   - If it is already `published`, it exits successfully. This makes retries
     harmless.
   - If it is `generating`, a lease with an expiry prevents concurrent jobs.
3. The job generates six challenge objects in one or small number of OpenAI
   Responses API calls. Request JSON Structured Outputs matching the existing
   `challenge.schema.json` shape.
4. For every candidate, run the current JSON Schema validation and
   `_semantic_checks` before any database write.
5. Apply deterministic checks:
   - exactly one required type per track;
   - correct IDs, date, track, and difficulty range;
   - no duplicate block IDs, invalid answer line, or answer absent from options;
   - payload and answer size limits; and
   - no duplicate normalized code/prompt against retained challenges.
6. Optionally use a second low-volume model call as a reviewer, but do not make
   publication depend solely on model self-review. The deterministic checks are
   the release gate.
7. In a Firestore transaction/batched write, create private challenge documents
   and set the stack manifest to `published`. The API treats only this status as
   playable.
8. If generation or validation fails, retry with bounded attempts. Leave the
   date unpublished and alert; do not partially publish a stack.

The OpenAI request uses the Responses API and Structured Outputs so the model
returns the expected JSON envelope. See the official [Responses API
quickstart](https://platform.openai.com/docs/quickstart/make-your-first-api-request)
and [Structured Outputs reference](https://platform.openai.com/docs/api-reference/responses-streaming/response/refusal/delta?lang=curl).

## Backend changes

### Content repository

Introduce a `ChallengeRepository` abstraction:

- `SeedChallengeRepository` loads existing JSON files for local demo mode.
- `FirestoreChallengeRepository` loads a `dailyStacks/{date}` manifest and its
  referenced private challenge documents.

The production repository returns a date-specific `ContentIndex`; it does not
use `seed.build_stack()`. The existing `grade()` logic and `Challenge`/
`ChallengePublic` models remain the authority for answer handling and API
serialization.

Configuration:

```ini
CONTENT_MODE=firestore       # production
DAILY_STACK_RETENTION_DAYS=7
OPENAI_MODEL=<configured model>
OPENAI_API_KEY=<Secret Manager injected secret>
```

`CONTENT_MODE=seed` stays the default for existing tests and demos.

### API behaviour

- `GET /daily/{date}?track=` reads that date's published manifest and challenge
  IDs, then returns public payloads exactly as it does today.
- `POST /submit` and `POST /complete` resolve challenge IDs from the same
  date-specific stack, preventing cross-date challenge submission.
- Remove deterministic hash selection from production paths, but retain it for
  `CONTENT_MODE=seed`.
- Return `404` for expired dates and `503` for a current/future date that is not
  yet published. Do not create a run until a stack is available.
- Add `generation_id` / `stack_id` to runs if useful for diagnostics; challenge
  IDs already make the content version auditable.

### New executable modules

- `app/jobs/generate_daily.py` — generation, validation, publish transaction.
- `app/jobs/cleanup_expired_content.py` — safe retention cleanup.
- `app/repositories/challenges.py` — seed and Firestore repositories.
- `app/generation/` — OpenAI client, prompt versioning, and quality checks.

Keep the OpenAI key in Google Secret Manager, exposed only to the job's service
account as an environment variable. The player-facing API service does not
need permission to read that secret or call OpenAI.

## IAM and security

- Cloud Scheduler invokes only the Cloud Run Job execution path with a dedicated
  scheduler service account.
- The job service account can read the OpenAI secret and read/write
  `challenges` and `dailyStacks`.
- The API service account can read those collections and write runs, users, and
  leaderboards; it needs no OpenAI secret access.
- Browser Firestore rules retain `allow read, write: if false` for
  `challenges` and `dailyStacks`.
- Log metadata, validation outcomes, and request IDs—not prompts/responses that
  could expose answers unnecessarily.

## Quality, observability, and recovery

Metrics and alerts:

- generation started / published / failed by game date;
- candidates rejected by schema, semantic, duplicate, and reviewer checks;
- duration, token use, and estimated cost;
- `GET /daily` 503 count; and
- cleanup deleted document count.

Operational safeguards:

- Generate the next date early, not at the moment players need it.
- Provide an operator-only `--date` and `--dry-run` mode to regenerate or
  inspect a stack before publishing.
- Never overwrite a published stack automatically. Correct it only through an
  explicit, audited operator action before players begin it.
- If the job fails, manually rerun it. If unavailable close to the deadline,
  publish a prevalidated emergency stack generated earlier; do not fall back to
  the demo bank without an explicit operational decision.

## Delivery phases

1. **Repository refactor:** add `CONTENT_MODE`, Firestore repository, and unit
   tests proving Firestore and seed repositories behave identically at the API
   boundary.
2. **Generation pipeline:** add OpenAI client, structured schema, deterministic
   validation, idempotent Firestore publication, and dry-run CLI.
3. **Cloud deployment:** add Cloud Run Job definition, Scheduler invocation,
   Secret Manager wiring, least-privilege service accounts, and alerts.
4. **Staging soak:** generate seven consecutive staging dates; inspect content,
   retries, expiry, and player submission flows.
5. **Production launch:** pre-generate at least three dates, enable scheduler,
   set `CONTENT_MODE=firestore`, and retain the seed mode only for demos/tests.

## Acceptance criteria

- A published date has exactly three valid challenges for each supported track.
- Every player requesting the same `(date, track)` gets the same three IDs.
- Answers and explanations are never included in unresolved client payloads.
- A failed/retried job cannot create a partial or different published stack.
- Submitting an answer works after an API restart and Cloud Run scale-to-zero.
- Cleanup removes only expired stack/challenge pairs and leaves active runs
  gradeable for the declared retention period.
- Local tests continue to run without Firebase or an OpenAI key.
