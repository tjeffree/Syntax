// Maps a challenge type to its component factory (GDD §2: modular, additive).
import type { ChallengeType } from "../types";
import { createBigO } from "./bigo";
import { createBugSpot } from "./bugspot";
import { createParsons } from "./parsons";
import type { ChallengeFactory } from "./types";

const REGISTRY: Record<ChallengeType, ChallengeFactory> = {
  "bug-spot": createBugSpot,
  "big-o": createBigO,
  parsons: createParsons,
};

export const TYPE_TITLE: Record<ChallengeType, string> = {
  "bug-spot": "spot the bug",
  parsons: "parsons problem",
  "big-o": "time complexity",
};

export function createChallenge(
  type: ChallengeType,
  payload: unknown,
  challengeId: string
) {
  return REGISTRY[type](payload, challengeId);
}
