import { Api, ApiError } from "./api";
import type { Auth } from "./auth";
import { createChallenge, TYPE_TITLE } from "./challenges/registry";
import type { ChallengeComponent } from "./challenges/types";
import { clear, h, mount } from "./dom";
import { buildShareText } from "./share";
import type {
  ChallengePublic,
  CompleteResponse,
  DailyResponse,
  MeResponse,
  Track,
} from "./types";
import {
  formatCountdown,
  formatMs,
  localDate,
  msUntilLocalMidnight,
} from "./util";

const TRACKS: Track[] = ["python", "javascript"];
const TRACK_KEY = "syntax.track";

export class App {
  private api: Api;
  private root: HTMLElement;

  private me: MeResponse | null = null;
  private track: Track;
  private date = localDate();

  private daily: DailyResponse | null = null;
  private index = 0;
  private component: ChallengeComponent | null = null;

  private playStart = 0;
  private timerHandle: number | null = null;
  private countdownHandle: number | null = null;

  private appbar!: HTMLElement;
  private view!: HTMLElement;

  constructor(root: HTMLElement, auth: Auth) {
    this.root = root;
    this.api = new Api(auth);
    const saved = localStorage.getItem(TRACK_KEY) as Track | null;
    this.track = saved && TRACKS.includes(saved) ? saved : "python";
  }

  async boot(): Promise<void> {
    const shell = h("div", { class: "shell" });
    this.appbar = h("header", { class: "appbar" });
    this.view = h("main", {});
    shell.append(this.appbar, this.view);
    mount(this.root, shell);

    this.setStatus("connecting…");
    try {
      this.me = await this.api.me();
    } catch (e) {
      this.renderFatal(e);
      return;
    }
    this.renderAppbar();
    await this.loadDaily();
  }

  // ---- appbar --------------------------------------------------------- #
  private renderAppbar(): void {
    const s = this.me?.streak;
    const lvl = this.me?.tracks[this.track]?.level ?? 1;

    const tabs = h("div", { class: "tabs", role: "tablist" });
    for (const t of TRACKS) {
      const tab = h(
        "button",
        {
          class: "tab",
          role: "tab",
          "aria-selected": String(t === this.track),
          onclick: () => this.switchTrack(t),
        },
        t
      );
      tabs.append(tab);
    }

    mount(
      this.appbar,
      h("span", { class: "brand" }, "syntax"),
      tabs,
      h("span", { class: "spacer" }),
      s && s.current > 0
        ? h("span", { class: "badge badge-streak", title: "daily streak" }, `⚑ ${s.current}`)
        : null,
      h("span", { class: "badge badge-lvl mono", title: `${this.track} level` }, `lvl ${lvl}`),
      h(
        "button",
        { class: "iconbtn", title: "toggle theme", "aria-label": "toggle theme", onclick: () => toggleTheme() },
        "◐"
      )
    );
  }

  private async switchTrack(t: Track): Promise<void> {
    if (t === this.track) return;
    this.track = t;
    localStorage.setItem(TRACK_KEY, t);
    this.renderAppbar();
    await this.loadDaily();
  }

  // ---- daily load ----------------------------------------------------- #
  private async loadDaily(): Promise<void> {
    this.stopTimers();
    this.setStatus("fetching daily stack…");
    try {
      this.daily = await this.api.daily(this.date, this.track);
    } catch (e) {
      this.renderError(e);
      return;
    }
    if (this.daily.completed) {
      // Finished today — recover the (idempotent) summary and show results.
      try {
        const result = await this.api.complete(this.date, this.track);
        this.applyCompletionToMe(result);
        this.renderResults(result);
      } catch (e) {
        this.renderError(e);
      }
      return;
    }
    this.playStart = Date.now();
    this.index = this.firstUnresolvedIndex();
    this.renderPlay();
    this.startTimer();
  }

  private firstUnresolvedIndex(): number {
    const i = this.daily!.challenges.findIndex((c) => !c.resolved);
    return i === -1 ? 0 : i;
  }

  // ---- play screen ---------------------------------------------------- #
  private renderPlay(): void {
    const daily = this.daily!;
    const ch = daily.challenges[this.index];

    const playbar = h(
      "div",
      { class: "playbar" },
      this.renderDots(),
      h("span", { class: "timer mono", id: "timer" }, "00:00")
    );

    const panel = h("div", { class: "panel" });
    const diff = h("span", { class: "badge badge-lvl", title: "difficulty" }, `d${ch.difficulty}`);
    panel.append(
      h(
        "div",
        { class: "panel-head" },
        h("span", { class: "panel-title" }, TYPE_TITLE[ch.type]),
        h("span", { class: "spacer", style: "flex:1" }),
        diff
      )
    );

    this.component = createChallenge(ch.type, ch.payload, ch.id);
    const resultSlot = h("div", { id: "result-slot" });
    const btnRow = h("div", { class: "btn-row", id: "btn-row" });
    panel.append(h("div", { class: "panel-body" }, this.component.element, resultSlot, btnRow));

    mount(this.view, playbar, panel);
    this.renderPlayControls(ch, ch.attempts_used, ch.resolved);
  }

