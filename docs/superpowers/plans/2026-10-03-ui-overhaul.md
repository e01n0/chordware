# CHORDWARE UI Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every diagram and tab label readable at arm's length on phone, tablet and desktop, and make every feature reachable by name from a five-hub nav, without changing the app's visual identity.

**Architecture:** Everything stays in `index.html` (styles, markup, JS) plus `sw.js`, as the repo does today. Hubs are plain views toggled by a persistent `<nav>`; the 12 existing overlays keep their `role="dialog"` open/close code and are reached from hub cards. A hash router (one `hashchange` listener and a route table) gives back-button support and deep links. Legibility is a token pass on `:root` plus three SVG renderers.

**Tech Stack:** Vanilla HTML/CSS/JS, no build step. Node 24 for the `tools/*.mjs` checks. Chrome (claude-in-chrome) for screenshot verification, `show` to push screenshots to Eoin's viewer tab.

**Spec:** `docs/superpowers/specs/2026-10-03-ui-overhaul-design.md`

## Global Constraints

- Single file: all app code lives in `index.html`; `sw.js` is the only sidecar. No new files except `tools/check-ui.mjs`.
- No new fonts, no new dependencies, no build step.
- Five skins keep their palettes; only `--dim` (all skins) and the paper skin's `--yellow` are retuned (section 2 of the spec).
- Type floor: nothing read is under 14px (`--fs-s`); nothing tapped is under 16px (`--fs-m`); 12px only for the BUILD line.
- Hit boxes: every button, chip, select and pager control is at least 44px tall.
- No em dashes in commit messages or UI copy added by this plan (existing copy may keep them).
- Each commit ends with `Claude-Session: https://claude.ai/code/session_013L3Q2CzvMrFqiEcR9vArz8`.
- `node tools/validate-chords.mjs` and `node tools/check-ui.mjs` must pass before every commit from Phase 0 onward.
- Existing overlay `open*`/`close*` functions are not rewritten; navigation wraps them.

## Phases

- **Phase 0: tokens and checks.** Type scale tokens, `--dim` retune, contrast checker, 44px targets, focus ring, reduced-motion coverage. Small, safe, verifiable by script.
- **Phase 1: SVG pass.** Learn tab notes without rings and without shrinking; chord-diagram, map and halo label sizes. The thing Eoin complained about first.
- **Phase 2: nav, router and hubs.** Persistent nav, hash router, Practice and Tools hubs, Songs list, chip-row and header cleanup, Styles into Learn.
- **Phase 3: Galaxy Z Fold layouts.** Cover screen and unfolded inner screen only (spec section 4); no hinge-aware split.
- **Phase 4: visual verification.** Screenshots at 390 / 1280 (and Fold sizes) on dark and paper skins, pushed to the viewer.

---

## Phase 0: tokens and checks

### Task 1: contrast checker, then retune the tokens it fails

**Files:**
- Create: `tools/check-ui.mjs`
- Modify: `index.html:20-73` (the `:root` block and the four `html[data-theme=…]` blocks)

**Interfaces:**
- Produces: `node tools/check-ui.mjs` exits 0 when every skin passes; prints one line per failure otherwise. Phase 2 Task 10 adds a second section (route check) to this same file.

- [ ] **Step 1: Write the checker (it is the failing test)**

```js
#!/usr/bin/env node
/* UI invariants for index.html:
   1. every text token in every skin reads at >= 4.5:1 against every
      background it can sit on (bg, bg2, panel)
   Exit 0 = clean. */
import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const html = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "..", "index.html"), "utf8");
const css = html.slice(html.indexOf("<style>"), html.indexOf("</style>"));

/* skin blocks: the bare :root is NIGHT CITY, each html[data-theme=X] overrides it */
const vars = block => Object.fromEntries([...block.matchAll(/--([a-z0-9]+):\s*(#[0-9a-f]{6})/gi)].map(m => [m[1], m[2].toLowerCase()]));
const root = vars(css.slice(css.indexOf(":root{"), css.indexOf("}", css.indexOf(":root{"))));
const skins = { night: root };
for(const m of css.matchAll(/html\[data-theme="([a-z]+)"\]\{([^}]*)\}/g)) skins[m[1]] = { ...root, ...vars(m[2]) };

const lum = h => {
  const [r, g, b] = h.match(/\w\w/g).map(x => parseInt(x, 16) / 255)
    .map(c => c <= .03928 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4);
  return .2126 * r + .7152 * g + .0722 * b;
};
const ratio = (a, b) => { const [hi, lo] = [lum(a), lum(b)].sort((p, q) => q - p); return (hi + .05) / (lo + .05); };

const TEXT = ["text", "dim", "yellow", "cyan", "red"], GROUNDS = ["bg", "bg2", "panel"], MIN = 4.5;
let bad = 0;
for(const [name, s] of Object.entries(skins)){
  for(const t of TEXT) for(const g of GROUNDS){
    const r = ratio(s[t], s[g]);
    if(r < MIN){ console.error(`${name}: --${t} ${s[t]} on --${g} ${s[g]} = ${r.toFixed(2)}:1 (< ${MIN})`); bad++; }
  }
}
console.log(bad ? `${bad} contrast failure(s)` : `contrast: ${Object.keys(skins).length} skins clean`);
process.exit(bad ? 1 : 0);
```

- [ ] **Step 2: Run it, expect failures**

