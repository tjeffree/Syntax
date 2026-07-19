// Pluggable auth, mirroring the backend (GDD §6, open question: anonymous play).
//
//  - dev mode: a stable random uid kept in localStorage; token is "dev:<uid>".
//    Powers anonymous play locally with no Firebase project.
//  - firebase mode: Firebase Anonymous Auth, upgradable in place to Google /
//    GitHub without losing progress. `firebase` is imported lazily so it's
//    code-split into its own chunk and only fetched when firebase mode is active.

export type ProviderId = "google" | "github";

export interface Auth {
  getToken(): Promise<string>;
  signOut(): Promise<void>;
  // Interactive sign-in providers this adapter supports. Empty in dev mode,
  // where the only identity is a local anonymous uid.
  readonly providers: ProviderId[];
  // Sign in with a provider. If the current user is anonymous the account is
  // upgraded in place (same uid → progress preserved); resolves once auth state
  // has settled. Throws AuthCancelled if the user dismisses the popup.
  signIn(provider: ProviderId): Promise<void>;
}

// Thrown when the user backs out of the sign-in popup — the caller treats this
// as a no-op rather than an error worth surfacing.
export class AuthCancelled extends Error {
  constructor() {
    super("sign-in cancelled");
    this.name = "AuthCancelled";
  }
}

const UID_KEY = "syntax.anonUid";

function ensureAnonUid(): string {
  let uid = localStorage.getItem(UID_KEY);
  if (!uid) {
    uid =
      (crypto.randomUUID?.() ??
        Math.random().toString(36).slice(2) + Date.now().toString(36));
    localStorage.setItem(UID_KEY, uid);
  }
  return uid;
}

class DevAuth implements Auth {
  readonly providers: ProviderId[] = []; // no real IdP without a Firebase project
  private uid = ensureAnonUid();
  async getToken(): Promise<string> {
    return `dev:${this.uid}`;
  }
  async signIn(): Promise<void> {
    throw new Error("interactive sign-in is unavailable in dev auth mode");
  }
  async signOut(): Promise<void> {
    localStorage.removeItem(UID_KEY);
    this.uid = ensureAnonUid();
  }
}

class FirebaseAuthAdapter implements Auth {
  readonly providers: ProviderId[] = ["google", "github"];
  private auth: any;
  private fb!: typeof import("firebase/auth");
  private ready: Promise<void>;

  constructor() {
    this.ready = this.init();
  }

  private async init(): Promise<void> {
    // Dynamic imports so Firebase is code-split into its own chunk and only
    // fetched in firebase mode. Vite resolves and bundles these at build time
    // (firebase is a declared dependency), so no bare specifier reaches the
    // browser. The auth module is cached on the instance so getToken (called on
    // every API request), signIn and signOut don't re-import it.
    const { initializeApp } = await import("firebase/app");
    this.fb = await import("firebase/auth");
    const app = initializeApp({
      apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
      authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
      projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
      appId: import.meta.env.VITE_FIREBASE_APP_ID,
    });
    this.auth = this.fb.getAuth(app);
    // Wait for Firebase to restore any persisted session before deciding whether
    // to start an anonymous one. getAuth() returns with currentUser === null and
    // only populates it asynchronously; without this we'd sign in anonymously on
    // every load and clobber the signed-in Google/GitHub session (i.e. the user
    // would appear signed out and have to sign in again).
    await this.auth.authStateReady();
    await this.ensureUser();
  }

  // Guarantee there's always an identity to mint a token for: fall back to
  // anonymous play whenever no user is signed in (fresh visit, or just after
  // sign-out). Mirrors DevAuth, which always has a local anon uid.
  private async ensureUser(): Promise<void> {
    if (!this.auth.currentUser) {
      await this.fb.signInAnonymously(this.auth);
    }
  }

  async getToken(): Promise<string> {
    await this.ready;
    await this.ensureUser();
    return this.auth.currentUser.getIdToken();
  }

  async signIn(id: ProviderId): Promise<void> {
    await this.ready;
    const ctor =
      id === "google" ? this.fb.GoogleAuthProvider : this.fb.GithubAuthProvider;
    const provider = new ctor();
    const user = this.auth.currentUser;

    try {
      if (user && user.isAnonymous) {
        // Upgrade the anonymous account in place — same uid, so runs, streak and
        // XP keyed to it on the backend are preserved (GDD §6).
        await this.fb.linkWithPopup(user, provider);
      } else {
        await this.fb.signInWithPopup(this.auth, provider);
      }
    } catch (err: any) {
      const code = err?.code;
      if (
        code === "auth/popup-closed-by-user" ||
        code === "auth/cancelled-popup-request"
      ) {
        throw new AuthCancelled();
      }
      if (
        code === "auth/credential-already-in-use" ||
        code === "auth/email-already-in-use"
      ) {
        // This Google/GitHub identity already owns a Firebase account. Two
        // accounts can't be merged, so we sign into the existing one — its
        // history is the source of truth; anonymous progress on this device is
        // left behind.
        const credential = ctor.credentialFromError(err);
        if (credential) {
          await this.fb.signInWithCredential(this.auth, credential);
          return;
        }
      }
      throw err;
    }
  }

  async signOut(): Promise<void> {
    await this.ready;
    await this.fb.signOut(this.auth);
    await this.ensureUser(); // back to anonymous play, not a token-less limbo
  }
}

export function createAuth(): Auth {
  const mode = import.meta.env.VITE_AUTH_MODE ?? "dev";
  return mode === "firebase" ? new FirebaseAuthAdapter() : new DevAuth();
}
