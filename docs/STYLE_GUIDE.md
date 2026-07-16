# "Syntax" — Visual Style Guide

**Direction:** Early-2010s developer tool. Clean lines, 1px borders, tame radii, blue-on-grey. The app should look like it was built by a competent engineer who cared — not by a design agency. Think GitHub/Stack Overflow circa 2013, Bootstrap 3 without the theme swap.

**Relationship to GDD §5:** This guide refines the original "Dark Mode IDE" note. The app **chrome is light grey/blue by default** (the authentic 2010s dev look); **code surfaces are always dark IDE-styled**, whatever the chrome theme. A dark chrome variant is defined below for players who prefer it.

**Rules of the aesthetic:**

1. Structure comes from **1px solid borders**, never from drop shadows. Shadows are reserved for overlays (modals, menus).
2. **Flat fills.** No gradients, no glassmorphism, no blur. The one permitted flourish is a darker 2px bottom border on buttons (the 2013 "pressable" look).
3. **Tame radius.** 3px on controls, 4px on panels. Nothing pill-shaped, nothing sharp-cornered.
4. Color is **information, not decoration**. Blue = interactive. Green/amber/red = result states. Grey = everything else.
5. Density over whitespace. 14px base type, 5px spacing grid. This is a tool, not a landing page.

---

## 1. Color

### Chrome (light theme — default)

| Token | Hex | Use |
|---|---|---|
| `--bg-page` | `#F4F5F7` | Page background |
| `--bg-panel` | `#FFFFFF` | Panels, cards, modals |
| `--bg-inset` | `#EDEFF2` | Wells, input backgrounds on hover, table header rows |
| `--border` | `#D4D9DE` | Default 1px border |
| `--border-strong` | `#B8C0C8` | Panel headers, active control borders |
| `--text` | `#333333` | Primary text |
| `--text-muted` | `#707880` | Secondary text, captions, timestamps |
| `--text-faint` | `#9AA3AB` | Disabled text, placeholders |

### Blues (interactive)

| Token | Hex | Use |
|---|---|---|
| `--blue` | `#337AB7` | Primary buttons, active tabs, progress fill |
| `--blue-dark` | `#2A6496` | Hover state, button bottom-border |
| `--blue-darker` | `#1F4E77` | Active/pressed |
| `--blue-link` | `#0088CC` | Text links |
| `--blue-wash` | `#E8F1F8` | Selected rows, info backgrounds |
| `--focus-ring` | `rgba(51,122,183,.45)` | Focus glow on inputs/controls |

### Result states (Bootstrap-3 heritage, used sparingly)

| Token | Hex | Use |
|---|---|---|
| `--green` | `#5CB85C` | Correct / first-try / streak alive |
| `--green-wash` | `#EAF5EA` | Correct-answer row background |
| `--amber` | `#F0AD4E` | Second-attempt success / warnings |
| `--amber-wash` | `#FCF4E6` | |
| `--red` | `#D9534F` | Wrong / failed / streak lost |
| `--red-wash` | `#FAEAEA` | |

### Chrome (dark variant)

Blue-tinted greys, not pure black. Same token names, swapped values.

| Token | Hex |
|---|---|
| `--bg-page` | `#1C222B` |
| `--bg-panel` | `#232A35` |
| `--bg-inset` | `#1A2028` |
| `--border` | `#39424E` |
| `--border-strong` | `#4A5563` |
| `--text` | `#D6DEE8` |
| `--text-muted` | `#8C97A4` |
| `--text-faint` | `#5E6873` |
| `--blue` | `#4E97D1` |
| `--blue-link` | `#58AEE0` |
| `--blue-wash` | `#25384C` |

### Code surface (theme-independent — always dark)

| Token | Hex | Use |
|---|---|---|
| `--code-bg` | `#1E1E1E` | Snippet background (VS Code dark heritage) |
| `--code-text` | `#D4D4D4` | Default code text |
| `--code-gutter` | `#858585` | Line numbers |
| `--code-line-hover` | `#2A2D2E` | Tappable line hover/press |
| `--code-line-selected` | `#264F78` | Selected line (Bug Spotting) |
| Syntax colors | `#569CD6` keyword · `#CE9178` string · `#B5CEA8` number · `#6A9955` comment · `#DCDCAA` function | Match VS Code Dark+ |

