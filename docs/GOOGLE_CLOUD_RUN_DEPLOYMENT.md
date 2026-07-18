# Deploy Syntax daily content to Google Cloud Run

This runbook deploys the FastAPI service plus two Cloud Run Jobs:

- `syntax-generate-daily` creates and atomically publishes the next day’s six
  challenges (three Python, three JavaScript).
- `syntax-cleanup-content` deletes generated stacks outside the retention
  window.

It uses a Cloud Scheduler HTTP target to execute the generation Job through
the Cloud Run API. This is intentionally not a public API endpoint.

Run the commands from PowerShell at the repository root. Set the four values
below before starting; keep the API, Cloud Run, and Firestore locations close
to each other.

```powershell
$PROJECT_ID = "YOUR_GCP_PROJECT_ID"
$REGION = "europe-west2"
$FIRESTORE_LOCATION = "europe-west2"
$FRONTEND_ORIGIN = "https://YOUR_PROJECT_ID.web.app"
```

## 1. Prepare the project

Authenticate, select the project, enable billing, and enable the services used
by this deployment:

```powershell
gcloud auth login
gcloud auth application-default login
gcloud config set project $PROJECT_ID

gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com secretmanager.googleapis.com cloudscheduler.googleapis.com iamcredentials.googleapis.com
```

If the Firebase project and Firestore database do not already exist, create a
Native-mode Firestore database once. Do not run this against a project that
already has Firestore configured.

```powershell
gcloud firestore databases create --location=$FIRESTORE_LOCATION --type=firestore-native
```

Enable Firebase Authentication providers and deploy the repository’s Firestore
rules as described in [FIREBASE_SETUP.md](FIREBASE_SETUP.md). The browser must
never have direct access to `challenges` or `dailyStacks`.

## 2. Create identities and grant only required roles

```powershell
$API_SA = "syntax-api@$PROJECT_ID.iam.gserviceaccount.com"
$GENERATOR_SA = "syntax-generator@$PROJECT_ID.iam.gserviceaccount.com"
$SCHEDULER_SA = "syntax-scheduler@$PROJECT_ID.iam.gserviceaccount.com"

gcloud iam service-accounts create syntax-api --display-name="Syntax API Cloud Run service"
gcloud iam service-accounts create syntax-generator --display-name="Syntax daily generator job"
gcloud iam service-accounts create syntax-scheduler --display-name="Syntax Cloud Scheduler invoker"

gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$API_SA" --role="roles/datastore.user"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$GENERATOR_SA" --role="roles/datastore.user"
```

`roles/datastore.user` permits the runtime identities to use Firestore through
the Admin SDK. Do not grant `Owner`, `Editor`, or project-wide Secret Manager
access. The generator alone receives access to the OpenAI key in the next step.

## 3. Store the OpenAI key

The safest simple method is the Google Cloud Console: **Secret Manager → Create
secret**, name it `openai-api-key`, and paste the API key as version 1. If using
the CLI, create the secret from a temporary file that is outside the repository
and remove it immediately after the command:

```powershell
gcloud secrets create openai-api-key --replication-policy=automatic
gcloud secrets versions add openai-api-key --data-file="C:\secure\openai-api-key.txt"
```

Grant only the generator identity access:

```powershell
gcloud secrets add-iam-policy-binding openai-api-key --member="serviceAccount:$GENERATOR_SA" --role="roles/secretmanager.secretAccessor"
```

The API service does not receive `OPENAI_API_KEY` and therefore cannot make
generation calls on behalf of players.

## 4. Build and publish the container image

Create the Artifact Registry repository once, then build the existing backend
Dockerfile using Cloud Build:

```powershell
gcloud artifacts repositories create syntax --repository-format=docker --location=$REGION --description="Syntax containers"

$TAG = (git rev-parse --short HEAD)
$IMAGE = "$REGION-docker.pkg.dev/$PROJECT_ID/syntax/syntax-api:$TAG"
gcloud builds submit backend --tag=$IMAGE
```

If the Artifact Registry repository already exists, the create command returns
an error; it is safe to continue with the build command.

## 5. Deploy the player-facing API service

The API is public at the Cloud Run edge because it verifies Firebase ID tokens
inside FastAPI. Its data access is still limited to its service account.

```powershell
gcloud run deploy syntax-api `
  --image=$IMAGE `
  --region=$REGION `
  --service-account=$API_SA `
  --allow-unauthenticated `
  --set-env-vars="AUTH_MODE=firebase,STORE_MODE=firestore,CONTENT_MODE=firestore,FIREBASE_PROJECT_ID=$PROJECT_ID,CORS_ORIGINS=$FRONTEND_ORIGIN,DAILY_STACK_RETENTION_DAYS=7" `
  --min=0 `
  --max=10