Run: `node tools/check-ui.mjs`
Expected: exit 1 with these lines (values from today's tokens):

```
night: --dim #5a7a86 on --bg2 #10101c = 4.10:1 (< 4.5)
amber: --dim #8a6a3a on --bg2 … 3.84
green: --dim #4d7a58 on --bg2 … 3.81
synth: --dim #8a6aa0 on --bg2 … 4.07
paper: --dim #8c8672 on … 2.88
paper: --yellow #8a6400 on … 4.26
```

(each token fails against more than one ground; the exact list is longer.)

- [ ] **Step 3: Retune the six values**

In `index.html`, change exactly these (nothing else in the skin blocks):

| Skin | Token | Old | New |
|---|---|---|---|
| `:root` (night) | `--dim` | `#5a7a86` | `#63838e` |
| amber | `--dim` | `#8a6a3a` | `#987a49` |
| green | `--dim` | `#4d7a58` | `#5a8866` |
| synth | `--dim` | `#8a6aa0` | `#9475a9` |
| paper | `--dim` | `#8c8672` | `#696555` |
| paper | `--yellow` | `#8a6400` | `#825e00` |

- [ ] **Step 4: Run both checks, expect clean**

Run: `node tools/check-ui.mjs && node tools/validate-chords.mjs`
Expected: `contrast: 5 skins clean` then the chord validator's existing clean output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add tools/check-ui.mjs index.html
git commit -m "Contrast check for every skin; dim and paper yellow retuned to pass 4.5:1

Claude-Session: https://claude.ai/code/session_013L3Q2CzvMrFqiEcR9vArz8"
```

### Task 2: type scale tokens, and the unstyled Dots button

**Files:**
- Modify: `index.html:20-38` (`:root`), `index.html:19-942` (every UI `font-size` under 13px inside `<style>`, excluding the `@media print` block which starts at line 943)
- Modify: `index.html:161-171` (`#ornToggle` rule gains `#dotToggle`)

**Interfaces:**
- Produces: CSS custom properties `--fs-s` (14px), `--fs-m` (16px), `--fs-l` (20px) on `:root`, used by every later task.

- [ ] **Step 1: Add the tokens**

In the `:root` block, after the `--font-m:` line:

```css
    --fs-s: 14px;          /* floor for anything read: legends, blurbs, counts */
    --fs-m: 16px;          /* buttons, chips, inputs; 16px stops iOS focus-zoom */
    --fs-l: 20px;          /* section + hub headings */
```

- [ ] **Step 2: Mechanical replacement in the style block only**

Run from the repo root (GNU sed; the line range keeps the print block untouched):

```bash
sed -i '19,942{s/font-size:9px/font-size:var(--fs-s)/g; s/font-size:10px/font-size:var(--fs-s)/g; s/font-size:11px/font-size:var(--fs-s)/g; s/font-size:12px/font-size:var(--fs-s)/g; s/font-size:13px/font-size:var(--fs-m)/g}' index.html
```

Then hand-revert two decorative rules back to 12px (they are the only 12px allowed by the spec):

- `.buildline` (around line 262, `color:var(--dim); opacity:.5; font-size:…`) → `font-size:12px`
- `.kbd-hint` (around line 343) → `font-size:12px`

- [ ] **Step 3: Rajdhani never below 600 at small sizes**

Grep `font-family:var(--font-h)` rules inside `<style>` that also carry `font-weight:400` or no weight; there are none today, but confirm:

```bash
awk 'NR>=19 && NR<=942' index.html | grep -n "font-h" | grep -v "font-weight:[67]00"
```

Expected: only `h1.glitch` and `.lnnow b` (both large). No change needed if so.

- [ ] **Step 4: Style the Dots toggle like the Ornaments toggle**

Change the selector on the `#ornToggle{` rule (line ~161) to `#ornToggle, #dotToggle{`, and the `#ornToggle.on{` rule to `#ornToggle.on, #dotToggle.on{`. Then add one override below them so Dots reads in cyan rather than red:

```css
  #dotToggle{ color:var(--cyan); border-color:var(--cyan); }
  #dotToggle.on{ background:var(--cyan); box-shadow:0 0 12px color-mix(in srgb, var(--cyan) 55%, transparent); }
```

- [ ] **Step 5: Check**

Run: `node tools/check-ui.mjs && node tools/validate-chords.mjs && grep -c "font-size:1[0-3]px\|font-size:9px" index.html`
Expected: both checks clean; the grep count equals the number of lines inside `@media print` plus the two decorative rules (expect 5).

Open `http://127.0.0.1:8092/` in Chrome (tabsmith.service serves the file live, no restart) and eyeball the header, chip row, map legend and learn controls: nothing truncated, chip row scrolls sideways on a narrow window.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "Type scale tokens: 14px floor for reading, 16px for tapping; Dots toggle styled

Claude-Session: https://claude.ai/code/session_013L3Q2CzvMrFqiEcR9vArz8"
```

### Task 3: 44px targets, focus ring, reduced motion

**Files:**
- Modify: `index.html` style block: `select#tuning` (~line 147), `.halorow button` rule carrying `min-height:40px` (~line 579), the song-editor `.sebtns button` rule carrying `min-height:38px` (~line 729), the perf transpose buttons `min-height:30px` (~line 830), `.stlist` row buttons `min-height:40px` (~line 881), the `h1.glitch::before/::after` animation rules (~lines 133-134)

- [ ] **Step 1: Raise every short target to 44px**

For each rule listed above change `min-height:NNpx` to `min-height:44px`. `select#tuning` also drops `padding:6px 8px` to `padding:0 8px`. (The `#lhBtn, #awakeBtn, #d5Btn` rule at ~line 352 is left alone: Phase 2 Task 11 deletes it.)

- [ ] **Step 2: Focus ring**

Add after the `*{ box-sizing… }` reset (line ~74):

```css
  :focus-visible{ outline:2px solid var(--yellow); outline-offset:2px; }
```

and delete `outline:none;` from the `#search` rule (~line 159) and the `#seLyrics`/textarea rule (~line 723) so the ring shows on keyboard focus (mouse focus never triggers `:focus-visible` on inputs in Chrome, so this is keyboard-only).

- [ ] **Step 3: Reduced motion covers the title glitch**

After the two `@keyframes gl*` blocks add:

```css
  @media (prefers-reduced-motion: reduce){ h1.glitch::before, h1.glitch::after{ animation:none; opacity:0; } }
```

- [ ] **Step 4: Check**

Run: `node tools/check-ui.mjs && node tools/validate-chords.mjs && awk 'NR>=19 && NR<=942' index.html | grep -c "min-height:\(2[0-9]\|3[0-9]\|4[0-3]\)px"`
Expected: checks clean; the count is 5 (the three non-interactive status rows at ~lines 450/484/534 with `min-height:20px`/`26px`, plus the `#lhBtn…` and `#themeBtn` rules Phase 2 removes).

In Chrome, Tab through the header and chip row: a yellow ring follows focus.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "44px targets everywhere, keyboard focus ring, reduced motion stills the title

Claude-Session: https://claude.ai/code/session_013L3Q2CzvMrFqiEcR9vArz8"
```

## Phase 1: SVG pass

### Task 4: learn tab: printed-tab notes, no shrinking

**Files:**
- Modify: `index.html:5407-5493` (`renderLessonTab`), `index.html:5589-5593` (bar highlight width in `lnFrame`), `index.html:519-536` (learn-tab CSS)

**Interfaces:**
- Consumes: `lnGeo` is read by `lnFrame()` (SVG user units; untouched fields `X0, STEP, TOP, SG, rowH, perRow, rows, NSTR, BAR`).
- Produces: the same `lnGeo` shape. `.lev` groups now contain `<rect>` + `<text class="fr">` instead of `<circle>` + text; anything selecting `.lev circle` must select `.lev rect`.

- [ ] **Step 1: Replace the metrics block**

In `renderLessonTab`, replace lines 5410-5419 (from `const cw = …` through `const H = …`) with:

```js
  const cw = $("#lnTab").clientWidth || 700;
  // Fixed, readable metrics: the tab never scales down to fit. A lesson
  // that is wider than the panel wraps into rows (whole bars when a bar
  // fits, else beat pairs), the way printed tab breaks lines.
  const X0 = 58, TOP = 34, STEP = 48, SG = 40, R = 10, F = 16;
  const fit = Math.max(2, Math.floor((cw - X0 - 14) / STEP));          // slots that fit at 1:1
  const perRow = lesson.steps <= fit ? lesson.steps
               : fit >= BAR ? Math.floor(fit / BAR) * BAR
               : Math.max(2, Math.floor(fit / 2) * 2);
  const rows = Math.ceil(lesson.steps / perRow);
  const rowH = TOP + (NSTR - 1) * SG + 40;
  const W = X0 + perRow * STEP + 14;
  const H = rowH * rows;
```

and change the opening tag so the SVG has intrinsic size:

```js
  const P = [`<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" font-family="'Share Tech Mono',monospace">`];
```

- [ ] **Step 2: Bigger string labels, counts and chord marks**

- String label (line ~5432): `font-size="${F + 2}"` → `font-size="${F}"` and add `font-weight="bold"`.
- Count label (line ~5439): `font-size="${/\d/.test(lab) ? F : F - 1}"` → `font-size="${/\d/.test(lab) ? F - 2 : F - 3}"`.
- Chord mark (line ~5445): `font-size="${F}"` → `font-size="${F - 1}"` and add `font-weight="bold"`.

- [ ] **Step 3: Replace the note drawing**

Replace the body of the `lesson.ev.forEach(e => { … })` loop (lines 5461-5488) with:

```js
  lesson.ev.forEach(e => {
    const si = rollString(e.s, chord, tuning);
    const r = Math.floor(e.t / perRow);
    const x = ex(e.t), y = sy(r, si), k = STEP / 64;
    // a note is a digit on the string line with a panel-coloured knockout
    // behind it, as printed tab does it: no ring to compete with the glyph
    const note = (cx, f) => {
      const w = String(f).length > 1 ? 2 * R + 8 : 2 * R;
      P.push(`<rect x="${cx - w / 2}" y="${y - R + 1}" width="${w}" height="${2 * R - 2}" rx="3"/>`);
      P.push(`<text class="fr" x="${cx}" y="${y + 5.5}" font-size="${F}" font-weight="bold" text-anchor="middle">${f}</text>`);
    };
    P.push(`<g class="lev" data-t="${e.t}">`);
    if(e.sl !== undefined){                             // slide: small from-fret gliding up the connector into the target
      const x2 = x + 32 * k;
      P.push(`<text class="slf" x="${x - 4 * k}" y="${y + 4}" font-size="${F - 3}" text-anchor="middle">${e.sl}</text>`);
      P.push(`<line class="sl" x1="${x + 4 * k}" y1="${y + 4}" x2="${x2 - R - 2}" y2="${y - 4}"/>`);
      note(x2, e.to);
    }else{
      const f = rollFret(e, si, chord, tuning);
      if(f < 0) P.push(`<text class="mute" x="${x}" y="${y + 5}" font-size="${F - 1}" font-weight="bold" text-anchor="middle">×</text>`);
      else note(x, f);
    }
    // clawhammer tab assumes the thumb on the 5th string and marks only a
    // DROP to any other string — so the drops are the only T's on the page,
    // which is the whole lesson. Rolls keep their full T/I/M fingering.
    const droneThumb = lesson.claw && e.fin === "T" && tuning.drone && si === tuning.drone.s;
    if(e.fin && !droneThumb)
      P.push(`<text class="fin" data-fin="${e.fin}" x="${x}" y="${y - R - 5}" font-size="${F - 3}" font-weight="bold" text-anchor="middle">${e.fin}</text>`);
    P.push(`</g>`);
  });
```

- [ ] **Step 4: Bar highlight never wider than a row**

In `lnFrame` (line ~5592) change `hi.setAttribute("width", G.BAR * G.STEP);` to `hi.setAttribute("width", Math.min(G.BAR, G.perRow) * G.STEP);`.

- [ ] **Step 5: CSS**

Replace lines 519-534 (`#lnTab svg{…}` through `.lev.lit text.fr{…}`) with:

```css
  #lnTab svg{ display:block; min-width:0; width:auto; height:auto; }   /* 1:1, never scaled down */
  .lev rect{ fill:var(--panel); }
  .lev text.fr{ fill:var(--text); }
  .lev text.slf{ fill:var(--dim); }
  /* picking hand at a glance: the thumb is the anchor every pattern is
     built around, so it gets the accent colour — the letter still carries
     the meaning where a theme flattens the hues */
  .lev text.fin{ fill:var(--red); }
  .lev text.fin[data-fin="T"]{ fill:var(--yellow); }
  .lev text.fin[data-fin="I"]{ fill:var(--cyan); }
  .lev text.fin[data-fin="R"]{ fill:var(--dim); }
  #lnTab .brush{ fill:none; stroke:var(--red); stroke-width:1.6; opacity:.8; }
  .lev text.mute{ fill:var(--dim); }
  .lev .sl{ stroke:var(--red); stroke-width:2; fill:none; }
  .lev.lit rect{ fill:var(--yellow); filter:drop-shadow(0 0 7px var(--yellow)); }
  .lev.lit text.fr{ fill:var(--ink); }
```

- [ ] **Step 6: Check in the browser**

Open `http://127.0.0.1:8092/`, LEARN, Forward Roll. In the console:

```js
const s = document.querySelector("#lnTab svg");
console.log(s.getBoundingClientRect().width === s.viewBox.baseVal.width, s.querySelectorAll(".lev rect").length, s.querySelectorAll(".lev circle").length);
```

Expected: `true 8 0`. Resize the window to 390px wide and re-pick the lesson: the roll shows as two rows of 4 (8-slot bar, `fit` = 5). Press PLAY: the playhead sweeps both rows, the yellow bar wash is one row wide, lit notes fill yellow. Pick SONG and a saved song: rows of whole bars, no horizontal scroll at 1280px.

- [ ] **Step 7: Commit**

```bash
git add index.html
git commit -m "Learn tab reads like printed tab: bold digits on knockouts, rows wrap instead of shrinking

Claude-Session: https://claude.ai/code/session_013L3Q2CzvMrFqiEcR9vArz8"
```

### Task 5: chord diagram labels

**Files:**
- Modify: `index.html:3010-3046` (`renderChordSVG` barre + dot block)

- [ ] **Step 1: Apply these exact substitutions inside `renderChordSVG` only**

| Line (approx) | Old | New |
|---|---|---|
| 3014 (theory-view barre rail) | `x0 - 8.5`, `y - 8.5`, `+ 17`, `height="17" rx="8.5"` | `x0 - 9.5`, `y - 9.5`, `+ 19`, `height="19" rx="9.5"` |
| 3018 (finger barre) | same four values | same four values as above |
| 3020 (barre finger label) | `font-size="10.5"` | `font-size="12"` |
| 3027 (× mute) | `font-size="13"` | `font-size="15" font-weight="bold"` |
| 3030 (open-string ring) | `r="${face ? 8 : 5}"` … `stroke-width="1.6"` | `r="${face ? 9 : 6}"` … `stroke-width="2"` |
| 3031 (open-string face) | `font-size="8.5"` | `font-size="10.5" font-weight="bold"` |
| 3038 (colour-tone dot) | `r="8.5"` | `r="9.5"` |
| 3039 (colour-tone face) | `font-size="9"` | `font-size="11" font-weight="bold"` |
| 3041 (dot) | `r="8.5"` | `r="9.5"` |
| 3043 (dot label) | `font-size="${face ? 9 : 10.5}"` | `font-size="${face ? 11 : 12}"` |

The `y + 3.4` / `y + 3.6` baselines become `y + 4` on the three dot-label lines so the larger glyphs stay centred.

- [ ] **Step 2: Check**

Run: `node tools/validate-chords.mjs` (the renderer is not under test but the file must still parse) and open the grid. On the paper skin, zoom on a G7 card: digits 2 and 3 are clearly bolder than before; the × above a muted string reads at card size. Open a chord fullscreen: Dots → NOTES → DEGREES all read.

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "Chord diagram dots: bigger, bold labels in slightly bigger dots

Claude-Session: https://claude.ai/code/session_013L3Q2CzvMrFqiEcR9vArz8"
```

### Task 6: map and halo labels

**Files:**
- Modify: `index.html:3199-3209` (`renderHaloSVG` note block), `index.html:3229-3238` (`fretMapNote`)

- [ ] **Step 1: Halo notes (lines 3199-3209)**

| Old | New |
|---|---|
| `r="17.5"` (home ring) | `r="18.5"` |
| `r="13.5"` … `font-size="11" font-weight="bold"` | `r="14.5"` … `font-size="13" font-weight="bold"` |
| `r="12.5"` … `font-size="11"` | `r="13.5"` … `font-size="13" font-weight="bold"` |
| `r="12"` … `font-size="10.5"` | `r="13"` … `font-size="13" font-weight="bold"` |

Baselines `y + 4` → `y + 4.5`.

- [ ] **Step 2: Map notes (lines 3229-3238)**

| Old | New |
|---|---|
| `r="13"` … `font-size="10.5" font-weight="bold"` | `r="14"` … `font-size="13" font-weight="bold"` |
| `r="12"` … `font-size="10.5"` | `r="13"` … `font-size="13" font-weight="bold"` |
| `r="11.5"` … `font-size="10"` | `r="12.5"` … `font-size="13" font-weight="bold"` |

Baselines `y + 3.8` → `y + 4.5`.

- [ ] **Step 3: Check**

Open MAP in key C major, then a chord fullscreen with HALO on. Note names read at phone width; the FIND IT quiz still hides non-root labels (the `.quiz … text{ opacity:0 }` rules select by element, so nothing else changes).

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "Map and halo note names at 13px bold

Claude-Session: https://claude.ai/code/session_013L3Q2CzvMrFqiEcR9vArz8"
```

## Phase 2: nav, router and hubs

### Task 7: nav bar and hub containers

**Files:**
- Modify: `index.html:988-1015` (wrap controls/main/pager in the Chords hub; add four hub sections and the nav), `index.html` style block (new `#nav` and `.hub` rules, inserted after the `.pager` rules, ~line 290)

**Interfaces:**
- Produces: `<nav id="nav">` with five `<a href="#hub" data-hub="hub">`; five hub containers `#hub-chords`, `#hub-songs`, `#hub-practice`, `#hub-learn`, `#hub-tools` (all but chords start `hidden`). Task 8 adds `showHub(name)`; Task 9 fills the four new hubs.

- [ ] **Step 1: Markup**

Wrap the existing `<div class="controls">…</div>`, `<main>…</main>` and `<div class="pager">…</div>` (lines 988-1015) in `<section class="hub" id="hub-chords">…</section>`. Directly after its closing tag add:

```html
<section class="hub" id="hub-songs" hidden>
  <div class="hubwrap">
    <h2 class="hubtitle">SONGS://</h2>
    <div class="hubacts" id="songActs"></div>
    <div class="hublist" id="songList"></div>
  </div>
</section>
<section class="hub" id="hub-practice" hidden>
  <div class="hubwrap">
    <h2 class="hubtitle">PRACTICE://</h2>
    <div class="hublist" id="pracList"></div>
  </div>
</section>
<section class="hub" id="hub-learn" hidden>
  <div class="hubwrap">
    <h2 class="hubtitle">LEARN://</h2>
    <div class="hublist" id="learnList"></div>
  </div>
</section>
<section class="hub" id="hub-tools" hidden>
  <div class="hubwrap">
    <h2 class="hubtitle">TOOLS://</h2>
    <div class="hublist" id="toolList"></div>
  </div>
</section>
<nav id="nav" aria-label="Sections">
  <a href="#chords"   data-hub="chords">Chords</a>
  <a href="#songs"    data-hub="songs">Songs</a>
  <a href="#practice" data-hub="practice">Practice</a>
  <a href="#learn"    data-hub="learn">Learn</a>
  <a href="#tools"    data-hub="tools">Tools</a>
</nav>
```

- [ ] **Step 2: CSS**

Insert after the `.pager button:not(:disabled):active{…}` rule (~line 289):

```css
  /* ── hubs + nav: bottom tab bar on phones/tablets, left rail on desktop ── */
  .hub[hidden]{ display:none; }
  .hubwrap{ max-width:var(--content-w); margin:0 auto; padding:14px 14px 96px; }
  .hubtitle{
    font-family:var(--font-h); font-weight:700; font-size:clamp(24px, 6vw, 34px);
    letter-spacing:.14em; color:var(--yellow); margin-bottom:12px;
  }
  .hubacts{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:14px; }
  .hublist{ display:grid; gap:10px; grid-template-columns:1fr; }
  @media (min-width:700px){ .hublist{ grid-template-columns:repeat(2, 1fr); } }
  @media (min-width:1280px){ .hublist{ grid-template-columns:repeat(3, 1fr); } }
  .hubcard{
    display:block; width:100%; text-align:left; min-height:72px; padding:12px 14px;
    background:var(--panel); color:var(--text); border:1px solid var(--line);
    font-family:var(--font-m); cursor:pointer; position:relative;
  }
  .hubcard:hover, .hubcard:active{ border-color:var(--cyan); }
  .hubcard b{ display:block; font-family:var(--font-h); font-weight:700; font-size:var(--fs-l); letter-spacing:.1em; color:var(--cyan); text-transform:uppercase; }
  .hubcard small{ display:block; font-size:var(--fs-s); color:var(--dim); line-height:1.5; margin-top:4px; }
  .hubcard .best{ position:absolute; top:12px; right:14px; font-size:var(--fs-s); color:var(--yellow); letter-spacing:.1em; }
  .hubcard.on b{ color:var(--yellow); }
  .hubcard[disabled]{ opacity:.45; cursor:default; }
  .pager{ bottom:calc(56px + env(safe-area-inset-bottom, 0px)); }   /* the pager sits on top of the nav bar */
  #nav{
    position:fixed; left:0; right:0; bottom:0; z-index:7900;   /* under every dialog (8000+), over the grid */
    display:flex; background:var(--bg2); border-top:1px solid var(--line2);
    padding-bottom:env(safe-area-inset-bottom, 0px);
  }
  #nav a{
    flex:1; min-height:56px; display:flex; align-items:center; justify-content:center;
    font-family:var(--font-h); font-weight:700; font-size:var(--fs-s); letter-spacing:.1em;
    text-transform:uppercase; color:var(--dim); text-decoration:none; border-top:3px solid transparent;
  }
  #nav a[aria-current="page"]{ color:var(--yellow); border-top-color:var(--yellow); }
  body{ padding-bottom:calc(56px + env(safe-area-inset-bottom, 0px)); }
  @media (min-width:1100px){
    #nav{ top:0; bottom:0; right:auto; width:120px; flex-direction:column; justify-content:flex-start;
          border-top:0; border-right:1px solid var(--line2); padding-top:calc(90px + env(safe-area-inset-top, 0px)); }
    #nav a{ flex:0 0 auto; min-height:56px; border-top:0; border-left:3px solid transparent; }
    #nav a[aria-current="page"]{ border-left-color:var(--yellow); }
    body{ padding-bottom:0; padding-left:120px; }
    header{ padding-left:calc(120px + 14px); }   /* the rail covers the title's left edge otherwise */
    .pager{ bottom:0; left:calc(50% + 60px); }   /* re-centre on the content column, which the rail shifted right */
  }
```

The `body{ padding-bottom }` rule replaces the existing `padding-bottom:env(safe-area-inset-bottom)` on `body` (line ~81): delete that one.

- [ ] **Step 3: Check**

Load the page: the chord grid still renders, a five-tab bar sits at the bottom (left rail at ≥1100px), no tab highlighted yet. Tapping a tab changes the hash and nothing else (Task 8 wires it).

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "Five-hub nav bar and empty hub containers

Claude-Session: https://claude.ai/code/session_013L3Q2CzvMrFqiEcR9vArz8"
```

### Task 8: hash router

**Files:**
- Modify: `index.html` script: add the router block just before the service-worker IIFE at the end of the script (~line 7520); convert every ✕ / backdrop / Escape / in-app open call site listed below.

**Interfaces:**
- Consumes: `openMap, openStyles, openLearn, openMine, openTuner, openSongEditor, openPerf, openModal, openTuningForge, openSetEditor, openAu` and their `close*` twins; `setLnKind(k)`, `setMineMode(m)`, `pracToggle(mode, start)`, `startFollow/startHear/startFind`, `mFindStart()`, `modalHalo`, `renderModalView()`, `chordList()`, `filtered()`, `$("#mnAbc")` click handler.
- Produces: `go(route, open?)`, `navBack()`, `showHub(name)`, `currentHub()`, `ROUTES` (object, keys are `hub/sub` strings), `HUBS` (array). Task 9's cards call `go(...)`. Task 10's check parses `ROUTES`.

- [ ] **Step 1: Router block**

```js
/* ── navigation: five hubs + a hash router ───────────────────────
   The hash says what is on screen. go() pushes a route and applies it;
   the hashchange handler (browser back, nav taps, pasted links) applies
   whatever the hash now says. Applying a route closes every open dialog
   first, so the back gesture always dismisses the thing on top. Sub-dialogs
   (forge, ABC, from-audio, set list editor, melody editor) are not routed:
   they open over whatever is up and close with their own ✕; a back gesture
   while one is open dismisses everything down to the previous route. */
const HUBS = ["chords", "songs", "practice", "learn", "tools"];
const noop = () => {};
const ROUTES = {
  "chords/map":        openMap,
  "chords/chord":      noop,                           // fullscreen chord: opened by a tap, never from a cold link
  "songs/edit":        openSongEditor,
  "songs/perform":     openPerf,
  "practice/follow":   () => { openMap(); pracToggle("follow", startFollow); },
  "practice/hear":     () => { openMap(); pracToggle("hear", startHear); },
  "practice/find":     () => { openMap(); pracToggle("find", startFind); },
  "practice/halo":     () => { const c = filtered()[0] || chordList()[0]; if(!c) return; openModal(c); mFindStart(); },
  "practice/tap":      () => { openMine(); setMineMode("tap"); },
  "practice/hearme":   () => { openMine(); setMineMode("hear"); },
  "practice/listen":   () => { openMine(); setMineMode("listen"); },
  "learn/rolls":       () => { setLnKind("roll"); openLearn(); },
  "learn/licks":       () => { setLnKind("lick"); openLearn(); },
  "learn/song":        () => { setLnKind("song"); openLearn(); },
  "learn/styles":      openStyles,
  "tools/tuner":       openTuner,
};
const currentHub = () => { const h = location.hash.slice(1).split("/")[0]; return HUBS.includes(h) ? h : "chords"; };
function closeOverlays(){                                // innermost first; close* functions are untouched
  if($("#abcEd").classList.contains("open")) closeAbc();
  if($("#auEd").classList.contains("open")) closeAu();
  if($("#tunEd").classList.contains("open")) closeTuningForge();
  if($("#setEd").classList.contains("open")) closeSetEditor();
  if($("#perf").classList.contains("open")) closePerf();
  if($("#mineov").classList.contains("open")) closeMine();
  if($("#songEd").classList.contains("open")) closeSongEditor();
  if($("#tuner").classList.contains("open")) closeTuner();
  if($("#styleov").classList.contains("open")) closeStyles();
  if($("#learnov").classList.contains("open")) closeLearn();
  if($("#mapov").classList.contains("open")) closeMap();
  if($("#modal").classList.contains("open")) closeModal();
}
function showHub(h){
  HUBS.forEach(x => { $("#hub-" + x).hidden = x !== h; });
  document.querySelectorAll("#nav a").forEach(a => {
    if(a.dataset.hub === h) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  if(h === "songs") drawSongsHub();
  if(h === "practice") drawPracticeHub();
  if(h === "learn") drawLearnHub();
  if(h === "tools") drawToolsHub();
}
let pendingOpen = null;                                  // a one-shot opener carried by go() (a tapped chord, a chosen set list)
function applyRoute(){
  const r = location.hash.slice(1) || "chords";
  closeOverlays();
  showHub(currentHub());
  const open = pendingOpen || ROUTES[r] || noop;
  pendingOpen = null;
  open();
}
function go(route, open){
  pendingOpen = open || null;
  if(location.hash.slice(1) !== route) history.pushState({ ov: route.includes("/") }, "", "#" + route);
  applyRoute();
}
function navBack(){                                      // what every ✕, backdrop tap and Escape calls
  if(!document.querySelector('[role="dialog"].open')) return;
  if(history.state && history.state.ov) history.back();   // we pushed this entry: pop it, hashchange applies the hub
  else location.replace("#" + currentHub());               // cold deep link: nothing to pop, just show the hub
}
addEventListener("hashchange", applyRoute);
applyRoute();
```

`drawSongsHub/drawPracticeHub/drawLearnHub/drawToolsHub` are defined in Task 9; until then add four one-line stubs `function drawSongsHub(){}` etc. directly above this block and delete them in Task 9.

- [ ] **Step 2: ✕ buttons, backdrops and Escape go through navBack**

Replace the handler in each of these listeners with `navBack` (the `close*` function stays defined and is still called by `closeOverlays`):

| Line | Listener | New handler |
|---|---|---|
| 4476 | `#mclose` click | `navBack` |
| 4477 | `#modal` backdrop | `if(e.target === e.currentTarget) navBack();` |
| 4554-4555 | `#mapclose`, `#mapov` backdrop | same pattern |
| 4836-4837 | `#styclose`, `#styleov` backdrop | same |
| 5777-5778 | `#lnclose`, `#learnov` backdrop | same |
| 6169-6170 | `#mnclose`, `#mineov` backdrop | same, **except** keep `closeMine` when `mine && mine.kind === "edit"` (the melody editor is a sub-dialog): `() => mine && mine.kind === "edit" ? closeMine() : navBack()` |
| 7066 | `#pclose` click | `navBack` |
| 7342, 7344 | `#tclose`, `#tuner` backdrop | same |
| 4364 | `#seClose` click | `navBack` |

Leave `#tfClose`, `#abClose`, `#auClose`, `#stClose` and their backdrops on their own `close*` functions (sub-dialogs).

Replace the Escape branch of the keydown handler (lines 7424-7436) with:

```js
  if(e.key === "Escape"){
    if($("#abcEd").classList.contains("open")) return closeAbc();
    if($("#auEd").classList.contains("open")) return closeAu();
    if($("#tunEd").classList.contains("open")) return closeTuningForge();
    if($("#setEd").classList.contains("open")) return closeSetEditor();
    if(mine && mine.kind === "edit") return closeMine();
    return navBack();
  }
```

- [ ] **Step 3: In-app openers push a route**

| Line | Old | New |
|---|---|---|
| 4466, 4473 | `if(chord) openModal(chord);` | `if(chord) go("chords/chord", () => openModal(chord));` |
| 4363 | `state.setlist ? openSetEditor(state.setlist) : openSongEditor()` | `state.setlist ? openSetEditor(state.setlist) : go("songs/edit")` |
| 4853 | `if(b.dataset.play) openPerf();` | `if(b.dataset.play) go("songs/perform");` |
| 7065 | `$("#perfBtn").addEventListener("click", openPerf);` | `$("#perfBtn").addEventListener("click", () => go("songs/perform"));` |
| 6621-6627 | the whole `$("#auOpen").onclick = () => { closeAu(); closeMine(); openLearn(); setLnKind("song"); … };` | `$("#auOpen").onclick = () => go("learn/song", () => { setLnKind("song"); openLearn(); const i = lnLessons().findIndex(l => l.name === name); if(i >= 0){ $("#lnLesson").value = String(i); drawLearn(); } });` (the two `close*` calls go: `applyRoute` closes everything first) |
| 6636 | `closeSongEditor(); openAu();` | unchanged (sub-dialog over the editor) |

Lines 4220-4224 (the five act chips) are deleted in Task 11.

- [ ] **Step 4: Check**

In Chrome at 390px wide:
1. Load `/#learn/rolls` cold: Learn hub behind, learn overlay open on Rolls. Tap ✕: overlay closes, hub stays, hash is `#learn`.
2. Tap CHORDS tab, tap a card: fullscreen chord. Press the browser back button: chord closes, grid stays.
3. Tap PRACTICE tab, type in the console `go("practice/find")`: map opens with FIND IT lit. Back: map closes, Practice hub shows.
4. Escape on a bare hub does nothing (no console error).

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "Hash router: hubs and overlays as routes, back gesture closes the thing on top

Claude-Session: https://claude.ai/code/session_013L3Q2CzvMrFqiEcR9vArz8"
```

### Task 9: hub screens

**Files:**
- Modify: `index.html` script: replace the four `draw*Hub` stubs from Task 8 with the real functions (same place, above the router block); add `"tools/forge": openTuningForge` to `ROUTES`; two one-line additions in the `storeSongs`/`storeSets` wrappers (~lines 6483-6484)
- Modify: `index.html` style block: hub-card extras after the Task 7 rules

**Interfaces:**
- Consumes: `go`, `openSetEditor(name)`, `openAu()`, `$("#mnAbc")` click handler (clears and opens the ABC dialog), `$("#seExport")`/`$("#seImport")` click handlers, `$("#songSel")` change handler (selects a song or set list for the grid), `pracKey()`, `PRAC_STORE` (fields `hearMs`, `find`), `MINE_STORE` (key `tuning|tune|mode`, ms), `fmtSecs(ms)`, `FIND_ROUND`, `TUNE_LIBRARY`, `SCALES`, `mapKeySel`, `mapScaleSel`, `THEMES`, `tabsmithHere`, `lessonsFor(tuningKey)`, `loadSongs()`, `loadSets()`, `songData(v)`, `escHTML(s)`, `refreshSongSel()`.
- Produces: `drawSongsHub()`, `drawPracticeHub()`, `drawLearnHub()`, `drawToolsHub()`; the `.hubcard[data-go]` and `[data-proxy]` click delegation.

- [ ] **Step 1: Card helpers and the four draw functions**

```js
/* ── hub screens: every feature as a named card with a one-line blurb ── */
const hubCard = (route, title, blurb, extra = "", attrs = "") =>
  `<button class="hubcard" data-go="${route}" ${attrs}><b>${title}</b><small>${blurb}</small>${extra}</button>`;
const storedBest = (store, key) => { try{ return (JSON.parse(localStorage.getItem(store)) || {})[key]; }catch(e){ return undefined; } };
const bestTag = v => v === undefined ? "" : `<span class="best">BEST ${v}</span>`;

function drawPracticeHub(){
  const pb = storedBest(PRAC_STORE, pracKey()) || {};            // the map's current key × scale × box
  const tune = TUNE_LIBRARY.length ? TUNE_LIBRARY[0].name : "";
  const mb = m => { const v = storedBest(MINE_STORE, [state.tuning, tune, m].join("|")); return bestTag(v === undefined ? undefined : fmtSecs(v)); };
  $("#pracList").innerHTML =
    `<div class="hubsec">ON THE MAP · ${mapKeySel.value.toUpperCase()} · ${SCALES[mapScaleSel.value].label.toUpperCase()}</div>` +
    hubCard("practice/follow", "Follow", "Watch and hear the scale walked at tempo, up from the lowest root and back down.") +
    hubCard("practice/hear", "Hear Me", "Play the scale into the mic; the target only moves when you play the note. Clean passes are timed.", bestTag(pb.hearMs === undefined ? undefined : fmtSecs(pb.hearMs))) +
    hubCard("practice/find", "Find It", "The map goes dark except the roots. Tap the asked degree. Ten prompts a round.", bestTag(pb.find === undefined ? undefined : pb.find + "/" + FIND_ROUND)) +
    `<div class="hubsec">ON A CHORD</div>` +
    hubCard("practice/halo", "Find It on the halo", "The notes in reach around the shape you are holding, quizzed by degree. Opens on the first chord in the grid.") +
    `<div class="hubsec">TUNE MINER · ${tune.toUpperCase()}</div>` +
    hubCard("practice/tap", "Tap It", "Pluck a melody out of chord shapes one lit note at a time.", mb("tap")) +
    hubCard("practice/hearme", "Hear Me", "Same tune, but the mic has to hear you play each note.", mb("hear")) +
    hubCard("practice/listen", "Listen", "Hear the whole tune mined out of the shapes, looping at tempo.");
}

function drawLearnHub(){
  const has = k => lessonsFor(state.tuning).some(l => l.kind === k);
  const songs = Object.keys(loadSongs()).length;
  $("#learnList").innerHTML =
    hubCard("learn/rolls", "Rolls", "Two dozen right-hand patterns as animated tab: bluegrass rolls, Travis, clawhammer, waltz and more. Pick any chord to roll over.") +
    hubCard("learn/licks", "Slide licks", "Blues slide phrases written for this tuning, plus three progression lessons that stitch them into changes.", "", has("lick") ? "" : "disabled") +
    hubCard("learn/song", "Song as tab", "Any saved song laid out bar by bar with a roll carried through its changes, or its own tapped-in melody.", "", songs ? "" : "disabled") +
    hubCard("learn/styles", "Styles", "Blues, country and folk primers: the genre's scale on the neck and its standard progressions in any key.");
}

function drawToolsHub(){
  const t = THEMES.find(t => t.id === (document.documentElement.dataset.theme || "")) || THEMES[0];
  const on = id => $(id).classList.contains("on");
  const proxy = (id, title, blurb) => `<button class="hubcard${on(id) ? " on" : ""}" data-proxy="${id}"><b>${title}</b><small>${blurb}</small></button>`;
  $("#toolList").innerHTML =
    hubCard("tools/tuner", "Tuner", "Mic pitch detection for every string of the current tuning.") +
    hubCard("tools/forge", "Tuning forge", "Name a custom tuning, pick its open strings, and forge a full chord library for it.") +
    proxy("#themeBtn", `Skin · ${t.label}`, "Cycle the colour scheme: Night City, Amber Term, Phosphor, Synthwave, Field Mode.") +
    proxy("#lhBtn", `Left-handed · ${on("#lhBtn") ? "ON" : "OFF"}`, "Mirror every diagram and map.") +
    ($("#d5Btn").style.display !== "none"
      ? proxy("#d5Btn", `5th string · ${on("#d5Btn") ? "SHOWN" : "HIDDEN"}`, "Printed banjo charts leave the drone out. Show or hide it in chord diagrams.")
      : "") +
    proxy("#awakeBtn", `Keep awake · ${on("#awakeBtn") ? "ON" : "OFF"}`, "Hold the screen on while CHORDWARE is open.") +
    `<div class="hubcard" style="cursor:default"><b>Library sync</b><small>${tabsmithHere
      ? "Songs and set lists are kept on this server. Every device on the tailnet sees the same library."
      : "Offline: songs and set lists live in this browser only."}</small></div>`;
}

function drawSongsHub(){
  const songs = loadSongs(), sets = loadSets();
  const esc = n => n.replace(/"/g, "&quot;");
  $("#songActs").innerHTML =
    `<button class="prbtn" data-act="new">+ Song</button>` +
    `<button class="prbtn" data-act="newset">+ Set list</button>` +
    `<button class="prbtn" data-act="abc">ABC import</button>` +
    (tabsmithHere ? `<button class="prbtn" data-act="audio">From audio</button>` : "") +
    `<button class="prbtn" data-act="export">Export all</button>` +
    `<button class="prbtn" data-act="import">Import</button>`;
  const row = (kind, n, meta) =>
    `<div class="hubcard songrow" role="button" tabindex="0" data-kind="${kind}" data-name="${esc(n)}">` +
      `<b>${kind === "set" ? "≡" : "♪"} ${escHTML(n)}</b><small>${meta}</small>` +
      `<span class="rowacts"><button data-act="chords" title="Show its chords in the grid">Chords</button>` +
      `<button data-act="perform" title="Performance mode">▶</button></span></div>`;
  const names = Object.keys(songs).sort(), setNames = Object.keys(sets).sort();
  $("#songList").innerHTML =
    (names.length ? names.map(n => {
        const d = songData(songs[n]), cs = d.chords.trim().split(/\s+/).filter(Boolean);
        return row("song", n, `${cs.length} chords${songs[n].melody ? " · melody" : ""}${d.lyrics.trim() ? " · lyrics" : ""}`);
      }).join("")
      : `<div class="hubcard" style="cursor:default"><small>No songs yet. + SONG pastes one straight from a tab site.</small></div>`) +
    setNames.map(n => row("set", n, `${(sets[n] || []).length} songs`)).join("");
}

/* hub cards: a route, a proxy for one of the hidden header toggles, or a song row */
document.addEventListener("click", e => {
  const b = e.target.closest(".hubcard"); if(!b) return;
  if(b.dataset.go){ go(b.dataset.go); return; }
  if(b.dataset.proxy){ $(b.dataset.proxy).click(); drawToolsHub(); }
});
$("#hub-songs").addEventListener("click", e => {
  const a = e.target.closest("[data-act]"), r = e.target.closest(".songrow");
  const act = a ? a.dataset.act : "";
  if(act === "new"){ state.song = ""; state.setlist = ""; state.query = ""; $("#search").value = ""; refreshSongSel(); go("songs/edit"); return; }
  if(act === "newset"){ openSetEditor(""); return; }
  if(act === "abc"){ $("#mnAbc").click(); return; }
  if(act === "audio"){ openAu(); return; }
  if(act === "export"){ $("#seExport").click(); return; }
  if(act === "import"){ $("#seImport").click(); return; }
  if(!r) return;
  const kind = r.dataset.kind, name = r.dataset.name;
  const select = () => {                                  // exactly what picking it in the grid's SONG:// dropdown does
    $("#songSel").value = (kind === "set" ? "set:" : "song:") + name;
    $("#songSel").dispatchEvent(new Event("change"));
  };
  select();
  if(act === "perform"){ go("songs/perform"); return; }
  if(act === "chords"){ go("chords"); return; }
  if(kind === "set") openSetEditor(name); else go("songs/edit");
});
$("#hub-songs").addEventListener("keydown", e => {
  if((e.key === "Enter" || e.key === " ") && e.target.classList.contains("songrow")){ e.preventDefault(); e.target.click(); }
});
```

Add to `ROUTES`: `"tools/forge": openTuningForge,`.

- [ ] **Step 2: The Songs hub redraws when the library changes**

In the two wrappers (~lines 6483-6484):

```js
storeSongs = function(s){ libMarkChanges("songs", loadSongs(), s); storeSongs0(s); libPush(); if(!$("#hub-songs").hidden) drawSongsHub(); };
storeSets  = function(s){ libMarkChanges("setlists", loadSets(), s); storeSets0(s); libPush(); if(!$("#hub-songs").hidden) drawSongsHub(); };
```

- [ ] **Step 3: CSS**

After the Task 7 hub rules:

```css
  .hubsec{ grid-column:1/-1; font-size:var(--fs-s); letter-spacing:.14em; color:var(--dim); margin-top:6px; }
  .songrow{ padding-right:150px; }
  .rowacts{ position:absolute; top:12px; right:12px; display:flex; gap:6px; }
  .rowacts button{
    min-height:44px; min-width:44px; padding:0 12px;
    background:transparent; color:var(--cyan); border:1px solid var(--cyan);
    font-family:var(--font-h); font-weight:600; font-size:var(--fs-s); letter-spacing:.1em;
    text-transform:uppercase; cursor:pointer;
  }
  .rowacts button:active{ background:var(--cyan); color:var(--ink); }
```

- [ ] **Step 4: Check**

- PRACTICE: eight cards under three section labels; tapping FIND IT opens the map dark with the quiz running; back returns to the hub; after a round, the card shows `BEST n/10`.
- LEARN: four cards; SLIDE LICKS is disabled on a forged tuning with no licks; STYLES opens the styles overlay.
- TOOLS: SKIN card cycles the skin and its title updates; LEFT-HANDED flips diagrams; 5TH STRING card appears only on gDGBD.
- SONGS: rows for every saved song with counts; ▶ performs; CHORDS lands on the grid filtered to that song; tapping a row opens the editor; + SET LIST opens the set editor; saving a song while on the hub redraws the list.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "Songs, Practice, Learn and Tools hubs: every feature as a named card

Claude-Session: https://claude.ai/code/session_013L3Q2CzvMrFqiEcR9vArz8"
```

### Task 10: route check

**Files:**
- Modify: `tools/check-ui.mjs` (append section 2)

- [ ] **Step 1: Append to the checker, before the final `console.log`/`process.exit`**

```js
/* 2. routing: every ROUTES key names a hub, every go()/hubCard() target is
      a hub or a route, and every hub has its section */
const js = html.slice(html.lastIndexOf("<script>"), html.lastIndexOf("</script>"));
const hubs = JSON.parse(js.match(/const HUBS = (\[[^\]]*\])/)[1]);
const rblock = js.slice(js.indexOf("const ROUTES = {"), js.indexOf("\n};", js.indexOf("const ROUTES = {")));
const routes = [...rblock.matchAll(/^\s*"([a-z]+\/[a-z]+)":/gm)].map(m => m[1]);
const used = [...js.matchAll(/(?:\bgo|hubCard)\("([a-z/]+)"/g)].map(m => m[1]);
for(const r of routes) if(!hubs.includes(r.split("/")[0])){ console.error(`route ${r}: unknown hub`); bad++; }
for(const u of used) if(!hubs.includes(u) && !routes.includes(u)){ console.error(`go("${u}"): no such route`); bad++; }
for(const h of hubs){
  if(!html.includes(`id="hub-${h}"`)){ console.error(`hub ${h}: no <section id="hub-${h}">`); bad++; }
  if(!html.includes(`data-hub="${h}"`)){ console.error(`hub ${h}: no nav link`); bad++; }
}
if(!bad) console.log(`routes: ${routes.length} routes over ${hubs.length} hubs clean`);
```

and change the final line to `console.log(bad ? `${bad} failure(s)` : "ui checks clean"); process.exit(bad ? 1 : 0);` (the contrast section's own `console.log` line is removed; keep its `console.error` lines).

- [ ] **Step 2: Run**

Run: `node tools/check-ui.mjs`
Expected: `routes: 17 routes over 5 hubs clean` then `ui checks clean`. Temporarily change `"tools/tuner"` to `"tool/tuner"` in `ROUTES`, run again, expect `route tool/tuner: unknown hub` and exit 1; revert.

- [ ] **Step 3: Commit**

```bash
git add tools/check-ui.mjs
git commit -m "check-ui: every route names a hub, every go() target exists

Claude-Session: https://claude.ai/code/session_013L3Q2CzvMrFqiEcR9vArz8"
```

### Task 11: chip row, header and README cleanup

**Files:**
- Modify: `index.html:4211-4224` (chips), `index.html:988-994` (controls row 1), `index.html:980-983` (header buttons), `README.md`

- [ ] **Step 1: Chips are categories only**

Replace lines 4211-4217 with:

```js
$("#chips").innerHTML = CATS.map(c =>
  `<button class="chip${c.id === state.cat ? " on" : ""}" data-cat="${c.id}">${c.label}</button>`).join("");
```

and delete the five `if(b.id === "…Chip")` lines (4220-4224) from the click handler.

- [ ] **Step 2: GRID / MAP switch on the Chords hub**

In `.row1` after `#dotToggle` add:

```html
    <button id="mapBtn" title="The whole neck: every in-key note, coloured by degree">Map</button>
```

Listener (next to the `#dotToggle` listener, ~line 4452): `$("#mapBtn").addEventListener("click", () => go("chords/map"));`

CSS: extend the Task 2 selector `#ornToggle, #dotToggle{` to `#ornToggle, #dotToggle, #mapBtn{` and add `#mapBtn{ color:var(--yellow); border-color:var(--yellow); }`.

- [ ] **Step 3: Header keeps only the tuning picker**

Add the `hidden` attribute to `#themeBtn`, `#lhBtn`, `#d5Btn` and `#awakeBtn` (lines 980-983). Their listeners stay; the Tools hub proxies clicks to them. Remove `style="display:none"` from `#d5Btn` and change the line that shows it (`$("#d5Btn").style.display = has ? "" : "none";`, ~line 7364) to `$("#d5Btn").dataset.has = has ? "1" : "";`, and in `drawToolsHub` test `$("#d5Btn").dataset.has` instead of `style.display`.

- [ ] **Step 4: The song editor says what MELODY is for**

After the `<div class="sebtns sesec">…</div>` block in `#songEd` (ends ~line 1266) add:

```html
    <div class="sehint">MELODY: tap the tune onto each chord's halo. It then shows up under PRACTICE as a tune-miner drill and under LEARN › SONG AS TAB.</div>
```

- [ ] **Step 5: README**

Add after the `## Files` table:

```markdown
## Getting around

Five hubs in a bar along the bottom (a rail on the left on wide screens),
each a list of named cards:

- **Chords**: the grid, search, categories, key filter, Dots and Ornaments,
  and MAP for the whole neck.
- **Songs**: every saved song and set list, + SONG (paste from a tab site),
  ABC import, FROM AUDIO, export / import.
- **Practice**: every drill in one place: FOLLOW, HEAR ME and FIND IT on the
  map, FIND IT on a chord's halo, and the tune miner's TAP IT / HEAR ME /
  LISTEN, each card showing your best.
- **Learn**: ROLLS, SLIDE LICKS, SONG AS TAB, STYLES.
- **Tools**: TUNER, TUNING FORGE, SKIN, LEFT-HANDED, 5TH STRING, KEEP AWAKE.

Every hub and overlay has a URL hash (`#practice/find`, `#learn/rolls`), so
the phone back gesture closes what is on top and links can be pasted.
```

Then: `sed -i 's/the MAP chip/CHORDS › MAP/g; s/the LEARN chip/LEARN › ROLLS/g; s/the MINE chip/PRACTICE › TAP IT/g; s/the STYLES chip/LEARN › STYLES/g' README.md` and read the Features list once for any other "chip" that now means a hub card.

- [ ] **Step 6: Check**

Run: `node tools/check-ui.mjs && node tools/validate-chords.mjs`. Load the page: chip row shows ALL / MAJOR / MINOR / 7TH / COLOUR only; MAP button beside Dots opens the map; header shows the title and tuning picker only; TOOLS still cycles the skin.

- [ ] **Step 7: Commit**

```bash
git add index.html README.md
git commit -m "Chip row is categories only; header toggles live in Tools; README explains the hubs

Claude-Session: https://claude.ai/code/session_013L3Q2CzvMrFqiEcR9vArz8"
```

## Phase 3: Galaxy Z Fold layouts

### Task 12: cover screen and unfolded inner screen

**Files:**
- Modify: `index.html` `gridLayout()` (~line 3745), nav CSS from Task 7

- [ ] **Step 1: Near-square viewports get 3 × 3**

Replace `gridLayout` with:

```js
function gridLayout(){
  const w = innerWidth, h = innerHeight, square = w >= 760 && w / h >= .85 && w / h <= 1.25;
  let cols = 2;                          // phone portrait
  if(w >= 1800) cols = 6;
  else if(w >= 1440) cols = 5;
  else if(w >= 1080) cols = 4;           // iPad landscape / laptop
  else if(w >= 820 || w > h) cols = 3;   // iPad portrait / phone landscape / unfolded Fold
  const rows = cols === 2 ? 3 : (h >= 1000 || square ? 3 : 2);   // a near-square screen (Z Fold open) has the height for 3
  return { cols, rows };
}
```

- [ ] **Step 2: Nav labels fit a 370px cover screen**

Add after the `#nav a[aria-current="page"]` rule:

```css
  @media (max-width:400px){ #nav a{ letter-spacing:.02em; padding:0 2px; } }
```

- [ ] **Step 3: Check**

In Chrome resize to 370 × 900 (cover): five nav labels on one row, none wrapped or clipped; grid 2 × 3; LEARN › ROLLS wraps the roll to rows of 4. Resize to 820 × 710 (unfolded): grid 3 × 3, bottom bar (no rail), page info reads `PAGE 1/…` with 9 per page. Resize to 1280 × 800: rail on the left.

- [ ] **Step 4: Commit**

```bash
git add index.html
git commit -m "Z Fold: 3x3 grid on the near-square inner screen, nav labels fit the cover screen

Claude-Session: https://claude.ai/code/session_013L3Q2CzvMrFqiEcR9vArz8"
```

## Phase 4: visual verification

### Task 13: screenshots for Eoin

**Files:**
- Create (scratchpad only, not committed): `<scratchpad>/shots/*.png`

- [ ] **Step 1: Capture**

With claude-in-chrome on `http://127.0.0.1:8092/`, for each size in `390×844`, `370×900`, `820×710`, `1280×800`, and for the NIGHT CITY and FIELD MODE skins (TOOLS › SKIN cycles; the order is Night City, Amber, Phosphor, Synthwave, Field Mode), screenshot with `save_to_disk`:

1. `#chords` grid
2. `#learn/rolls` Forward Roll on gCEA
3. `#learn/song` with a saved song (create one from the Songs hub if none: paste `C G Am F` as the chord list)
4. `#chords/map` key C major
5. `#practice` hub

Name files `<size>-<skin>-<view>.png`.

- [ ] **Step 2: Push to the viewer**

Run from `~/chordware`: `show <scratchpad>/shots/*.png`. If `show` exits non-zero, run `systemctl --user restart comfy-gallery.service` and retry once.

- [ ] **Step 3: Checks that are not eyeballing**

Run: `node tools/check-ui.mjs && node tools/validate-chords.mjs && uv run --project ~/chordware pytest -q tests/test_web.py`
Expected: all clean (the web test covers the tabsmith server still serving `index.html`).

- [ ] **Step 4: Report**

Tell Eoin which screenshots are up, and the one thing to judge in each: digit legibility in the learn tab, finger numbers on the grid, nav fit on the cover screen, 3 × 3 on the unfolded screen. No commit; this task produces no repo change.
