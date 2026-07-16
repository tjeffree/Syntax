import type { Auth } from "./auth";
import type {
  AnswerPayload,
  CompleteResponse,
  DailyResponse,
  LeaderboardResponse,
  MeResponse,
  SubmitResponse,
  Track,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export class Api {
  constructor(private auth: Auth) {}

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const token = await this.auth.getToken();
    const res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...(init.headers ?? {}),
      },
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      } catch {
        /* keep statusText */
      }
      throw new ApiError(res.status, detail);
    }
    return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
  }

  me(): Promise<MeResponse> {
    return this.request<MeResponse>("/me");
  }

  daily(date: string, track: Track): Promise<DailyResponse> {
    return this.request<DailyResponse>(`/daily/${date}?track=${track}`);
  }

  submit(args: {
    date: string;
    track: Track;
    challengeId: string;
    answerPayload: AnswerPayload;
    clientElapsedMs: number;
  }): Promise<SubmitResponse> {
    return this.request<SubmitResponse>("/submit", {
      method: "POST",
      body: JSON.stringify({
        date: args.date,
        track: args.track,
        challenge_id: args.challengeId,
        answer_payload: args.answerPayload,
        client_elapsed_ms: args.clientElapsedMs,
      }),
    });
  }

  complete(date: string, track: Track): Promise<CompleteResponse> {
    return this.request<CompleteResponse>("/complete", {
      method: "POST",
      body: JSON.stringify({ date, track }),
    });
  }

  leaderboard(date: string, track: Track, scope = "global"): Promise<LeaderboardResponse> {
    return this.request<LeaderboardResponse>(
      `/leaderboard/${date}?track=${track}&scope=${scope}`
    );
  }
}