$API_URL = gcloud run services describe syntax-api --region=$REGION --format='value(status.url)'
Invoke-WebRequest "$API_URL/health" | Select-Object -ExpandProperty Content
```

Expected `/health` fields include `auth_mode: firebase` and `store_mode:
firestore`. A `503` from `/daily/<future-date>` before publishing is expected.
Set the frontend’s `VITE_API_BASE` to `$API_URL` and deploy Firebase Hosting
after the daily jobs have published their initial content.

## 6. Deploy the generation and cleanup Jobs

The two jobs use the same image, overriding only its command. `OPENAI_MODEL` is
configurable; `gpt-5.6-luna` is the default cost-sensitive model in the code.

```powershell
gcloud run jobs deploy syntax-generate-daily `
  --image=$IMAGE `
  --region=$REGION `
  --service-account=$GENERATOR_SA `
  --command=python `
  --args=-m,app.jobs.generate_daily `
  --tasks=1 `
  --max-retries=2 `
  --task-timeout=10m `
  --set-env-vars="CONTENT_MODE=firestore,FIREBASE_PROJECT_ID=$PROJECT_ID,DAILY_STACK_RETENTION_DAYS=7,OPENAI_MODEL=gpt-5.6-luna" `
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest"

gcloud run jobs deploy syntax-cleanup-content `
  --image=$IMAGE `
  --region=$REGION `
  --service-account=$GENERATOR_SA `
  --command=python `
  --args=-m,app.jobs.cleanup_expired_content `
  --tasks=1 `
  --max-retries=1 `
  --task-timeout=5m `
  --set-env-vars="CONTENT_MODE=firestore,FIREBASE_PROJECT_ID=$PROJECT_ID,DAILY_STACK_RETENTION_DAYS=7"
```

Run the generator manually for three dates before enabling the scheduler. Check
the Job execution logs and inspect the Firestore manifests before proceeding.

```powershell
gcloud run jobs execute syntax-generate-daily --region=$REGION --args=-m,app.jobs.generate_daily,--date=2026-07-20 --wait
gcloud run jobs execute syntax-generate-daily --region=$REGION --args=-m,app.jobs.generate_daily,--date=2026-07-21 --wait
gcloud run jobs execute syntax-generate-daily --region=$REGION --args=-m,app.jobs.generate_daily,--date=2026-07-22 --wait
```

Use real upcoming dates rather than the examples. Each successfully published
manifest must have `status: published`, both track arrays, and three IDs per
track. A re-execution for the same date exits safely without replacing an
already-published stack.

## 7. Schedule generation and cleanup

Grant the Scheduler identity permission to execute each Job:

```powershell
gcloud run jobs add-iam-policy-binding syntax-generate-daily --region=$REGION --member="serviceAccount:$SCHEDULER_SA" --role="roles/run.invoker"
gcloud run jobs add-iam-policy-binding syntax-cleanup-content --region=$REGION --member="serviceAccount:$SCHEDULER_SA" --role="roles/run.invoker"
```

Cloud Scheduler calls the Cloud Run v2 API, so use an OAuth token rather than
an OIDC token. Generate the next game date at 09:45 UTC, which is before
midnight in UTC+14; this preserves the game’s local-date rule.

```powershell
$GENERATE_URI = "https://run.googleapis.com/v2/projects/$PROJECT_ID/locations/$REGION/jobs/syntax-generate-daily:run"
$CLEANUP_URI = "https://run.googleapis.com/v2/projects/$PROJECT_ID/locations/$REGION/jobs/syntax-cleanup-content:run"

gcloud scheduler jobs create http syntax-generate-daily `
  --location=$REGION `
  --schedule="45 9 * * *" `
  --time-zone="Etc/UTC" `
  --uri=$GENERATE_URI `
  --http-method=POST `
  --headers="Content-Type=application/json" `
  --message-body="{}" `
  --oauth-service-account-email=$SCHEDULER_SA

gcloud scheduler jobs create http syntax-cleanup-content `
  --location=$REGION `
  --schedule="15 10 * * *" `
  --time-zone="Etc/UTC" `
  --uri=$CLEANUP_URI `
  --http-method=POST `
  --headers="Content-Type=application/json" `
  --message-body="{}" `
  --oauth-service-account-email=$SCHEDULER_SA
```

Test each Scheduler job after creation:

```powershell
gcloud scheduler jobs run syntax-generate-daily --location=$REGION
gcloud scheduler jobs run syntax-cleanup-content --location=$REGION
gcloud run jobs executions list --job=syntax-generate-daily --region=$REGION
```

## 8. Post-deployment checks and operations

1. Sign in through the deployed frontend and request today’s Python and
   JavaScript stacks. Confirm each has exactly three challenges and no `answer`
   field.
2. Submit known answers, complete a run, and verify Firestore writes user, run,
   and leaderboard documents.
3. Review Cloud Run Job logs for `published` and Cloud Scheduler execution
   history for HTTP 2xx responses.
4. Create an alert for failed Job executions and an alert/log metric for API
   responses with `503` and `daily stack` in the detail.
5. To deploy code updates, repeat steps 4–6 with a new `$TAG`; use `gcloud run
   jobs deploy` again to update each Job image.

Cloud Run Jobs are appropriate here because they run to completion rather than
serve HTTP. Cloud Scheduler authenticates to Google APIs with an OAuth service
account token, and that identity needs `roles/run.invoker` on the target Job.
See Google’s [Cloud Run Jobs guide](https://cloud.google.com/run/docs/create-jobs),
[job execution guide](https://cloud.google.com/run/docs/execute/jobs), and
[Cloud Scheduler authentication guide](https://cloud.google.com/scheduler/docs/http-target-auth).
