// Pluggable auth, mirroring the backend (GDD §6, open question: anonymous play).
//
//  - dev mode: a stable random uid kept in localStorage; token is "dev:<uid>".
//    Powers anonymous play locally with no Firebase project.
//  - firebase mode: Firebase Anonymous Auth (later linkable to Google/GitHub
//    without losing progress). `firebase` is imported lazily so it's code-split
//    into its own chunk and only fetched when firebase mode is active.

export interface Auth {
  getToken(): Promise<string>;
  signOut(): Promise<void>;
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
  private uid = ensureAnonUid();
  async getToken(): Promise<string> {
    return `dev:${this.uid}`;
  }
  async signOut(): Promise<void> {
    localStorage.removeItem(UID_KEY);
    this.uid = ensureAnonUid();
  }
}

class FirebaseAuthAdapter implements Auth {
  private auth: any;
  private ready: Promise<void>;

  constructor() {
    this.ready = this.init();
  }

  private async init(): Promise<void> {
    // Dynamic imports so Firebase is code-split into its own chunk and only
    // fetched in firebase mode. Vite resolves and bundles these at build time
    // (firebase is a declared dependency), so no bare specifier reaches the
    // browser.
    const { initializeApp } = await import("firebase/app");
    const fbAuth = await import("firebase/auth");
    const app = initializeApp({
      apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
      authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
      projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
      appId: import.meta.env.VITE_FIREBASE_APP_ID,
    });
    this.auth = fbAuth.getAuth(app);
    if (!this.auth.currentUser) {
      await fbAuth.signInAnonymously(this.auth);
    }
  }

  async getToken(): Promise<string> {
    await this.ready;
    return this.auth.currentUser.getIdToken();
  }

  async signOut(): Promise<void> {
    await this.ready;
    const fbAuth = await import("firebase/auth");
    await fbAuth.signOut(this.auth);
  }
}

export function createAuth(): Auth {
  const mode = import.meta.env.VITE_AUTH_MODE ?? "dev";
  return mode === "firebase" ? new FirebaseAuthAdapter() : new DevAuth();
}