  private renderDots(): HTMLElement {
    const dots = h("div", { class: "dots" });
    this.daily!.challenges.forEach((c, i) => {
      let cls = "dot";
      let glyph = String(i + 1);
      if (c.resolved && c.correct && c.attempts_used <= 1) {
        cls += " correct";
        glyph = "✓";
      } else if (c.resolved && c.correct) {
        cls += " second";
        glyph = "✓";
      } else if (c.resolved) {
        cls += " fail";
        glyph = "✕";
      }
      if (i === this.index && !c.resolved) cls += " active";
      dots.append(h("span", { class: cls, title: `challenge ${i + 1}` }, glyph));
    });
    return dots;
  }

  private renderPlayControls(_ch: ChallengePublic, attemptsUsed: number, resolved: boolean): void {
    const btnRow = this.view.querySelector("#btn-row") as HTMLElement;
    clear(btnRow);
    const attemptsLeft = this.daily!.attempts_per_challenge - attemptsUsed;

    if (resolved) {
      this.component?.setEnabled(false);
      const isLast = this.index >= this.daily!.challenges.length - 1;
      const nextBtn = h(
        "button",
        { class: "btn btn-primary", onclick: () => this.next() },
        isLast ? "see results ▸" : "next ▸"
      );
      btnRow.append(nextBtn);
      return;
    }

    const info = h(
      "span",
      { class: "muted mono", style: "margin-right:auto" },
      `${attemptsLeft} ${attemptsLeft === 1 ? "attempt" : "attempts"} left`
    );
    const lockBtn = h("button", { class: "btn btn-primary", onclick: () => this.submit() }, "lock in");
    btnRow.append(info, lockBtn);
  }

  private async submit(): Promise<void> {
    const ch = this.daily!.challenges[this.index];
    const answer = this.component!.getAnswer();
    if (answer == null) {
      this.flashResult("select an answer first", "fail");
      return;
    }
    const btnRow = this.view.querySelector("#btn-row") as HTMLElement;
    (btnRow.querySelector(".btn-primary") as HTMLButtonElement)?.setAttribute("disabled", "");

    try {
      const res = await this.api.submit({
        date: this.date,
        track: this.track,
        challengeId: ch.id,
        answerPayload: answer,
        clientElapsedMs: Date.now() - this.playStart,
      });

      ch.attempts_used += 1;
      ch.resolved = res.resolved;
      ch.correct = res.correct;
      if (res.resolved) ch.explanation = res.explanation;

      // sound cue for a correct lock-in (muted by default; only on gesture)
      if (res.correct) playClick();

      this.showResult(res.correct, ch.attempts_used, res.resolved, res.explanation, res.score);
      const playbarEl = this.view.querySelector<HTMLElement>(".playbar");
      if (playbarEl) {
        mount(playbarEl, this.renderDots(), h("span", { class: "timer mono", id: "timer" }, this.currentTimerText()));
      }
      this.renderPlayControls(ch, ch.attempts_used, ch.resolved);
    } catch (e) {
      this.flashResult(e instanceof ApiError ? e.message : "request failed — try again", "fail");
      (btnRow.querySelector(".btn-primary") as HTMLButtonElement)?.removeAttribute("disabled");
    }
  }

  private showResult(
    correct: boolean,
    attempts: number,
    resolved: boolean,
    explanation: string | null,
    score: number | null
  ): void {
    const slot = this.view.querySelector("#result-slot") as HTMLElement;
    let cls: string;
    let mark: string;
    let msg: string;
    if (correct && attempts <= 1) {
      cls = "correct";
      mark = "✓";
      msg = `correct — first try${score != null ? ` · +${score}` : ""}`;
    } else if (correct) {
      cls = "second";
      mark = "✓²";
      msg = `correct — second try${score != null ? ` · +${score}` : ""}`;
    } else if (resolved) {
      cls = "fail";
      mark = "✕";
      msg = "out of attempts";
    } else {
      cls = "fail";
      mark = "✕";
      msg = "not quite — try again";
    }
    const parts: (HTMLElement | string)[] = [
      h("span", { class: "mark" }, mark),
      h("span", { class: "why mono" }, msg),
    ];
    mount(slot, h("div", { class: `result ${cls}` }, ...parts));
    if (resolved && explanation) {
      slot.append(h("div", { class: "result", style: "border-top:none" }, h("span", { class: "why" }, explanation)));
    }
  }

