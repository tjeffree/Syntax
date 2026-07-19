// Parsons Problems: drag/reorder scrambled code blocks into the correct order
// and indentation (GDD §2). The grip handle is a pointer-driven manipulator that
// works with mouse and touch alike: drag vertically to reorder, swipe/drag
// horizontally to change indentation. The up/down + indent/outdent buttons are a
// tap-first fallback (GDD §5 accessibility); long lines scroll horizontally so
// nothing is clipped on a narrow screen.
import { h, mount } from "../dom";
import { highlightLine } from "../highlight";
import { seededShuffle } from "../rng";
import type { ParsonsPayload } from "../types";
import type { ChallengeComponent } from "./types";

interface Row {
  id: string;
  code: string;
  indent: number;
  el: HTMLElement;
  codeEl: HTMLElement;
  up: HTMLButtonElement;
  down: HTMLButtonElement;
  outd?: HTMLButtonElement;
  ind?: HTMLButtonElement;
}

const INDENT_PX = 20; // visual px per indent level
const SWIPE_STEP_PX = 24; // horizontal drag distance for one indent level

export function createParsons(payloadRaw: unknown, challengeId: string): ChallengeComponent {
  const payload = payloadRaw as ParsonsPayload;
  const indentEnabled = !!payload.indent && (payload.maxIndent ?? 0) > 0;
  const maxIndent = payload.maxIndent ?? 0;
  const lang = payload.language;

  // Same scramble for everyone (universal seed), and never the authored order.
  const seeded = seededShuffle(
    payload.blocks.map((b) => ({ id: b.id, code: b.code })),
    `${challengeId}:parsons`
  );
  let enabled = true;

  const list = h("div", { class: "parsons", role: "list" });
  const hint = h(
    "div",
    { class: "parsons-hint muted mono" },
    indentEnabled
      ? "drag the handle to reorder · swipe it left/right to indent"
      : "drag the handle to reorder"
  );
  const element = h("div", {}, list, hint);

  const rowOf = new Map<HTMLElement, Row>();
  const order: Row[] = seeded.map((b) => buildRow(b.id, b.code));

  function buildRow(id: string, code: string): Row {
    const grip = h("span", { class: "grip", "aria-hidden": "true", title: "drag to reorder" }, "⣿");
    const codeEl = h("span", {
      class: "pcode",
      html: highlightLine(code, lang) || "&nbsp;",
    });

    const ctrls = h("div", { class: "pctrls" });
    const up = h("button", { type: "button", "aria-label": "move up", title: "move up" }, "▲") as HTMLButtonElement;
    const down = h("button", { type: "button", "aria-label": "move down", title: "move down" }, "▼") as HTMLButtonElement;
    up.addEventListener("click", () => moveBy(row, -1));
    down.addEventListener("click", () => moveBy(row, +1));
    ctrls.append(up, down);

    let outd: HTMLButtonElement | undefined;
    let ind: HTMLButtonElement | undefined;
    if (indentEnabled) {
      outd = h("button", { type: "button", "aria-label": "outdent", title: "outdent" }, "⇤") as HTMLButtonElement;
      ind = h("button", { type: "button", "aria-label": "indent", title: "indent" }, "⇥") as HTMLButtonElement;
      outd.addEventListener("click", () => reindent(row, -1));
      ind.addEventListener("click", () => reindent(row, +1));
      ctrls.append(outd, ind);
    }

    const block = h("div", { class: "pblock", role: "listitem" }, grip, codeEl, ctrls);
    const row: Row = { id, code, indent: 0, el: block, codeEl, up, down, outd, ind };
    rowOf.set(block, row);
    applyIndent(row);
    attachDrag(row, grip);
    return row;
  }

  function applyIndent(row: Row) {
    row.codeEl.style.paddingLeft = `${row.indent * INDENT_PX}px`;
  }

  // Rebuild the `order` array from the live DOM (source of truth during a drag).
  function syncOrder() {
    order.length = 0;
    for (const child of Array.from(list.children)) {
      const row = rowOf.get(child as HTMLElement);
      if (row) order.push(row);
    }
  }

  // Refresh disabled states + indent padding without recreating any nodes (so an
  // in-flight pointer capture on a grip survives).
  function refresh() {
    order.forEach((row, i) => {
      row.up.disabled = !enabled || i === 0;
      row.down.disabled = !enabled || i === order.length - 1;
      if (row.outd) row.outd.disabled = !enabled || row.indent === 0;
      if (row.ind) row.ind.disabled = !enabled || row.indent >= maxIndent;
      applyIndent(row);
    });
  }

  function moveBy(row: Row, delta: number) {
    const from = order.indexOf(row);
    const to = from + delta;
    if (to < 0 || to >= order.length) return;
    const ref = delta > 0 ? order[to].el.nextSibling : order[to].el;
    list.insertBefore(row.el, ref);
    syncOrder();
    refresh();
  }

  function reindent(row: Row, delta: number) {
    setIndent(row, row.indent + delta);
  }

  function setIndent(row: Row, level: number) {
    const next = Math.max(0, Math.min(maxIndent, level));
    if (next === row.indent) return;
    row.indent = next;
    applyIndent(row);
    refresh();
  }

  // Pointer-driven drag: unified for mouse + touch. Vertical movement reorders
  // by moving the real node in the list; horizontal movement steps indentation.
  function attachDrag(row: Row, grip: HTMLElement) {
    const surface = grip;
    surface.addEventListener("pointerdown", (e) => {
      if (!enabled) return;
      e.preventDefault();
      surface.setPointerCapture(e.pointerId);

      const startX = e.clientX;
      const startIndent = row.indent;
      row.el.classList.add("dragging");

      const onMove = (ev: PointerEvent) => {
        // Indentation from horizontal travel, relative to where the drag began.
        if (indentEnabled) {
          const steps = Math.round((ev.clientX - startX) / SWIPE_STEP_PX);
          setIndent(row, startIndent + steps);
        }

        // Reorder: slide the node before the first other row whose midpoint sits
        // below the pointer (native list-reorder pattern).
        const y = ev.clientY;
        let ref: Node | null = null;
        for (const other of order) {
          if (other === row) continue;
          const r = other.el.getBoundingClientRect();
          if (y < r.top + r.height / 2) {
            ref = other.el;
            break;
          }
        }
        if (ref !== row.el && ref !== row.el.nextSibling) {
          list.insertBefore(row.el, ref);
          syncOrder();
          refresh();
        }
      };

      const onUp = () => {
        surface.releasePointerCapture(e.pointerId);
        row.el.classList.remove("dragging");
        surface.removeEventListener("pointermove", onMove);
        surface.removeEventListener("pointerup", onUp);
        surface.removeEventListener("pointercancel", onUp);
      };

      surface.addEventListener("pointermove", onMove);
      surface.addEventListener("pointerup", onUp);
      surface.addEventListener("pointercancel", onUp);
    });
  }

  mount(list, ...order.map((r) => r.el));
  refresh();

  return {
    element,
    getAnswer: () => ({ solution: order.map((r) => ({ id: r.id, indent: r.indent })) }),
    setEnabled(v: boolean) {
      enabled = v;
      refresh();
    },
  };
}