**Contrast:** all text/background pairs above meet WCAG AA at their intended sizes. Never place `--text-muted` on `--bg-inset` at sizes below 12px.

---

## 2. Typography

```css
--font-ui:   "Helvetica Neue", Helvetica, Arial, "Segoe UI", sans-serif;
--font-code: Consolas, Menlo, Monaco, "Liberation Mono", "Courier New", monospace;
```

No webfonts. System stacks only — this is both the aesthetic and the §7 performance budget.

| Style | Size / line-height | Weight | Use |
|---|---|---|---|
| Page title | 24 / 30 | 500 | One per screen, max |
| Section heading | 18 / 24 | 600 | Panel titles |
| Subheading | 14 / 20 | 700, `--text-muted`, uppercase, 0.5px tracking | Table headers, group labels |
| Body | 14 / 21 | 400 | Default |
| Small | 12 / 18 | 400 | Captions, timestamps, legal |
| Code | 13 / 20 | 400, `--font-code` | Snippets, handles, stats, timers |

**Coder tells (deliberate):** player handles, scores, timers, streak counts, and dates render in `--font-code`. Numbers in tables use `font-variant-numeric: tabular-nums`. Headings are sentence case, never Title Case.

---

## 3. Spacing, Radius, Elevation

- **Spacing scale:** `5 / 10 / 15 / 20 / 30 / 40px`. Nothing off-grid.
- **Radius:** `--radius-s: 3px` (buttons, inputs, badges, code blocks) · `--radius-m: 4px` (panels, modals). Never larger.
- **Borders:** 1px solid `--border` everywhere; `--border-strong` for the top edge of panel headers and active states.
- **Shadows:** panels get none. Dropdowns/modals only: `0 2px 8px rgba(0,0,0,.18)`.
- **Layout:** single centered column, `max-width: 720px`, 15px gutters. Panels stack vertically with 20px gaps. It's a daily quiz, not a dashboard.

---

## 4. Components

### Buttons

Flat fill, 1px border, 2px darker bottom border ("pressable" edge), 3px radius. Height 36px (44px min touch target via padding on mobile). Label: 14px, weight 600.

| Variant | Fill | Border / bottom edge | Text |
|---|---|---|---|
| Primary | `--blue` | `--blue-dark` / `--blue-darker` | `#FFF` |
| Default | `--bg-panel` | `--border-strong` / `#A6AFB8` | `--text` |
| Danger (rare) | `--red` | darker 12% | `#FFF` |
| Disabled | `--bg-inset` | `--border` | `--text-faint` |

Hover: darken fill ~7%. Active: translate down 1px and drop the bottom edge to 1px — the button visibly "presses." Focus: `box-shadow: 0 0 0 3px var(--focus-ring)`.

### Panels

White card, 1px border, 4px radius. Optional header strip: `--bg-inset` fill, 10px 15px padding, subheading style, 1px bottom border. Body padding 15px.

### Leaderboard table

Full-width, 1px outer border, zebra striping (`--bg-inset` on even rows), 8px 10px cell padding. Rank + score in `--font-code`, tabular-nums, right-aligned. Current player's row: `--blue-wash` fill with a 3px `--blue` left edge. Top-3 ranks get a subtle badge, not gold/silver/bronze theatrics.

### Badges & labels

Inline rect, 3px radius, 11px bold uppercase text, 2px 6px padding. Streak badge: `--green` fill, white text, flame prefix. Track badges: `--blue-wash` fill, `--blue-dark` text. Difficulty: grey / amber / red washes.

### Progress bars (XP)

Height 8px, `--bg-inset` track with 1px border, flat `--blue` fill, 3px radius. No animation stripes, no gradient. XP delta printed beside it in `--font-code`: `+140 xp`.

### Forms & inputs

34px height, 1px `--border`, 3px radius, white fill, 13px text. Focus: border becomes `--blue`, plus the classic soft glow `box-shadow: 0 0 6px var(--focus-ring)`. Labels above inputs, 12px bold `--text-muted`.

### Tabs (track switcher)