  private flashResult(msg: string, cls: string): void {
    const slot = this.view.querySelector("#result-slot") as HTMLElement;
    mount(slot, h("div", { class: `result ${cls}` }, h("span", { class: "why mono" }, msg)));
  }

  private next(): void {
    const nextUnresolved = this.daily!.challenges.findIndex((c, i) => i > this.index && !c.resolved);
    if (nextUnresolved !== -1) {
      this.index = nextUnresolved;
      this.renderPlay();
      return;
    }
    if (this.daily!.challenges.every((c) => c.resolved)) {
      void this.finish();
      return;
    }
    // fall back to the first unresolved (shouldn't normally happen)
    this.index = this.firstUnresolvedIndex();
    this.renderPlay();
  }

  private async finish(): Promise<void> {
    this.stopTimers();
    this.setStatus("scoring…");
    try {
      const result = await this.api.complete(this.date, this.track);
      this.applyCompletionToMe(result);
      this.renderResults(result);
    } catch (e) {
      this.renderError(e);
    }
  }

  private applyCompletionToMe(result: CompleteResponse): void {
    if (!this.me) return;
    this.me.streak = result.streak;
    this.me.tracks[this.track] = {
      xp: result.xp.xp_after,
      level: result.xp.level_after,
    };
    this.renderAppbar();
  }

  // ---- results screen ------------------------------------------------- #
  private renderResults(result: CompleteResponse): void {
    this.stopTimers();
    const lvl = result.xp.level_after;
    const xpIntoLevel = pctIntoLevel(result.xp.xp_after);

    const panel = h(
      "div",
      { class: "panel" },
      h("div", { class: "panel-head" }, h("span", { class: "panel-title" }, `${this.track} · daily complete`)),
      h(
        "div",
        { class: "panel-body stack" },
        h("div", { class: "center" }, h("div", { class: "score-big" }, String(result.score)), h("div", { class: "muted mono" }, "score")),
        this.resultKvs(result, lvl),
        h(
          "div",
          {},
          h("div", { class: "muted mono", style: "font-size:12px" }, `${this.track}: lvl ${result.xp.level_before} → ${lvl} · +${result.xp.xp_delta} xp`),
          h("div", { class: "xpbar" }, h("span", { style: `width:${xpIntoLevel}%` }))
        ),
        result.quarantined
          ? h("div", { class: "result fail" }, h("span", { class: "why mono" }, "flagged: solve time too fast — kept off the leaderboard"))
          : null,
        this.shareBlock(result, lvl),
        h(
          "div",
          { class: "btn-row" },
          h("button", { class: "btn", onclick: () => this.renderLeaderboard() }, "leaderboard"),
        ),
        this.countdownLine()
      )
    );
    mount(this.view, panel);
  }

  private resultKvs(result: CompleteResponse, _lvl: number): HTMLElement {
    const box = h("div", {});
    box.append(
      kv("time", formatMs(result.total_ms)),
      kv("streak", `⚑ ${result.streak.current}${result.streak.freeze_used ? " (freeze used)" : ""}`),
      kv("leaderboard", result.leaderboard_rank ? `#${result.leaderboard_rank}` : "—")
    );
    result.results.forEach((r, i) => {
      const label = `${i + 1}. ${TYPE_TITLE[r.type]}`;
      const glyph = r.correct ? (r.attempts <= 1 ? "🟩 ✓" : "🟨 ✓²") : "🟥 ✕";
      box.append(kv(label, `${glyph}  +${r.score}`));
    });
    return box;
  }

  private shareBlock(result: CompleteResponse, lvl: number): HTMLElement {
    const text = buildShareText(result, lvl);
    const pre = h("div", { class: "share" }, text);
    const copyBtn = h("button", { class: "btn btn-primary", onclick: onCopy }, "copy result");
    async function onCopy() {
      try {
        await navigator.clipboard.writeText(text);
        copyBtn.textContent = "copied ✓";
        setTimeout(() => (copyBtn.textContent = "copy result"), 1500);
      } catch {
        copyBtn.textContent = "copy failed";
      }
    }
    return h("div", { class: "stack" }, pre, h("div", { class: "btn-row" }, copyBtn));
  }

  private countdownLine(): HTMLElement {
    const line = h("div", { class: "center muted mono", id: "countdown" }, "");
    const tick = () => {
      line.textContent = `next stack in ${formatCountdown(msUntilLocalMidnight())}`;
    };
    tick();
    this.countdownHandle = window.setInterval(tick, 1000);
    return line;
  }

