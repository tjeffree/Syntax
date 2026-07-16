// Shareable emoji grid (GDD §4). Obfuscates answers, brags about performance.
import type { ChallengeResult, CompleteResponse } from "./types";
import { dailyNumber, formatMs } from "./util";

const NUM = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"];
const TYPE_LABEL: Record<string, string> = {
  "bug-spot": "Spot the Bug",
  parsons: "Parsons Problem",
  "big-o": "Time Complexity",
};

function mark(r: ChallengeResult): string {
  if (r.correct && r.attempts <= 1) return "🟩";
  if (r.correct) return "🟨";
  return "🟥";
}

export function buildShareText(result: CompleteResponse, level: number): string {
  const track = result.track[0].toUpperCase() + result.track.slice(1);
  const lines = [
    `Syntax Daily #${dailyNumber(result.date)}`,
    `${track} Track: Lvl ${level}`,
    `⏱ ${formatMs(result.total_ms)}`,
    ...result.results.map(
      (r, i) => `${NUM[i + 1] ?? `${i + 1}.`} ${mark(r)} (${TYPE_LABEL[r.type] ?? r.type})`
    ),
  ];
  return lines.join("\n");
}
