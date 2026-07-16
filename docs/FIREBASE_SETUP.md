# Firebase setup — do this when you're ready to go beyond local dev

The app runs **fully locally with no Firebase project** (anonymous dev auth +
a JSON-file store). Follow this guide only when you want real Google/GitHub
sign-in, a shared Firestore database, and hosting.

Nothing in the codebase changes — you flip a few environment variables and
install two packages. `git grep AUTH_MODE STORE_MODE` shows every switch.

---

## 0. Prerequisites

```bash
npm install -g firebase-tools
firebase login
```

---

## 1. Create the Firebase project

1. Go to <https://console.firebase.google.com> → **Add project**.
2. Name it (e.g. `syntax-game`). Google Analytics is optional.
3. Note the **Project ID** (e.g. `syntax-game-1a2b3`) — you'll paste it in a few places.

---

## 2. Enable Authentication (GDD §6)

Console → **Build → Authentication → Get started**, then under **Sign-in method**
enable:

- **Anonymous** — powers "play before sign-in" (GDD open question: yes).
- **Google**.
- **GitHub** — the natural identity for a developer audience. You'll need to
  register an OAuth app at <https://github.com/settings/developers>:
  - Authorization callback URL: the one Firebase shows you
    (`https://<project-id>.firebaseapp.com/__/auth/handler`).
  - Copy the GitHub **Client ID** and **Client secret** back into Firebase.

Later you can **link** an anonymous account to Google/GitHub so a player keeps
their progress after signing in (Firebase supports this natively).

---

## 3. Enable Cloud Firestore

Console → **Build → Firestore Database → Create database**.

- Start in **production mode** (our rules lock it down; the backend uses the
  Admin SDK, which bypasses rules).
- Pick a region close to your users.

---

## 4. Wire up the backend (FastAPI → Firebase Admin)

The backend needs a **service account** to verify ID tokens and write Firestore.

1. Console → **Project settings → Service accounts → Generate new private key**.
   Save the JSON as `backend/serviceAccount.json` (already git-ignored).
2. Install the Firebase extras and set env vars:

   ```bash
   cd backend
   pip install -r requirements-firebase.txt      # adds firebase-admin
   ```

   In `backend/.env`:

   ```ini
   AUTH_MODE=firebase
   STORE_MODE=firestore
   FIREBASE_CREDENTIALS=./serviceAccount.json
   FIREBASE_PROJECT_ID=<your-project-id>
   CORS_ORIGINS=http://localhost:5173,https://<your-project-id>.web.app
   ```

3. Restart the server. `GET /health` should report
   `"auth_mode":"firebase","store_mode":"firestore"`.

> On Google Cloud Run you don't need the key file — the runtime service account
> is picked up automatically. Leave `FIREBASE_CREDENTIALS` unset there.

---

## 5. Wire up the frontend (Firebase JS SDK)

1. Console → **Project settings → General → Your apps → Web app (`</>`)**.
   Register an app and copy the config values.
2. Install the SDK (only needed in firebase mode; kept out of the default
   install to protect the bundle budget, GDD §7):

   ```bash
   cd frontend
   npm install firebase
   ```

3. In `frontend/.env.local`:

   ```ini
   VITE_AUTH_MODE=firebase
   VITE_API_BASE=https://<your-backend-url>        # Cloud Run URL, or http://localhost:8000
   VITE_FIREBASE_API_KEY=...
   VITE_FIREBASE_AUTH_DOMAIN=<project-id>.firebaseapp.com
   VITE_FIREBASE_PROJECT_ID=<project-id>
   VITE_FIREBASE_APP_ID=...
   ```

The frontend already loads `firebase/auth` and `firebase/firestore` lazily and
tree-shaken (GDD §6); dev builds never pull it in.

---

## 6. Deploy Firestore security rules

The rules live in `firebase/firestore.rules` (GDD §6 sketch: clients get no
write access to score-bearing collections; leaderboards are world-readable).

```bash
cd firebase
cp .firebaserc.example .firebaserc     # then edit in your project id
firebase deploy --only firestore:rules
```

---

## 7. Host the frontend (optional)

```bash
cd frontend && npm run build
cd ../firebase && firebase deploy --only hosting
```

`firebase.json` already points hosting at `../frontend/dist` with an SPA
rewrite.

---

## 8. Deploy the backend to Cloud Run (front-runner, GDD §6)

The backend is a plain container (config via env vars — host-agnostic).

```bash
cd backend
gcloud run deploy syntax-api \
  --source . \
  --region <your-region> \
  --allow-unauthenticated \
  --set-env-vars AUTH_MODE=firebase,STORE_MODE=firestore,FIREBASE_PROJECT_ID=<project-id>,CORS_ORIGINS=https://<project-id>.web.app
```

(Add a minimal `Dockerfile` or rely on Cloud Run's buildpacks — `uvicorn
app.main:app --host 0.0.0.0 --port $PORT` is the start command. Set
`--min-instances=1` to avoid cold starts for pennies.)

Then point the frontend's `VITE_API_BASE` at the Cloud Run URL and redeploy
hosting.

---

## Local testing with the Firebase Emulator Suite (no cloud cost)

If you want to exercise firebase mode without touching a real project:

```bash
cd firebase
firebase emulators:start          # auth :9099, firestore :8080, UI on :4000
```

Set `FIRESTORE_EMULATOR_HOST=localhost:8080` and
`FIREBASE_AUTH_EMULATOR_HOST=localhost:9099` in the backend environment; the
Admin SDK auto-detects the emulators.

---

## Switching back to local dev

Set `AUTH_MODE=dev` and `STORE_MODE=memory` (backend) and `VITE_AUTH_MODE=dev`
(frontend). No Firebase project required. That's the default in every
`.env.example`.