  // ---- leaderboard screen -------------------------------------------- #
  private async renderLeaderboard(): Promise<void> {
    this.stopTimers();
    this.setStatus("loading leaderboard…");
    try {
      const lb = await this.api.leaderboard(this.date, this.track);
      const table = h("table", { class: "lb" });
      table.append(
        h(
          "tr",
          {},
          h("th", { class: "num" }, "#"),
          h("th", {}, "handle"),
          h("th", { class: "num" }, "score"),
          h("th", { class: "num" }, "time")
        )
      );
      if (lb.entries.length === 0) {
        table.append(h("tr", {}, h("td", { colspan: "4", class: "muted" }, "no entries yet — be the first")));
      }
      for (const e of lb.entries) {
        table.append(
          h(
            "tr",
            { class: e.is_me ? "me" : "" },
            h("td", { class: "num mono" }, String(e.rank)),
            h("td", { class: "mono" }, e.handle),
            h("td", { class: "num mono" }, String(e.score)),
            h("td", { class: "num mono" }, formatMs(e.total_ms))
          )
        );
      }
      const panel = h(
        "div",
        { class: "panel" },
        h("div", { class: "panel-head" }, h("span", { class: "panel-title" }, `${this.track} · daily leaderboard`)),
        h(
          "div",
          { class: "panel-body stack" },
          table,
          lb.me ? h("div", { class: "muted mono" }, `you: #${lb.me.rank} · ${lb.me.score} pts`) : null,
          h("div", { class: "btn-row" }, h("button", { class: "btn", onclick: () => this.loadDaily() }, "◂ back"))
        )
      );
      mount(this.view, panel);
    } catch (e) {
      this.renderError(e);
    }
  }

  // ---- timers / helpers ---------------------------------------------- #
  private startTimer(): void {
    const update = () => {
      const el = this.view.querySelector("#timer");
      if (el) el.textContent = this.currentTimerText();
    };
    update();
    this.timerHandle = window.setInterval(update, 1000);
  }

  private currentTimerText(): string {
    return formatMs(Date.now() - this.playStart);
  }

  private stopTimers(): void {
    if (this.timerHandle) window.clearInterval(this.timerHandle);
    if (this.countdownHandle) window.clearInterval(this.countdownHandle);
    this.timerHandle = null;
    this.countdownHandle = null;
  }

  private setStatus(msg: string): void {
    mount(this.view, h("div", { class: "status" }, msg));
  }

  private renderError(e: unknown): void {
    const msg = e instanceof ApiError ? `${e.status}: ${e.message}` : String(e);
    mount(
      this.view,
      h(
        "div",
        { class: "panel" },
        h("div", { class: "panel-body stack" }, h("div", { class: "error" }, `error — ${msg}`), h("div", { class: "btn-row" }, h("button", { class: "btn", onclick: () => this.loadDaily() }, "retry")))
      )
    );
  }

  private renderFatal(e: unknown): void {
    const msg = e instanceof ApiError ? `${e.status}: ${e.message}` : String(e);
    mount(
      this.root,
      h(
        "div",
        { class: "shell" },
        h("div", { class: "status error" }, `cannot reach the syntax api — ${msg}`),
        h("div", { class: "status muted" }, "is the backend running on " + (import.meta.env.VITE_API_BASE ?? "http://localhost:8000") + "?")
      )
    );
  }
}

// ---- small module helpers -------------------------------------------- #
function kv(k: string, v: string): HTMLElement {
  return h("div", { class: "kv" }, h("span", { class: "k" }, k), h("span", { class: "v" }, v));
}

function pctIntoLevel(xp: number): number {
  // level thresholds: level n starts at 100*(n-1)^2 xp (matches backend curve).
  const lvl = 1 + Math.floor(Math.sqrt(xp / 100));
  const start = 100 * (lvl - 1) ** 2;
  const next = 100 * lvl ** 2;
  return Math.round(((xp - start) / (next - start)) * 100);
}

function toggleTheme(): void {
  const cur = document.documentElement.getAttribute("data-theme");
  const next = cur === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("syntax.theme", next);
}

// Subtle mechanical "click" on a correct lock-in (GDD §5). WebAudio, no assets;
// only fires after a user gesture so mobile autoplay rules are satisfied.
let audioCtx: AudioContext | null = null;
function playClick(): void {
  if (localStorage.getItem("syntax.sound") !== "on") return;
  try {
    audioCtx = audioCtx ?? new AudioContext();
    const t = audioCtx.currentTime;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "square";
    osc.frequency.setValueAtTime(880, t);
    gain.gain.setValueAtTime(0.05, t);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.06);
    osc.connect(gain).connect(audioCtx.destination);
    osc.start(t);
    osc.stop(t + 0.07);
  } catch {
    /* audio unavailable — silent */
  }
}
