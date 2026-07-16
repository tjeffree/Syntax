// Parsons Problems: drag/reorder scrambled code blocks into the correct order
// and indentation (GDD §2). Reordering works by drag (desktop) OR the up/down
// buttons (tap-first fallback, GDD §5 accessibility); indentation via the
// indent/outdent buttons.
import { h, mount } from "../dom";
import { highlightLine } from "../highlight";
import { seededShuffle } from "../rng";
import type { ParsonsPayload } from "../types";
import type { ChallengeComponent } from "./types";

interface Row {
  id: string;
  code: string;
  indent: number;
}

export function createParsons(payloadRaw: unknown, challengeId: string): ChallengeComponent {
  const payload = payloadRaw as ParsonsPayload;
  const indentEnabled = !!payload.indent && (payload.maxIndent ?? 0) > 0;
  const maxIndent = payload.maxIndent ?? 0;
  const lang = payload.language;

  // Same scramble for everyone (universal seed), and never the authored order.
  let order: Row[] = seededShuffle(
    payload.blocks.map((b) => ({ id: b.id, code: b.code, indent: 0 })),
    `${challengeId}:parsons`
  );
  let enabled = true;
  let dragIndex: number | null = null;

  const list = h("div", { class: "parsons", role: "list" });
  const hint = h(
    "div",
    { class: "parsons-hint muted mono" },
    indentEnabled ? "reorder + set indent to match the correct program" : "reorder to match the correct program"
  );
  const element = h("div", {}, list, hint);

  function move(from: number, to: number) {
    if (to < 0 || to >= order.length) return;
    const [item] = order.splice(from, 1);
    order.splice(to, 0, item);
    render();
  }
  function reindent(i: number, delta: number) {
    order[i].indent = Math.max(0, Math.min(maxIndent, order[i].indent + delta));
    render();
  }

  function render() {
    const rows = order.map((row, i) => {
      const grip = h("span", { class: "grip", "aria-hidden": "true" }, "⣿");
      const codeEl = h("span", {
        class: "pcode",
        style: `padding-left:${row.indent * 20}px`,
        html: highlightLine(row.code, lang) || "&nbsp;",
      });

      const ctrls = h("div", { class: "pctrls" });
      const up = h("button", { type: "button", "aria-label": "move up", title: "move up" }, "▲") as HTMLButtonElement;
      const down = h("button", { type: "button", "aria-label": "move down", title: "move down" }, "▼") as HTMLButtonElement;
      up.disabled = !enabled || i === 0;
      down.disabled = !enabled || i === order.length - 1;
      up.addEventListener("click", () => move(i, i - 1));
      down.addEventListener("click", () => move(i, i + 1));
      ctrls.append(up, down);

      if (indentEnabled) {
        const outd = h("button", { type: "button", "aria-label": "outdent", title: "outdent" }, "⇤") as HTMLButtonElement;
        const ind = h("button", { type: "button", "aria-label": "indent", title: "indent" }, "⇥") as HTMLButtonElement;
        outd.disabled = !enabled || row.indent === 0;
        ind.disabled = !enabled || row.indent >= maxIndent;
        outd.addEventListener("click", () => reindent(i, -1));
        ind.addEventListener("click", () => reindent(i, +1));
        ctrls.append(outd, ind);
      }

      const block = h(
        "div",
        { class: "pblock", role: "listitem", draggable: enabled ? "true" : "false" },
        grip,
        codeEl,
        ctrls
      );

      // Drag reordering (desktop enhancement).
      block.addEventListener("dragstart", () => {
        if (!enabled) return;
        dragIndex = i;
        block.classList.add("dragging");
      });
      block.addEventListener("dragend", () => {
        dragIndex = null;
        block.classList.remove("dragging");
        list.querySelectorAll(".drop-target").forEach((el) => el.classList.remove("drop-target"));
      });
      block.addEventListener("dragover", (e) => {
        if (!enabled || dragIndex === null) return;
        e.preventDefault();
        block.classList.add("drop-target");
      });
      block.addEventListener("dragleave", () => block.classList.remove("drop-target"));
      block.addEventListener("drop", (e) => {
        e.preventDefault();
        block.classList.remove("drop-target");
        if (dragIndex !== null && dragIndex !== i) move(dragIndex, i);
      });

      return block;
    });
    mount(list, ...rows);
  }

  render();

  return {
    element,
    getAnswer: () => ({ solution: order.map((r) => ({ id: r.id, indent: r.indent })) }),
    setEnabled(v: boolean) {
      enabled = v;
      render();
    },
  };
}
