// Time Complexity Match: assign Big-O from a fixed set of buttons (GDD §2).
import { h } from "../dom";
import { highlightLine } from "../highlight";
import type { BigOPayload } from "../types";
import type { ChallengeComponent } from "./types";

export function createBigO(payloadRaw: unknown): ChallengeComponent {
  const payload = payloadRaw as BigOPayload;
  let choice: string | null = null;
  let enabled = true;

  const codeBlock = h("div", { class: "code code-static" });
  payload.code.split("\n").forEach((line) => {
    codeBlock.append(
      h(
        "div",
        { class: "code-line" },
        h("span", { class: "content", html: highlightLine(line, payload.language) || "&nbsp;" })
      )
    );
  });

  const buttons: HTMLButtonElement[] = [];
  const options = h("div", { class: "options", role: "group" });
  payload.options.forEach((opt) => {
    const btn = h(
      "button",
      { class: "btn option", type: "button", "aria-pressed": "false" },
      opt
    ) as HTMLButtonElement;
    btn.addEventListener("click", () => {
      if (!enabled) return;
      choice = opt;
      buttons.forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      if (navigator.vibrate) navigator.vibrate(8);
    });
    buttons.push(btn);
    options.append(btn);
  });

  const promptWord = payload.prompt === "space" ? "space" : "time";
  const element = h(
    "div",
    {},
    codeBlock,
    h("div", { class: "prompt-line" }, `what is the ${promptWord} complexity?`),
    options
  );

  return {
    element,
    getAnswer: () => (choice == null ? null : { choice }),
    setEnabled(v: boolean) {
      enabled = v;
      buttons.forEach((b) => (b.disabled = !v));
    },
  };
}
