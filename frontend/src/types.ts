// Mirrors the backend API models (app/models.py). Kept hand-written and small.

export type Track = "python" | "javascript";
export type ChallengeType = "bug-spot" | "parsons" | "big-o";

export interface BugSpotPayload {
  language: string;
  code: string;
}
export interface ParsonsBlock {
  id: string;
  code: string;
}
export interface ParsonsPayload {
  language: string;
  blocks: ParsonsBlock[];
  indent?: boolean;
  maxIndent?: number;
}
export interface BigOPayload {
  language: string;
  code: string;
  prompt: "time" | "space";
  options: string[];
}

export interface ChallengePublic {
  id: string;
  type: ChallengeType;
  track: Track;
  difficulty: number;
  payload: BugSpotPayload | ParsonsPayload | BigOPayload;
  attempts_used: number;
  resolved: boolean;
  correct: boolean | null;
  explanation: string | null;
}

export interface DailyResponse {
  date: string;
  track: Track;
  stack_id: string;
  attempts_per_challenge: number;
  started_at: string;
  completed: boolean;
  challenges: ChallengePublic[];
}

export interface SubmitResponse {
  correct: boolean;
  resolved: boolean;
  attempts_remaining: number;
  score: number | null;
  explanation: string | null;
}

export interface StreakInfo {
  current: number;
  longest: number;
  freezes_available: number;
  last_played_date: string | null;
  freeze_used?: boolean;
}
export interface TrackXp {
  track: Track;
  xp_before: number;
  xp_after: number;
  xp_delta: number;
  level_before: number;
  level_after: number;
}
export interface ChallengeResult {
  challenge_id: string;
  type: ChallengeType;
  correct: boolean;
  attempts: number;
  score: number;
  elapsed_ms: number;
}
export interface CompleteResponse {
  date: string;
  track: Track;
  score: number;
  total_ms: number;
  results: ChallengeResult[];
  streak: StreakInfo;
  xp: TrackXp;
  quarantined: boolean;
  leaderboard_rank: number | null;
}

export interface LeaderboardEntry {
  rank: number;
  uid: string;
  handle: string;
  score: number;
  total_ms: number;
  track: Track;
  is_me: boolean;
}
export interface LeaderboardResponse {
  date: string;
  scope: string;
  entries: LeaderboardEntry[];
  me: LeaderboardEntry | null;
}

export interface MeResponse {
  uid: string;
  handle: string;
  display_name: string;
  anonymous: boolean;
  created_at: string;
  streak: StreakInfo;
  tracks: Record<string, { xp: number; level: number }>;
}

// Answer payloads produced by challenge components and sent to /submit.
export type AnswerPayload =
  | { line: number }
  | { choice: string }
  | { solution: { id: string; indent: number }[] };
