// Bug Spotting: tap the exact line containing the fault (GDD §2).
import { h } from "../dom";
import { highlightLine } from "../highlight";
import type { BugSpotPayload } from "../types";
import type { ChallengeComponent } from "./types";

export function createBugSpot(payloadRaw: unknown): ChallengeComponent {
  const payload = payloadRaw as BugSpotPayload;
  const lines = payload.code.split("\n");
  let selected: number | null = null;
  let enabled = true;

  const lineEls: HTMLElement[] = [];
  const code = h("div", { class: "code tappable", role: "listbox", "aria-label": "code — tap the buggy line" });

  lines.forEach((line, i) => {
    const n = i + 1;
    const content = h("span", { class: "content", html: highlightLine(line, payload.language) || "&nbsp;" });
    const row = h(
      "div",
      {
        class: "code-line",
        role: "option",
        tabindex: "0",
        "aria-selected": "false",
        "data-line": n,
      },
      h("span", { class: "gutter" }, String(n)),
      content
    );
    const select = () => {
      if (!enabled) return;
      selected = n;
      lineEls.forEach((el) => {
        const on = Number(el.dataset.line) === n;
        el.classList.toggle("selected", on);
        el.setAttribute("aria-selected", String(on));
      });
      if (navigator.vibrate) navigator.vibrate(8);
    };
    row.addEventListener("click", select);
    row.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        select();
      }
    });
    lineEls.push(row);
    code.append(row);
  });

  return {
    element: code,
    getAnswer: () => (selected == null ? null : { line: selected }),
    setEnabled(v: boolean) {
      enabled = v;
      code.classList.toggle("tappable", v);
    },
  };
}
