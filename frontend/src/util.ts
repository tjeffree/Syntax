// Time / date helpers. The daily stack is keyed by the player's LOCAL calendar
// date (GDD §4 clarification).

export function localDate(d = new Date()): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function formatMs(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000));
  const mm = String(Math.floor(total / 60)).padStart(2, "0");
  const ss = String(total % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

export function msUntilLocalMidnight(now = new Date()): number {
  const next = new Date(now);
  next.setHours(24, 0, 0, 0);
  return next.getTime() - now.getTime();
}

export function formatCountdown(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const h = String(Math.floor(total / 3600)).padStart(2, "0");
  const m = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
  const s = String(total % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

// Sequential "Syntax Daily #N" number, counting days from launch.
export function dailyNumber(date: string): number {
  const epoch = Date.UTC(2026, 0, 1); // 2026-01-01 => #1
  const [y, m, d] = date.split("-").map(Number);
  const days = Math.round((Date.UTC(y, m - 1, d) - epoch) / 86_400_000);
  return days + 1;
}
