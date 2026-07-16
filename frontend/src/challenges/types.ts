import type { AnswerPayload } from "../types";

// Each question type is a self-contained component implementing this interface
// (GDD §2: "one component + a server-side validator, registered against a
// shared challenge schema"). New types are additive.
export interface ChallengeComponent {
  element: HTMLElement;
  /** Current answer, or null if the player hasn't produced a complete one. */
  getAnswer(): AnswerPayload | null;
  /** Freeze interaction once the challenge is resolved. */
  setEnabled(enabled: boolean): void;
}

export type ChallengeFactory = (payload: unknown, challengeId: string) => ChallengeComponent;