Boxed tabs, 2013-style: inactive tabs transparent with `--text-muted`; active tab is white with 1px borders on top/left/right, joined to the panel below (no bottom border). 14px, weight 600.

### Modals

`max-width: 480px`, panel styling plus the overlay shadow, `rgba(0,0,0,.5)` backdrop. Header strip + body + right-aligned button row (primary rightmost). No slide/zoom theatrics — 120ms fade only.

### Code challenge surface

Always dark (`--code-bg`) regardless of chrome theme, 3px radius, 1px `#000` border in light chrome. Line numbers in a 40px gutter, `--code-gutter`, `--font-code` 13px, line-height 20px with 6px vertical padding per line for touch (≥ 32px effective target; whole line is the tap target, not the text). Hover `--code-line-hover`; selected `--code-line-selected` with a 2px `--blue` left edge. Parsons drag blocks: same surface, 1px `#3C3C3C` border, grip dots on the left, 3px radius; while dragging, border becomes `--blue` and a dashed drop-slot appears.

### Result marks

Correct: green check in a `--green-wash` square. Second-try: amber. Fail: red cross. Squares 20px, 3px radius — these mirror the emoji share grid (🟩 🟨 🟥) exactly, and each mark also differs by glyph (✓ / ✓² / ✕) so color is never the only signal.

---

## 5. Motion & Sound

- **Durations:** 100–150ms, `ease-out`, opacity/transform only. The only "juicy" moment: a Parsons block snapping into a slot (80ms translate + the mechanical click from GDD §5).
- Respect `prefers-reduced-motion`: snap transitions become instant, fades stay.
- No skeleton shimmer, no spinners longer than 300ms — if the API is slower than that, show a `--font-code` status line: `fetching daily stack…`

---

## 6. Voice & Microcopy

Terse, lowercase-leaning, technical. Written like commit messages, not marketing.

| Instead of | Write |
|---|---|
| "Awesome job! You nailed it! 🎉" | `correct — first try` |
| "Oops! Something went wrong!" | `request failed — retrying (2/3)` |
| "Level Up! You're amazing!" | `python: lvl 12 → 13` |
| "Come back tomorrow!" | `next stack in 06:41:12` |

Errors state the fact and the next action. No exclamation marks in system text. Emoji appear in exactly one place: the share grid.

---

## 7. Iconography

Minimal set, 16px grid, 1.5px stroke, single color (inherits text color). Prefer unicode glyphs where they read cleanly (`✓ ✕ ▸ ⏱ ⚑`) — a coder would. No filled multicolor icon packs, no emoji in chrome.

---

## 8. Drop-in tokens

```css
:root {
  /* chrome — light (default) */
  --bg-page: #F4F5F7; --bg-panel: #FFFFFF; --bg-inset: #EDEFF2;
  --border: #D4D9DE; --border-strong: #B8C0C8;
  --text: #333333; --text-muted: #707880; --text-faint: #9AA3AB;
  --blue: #337AB7; --blue-dark: #2A6496; --blue-darker: #1F4E77;
  --blue-link: #0088CC; --blue-wash: #E8F1F8;
  --focus-ring: rgba(51,122,183,.45);
  --green: #5CB85C; --green-wash: #EAF5EA;
  --amber: #F0AD4E; --amber-wash: #FCF4E6;
  --red: #D9534F;   --red-wash: #FAEAEA;
  /* code surface — theme independent */
  --code-bg: #1E1E1E; --code-text: #D4D4D4; --code-gutter: #858585;
  --code-line-hover: #2A2D2E; --code-line-selected: #264F78;
  /* type, shape */
  --font-ui: "Helvetica Neue", Helvetica, Arial, "Segoe UI", sans-serif;
  --font-code: Consolas, Menlo, Monaco, "Liberation Mono", "Courier New", monospace;
  --radius-s: 3px; --radius-m: 4px;
}

[data-theme="dark"] {
  --bg-page: #1C222B; --bg-panel: #232A35; --bg-inset: #1A2028;
  --border: #39424E; --border-strong: #4A5563;
  --text: #D6DEE8; --text-muted: #8C97A4; --text-faint: #5E6873;
  --blue: #4E97D1; --blue-link: #58AEE0; --blue-wash: #25384C;
}
```
