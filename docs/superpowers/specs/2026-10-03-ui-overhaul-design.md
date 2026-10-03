# CHORDWARE UI overhaul: readability + discoverability

Date: 2026-10-03. Approach A (in-place, single file kept). Visual identity
(skins, Rajdhani + Share Tech Mono, scanlines) is kept; this pass fixes what
is hard to read and makes every feature reachable by name.

## Problems

- Diagram and tab labels are 9–11px thin mono inside small circles; in the
  learn tab the ring and digit share a colour and the SVG scales down to fit.
- `--dim` runs ~3:1 against the backgrounds on every skin; UI text is
  mostly 11–13px mono.
- 25-odd features reached through 5 chips, 4 header micro-buttons, a dropdown
  entry (forge), and toggles inside other overlays (halo quiz, scale drills,
  ABC, melody editor, set lists, from-audio). No back-button support on phone.

## 1. Navigation and hubs

Persistent `<nav>` with five entries: CHORDS · SONGS · PRACTICE · LEARN ·
TOOLS. Below 1100px: bottom tab bar, 56px + safe-area, text labels only
(Rajdhani caps, `aria-current` on the active hub). At ≥1100px: left rail; the
content column shifts right. Tuning picker stays in the header on every hub.
The chip row keeps only the chord-category chips (ALL/MAJOR/MINOR/7TH/COLOUR).

| Hub | Contents |
|---|---|
| Chords | Grid as now: search, category chips, key filter, Dots and Ornaments toggles. A visible GRID / MAP view switch replaces the MAP chip. |
| Songs | A list (not a `<select>`): songs and set lists as rows showing chord count, tuning, a ▶ perform button. Top actions: + SONG, FROM AUDIO, ABC IMPORT, EXPORT / IMPORT. Row tap opens the existing song editor; the editor's MELODY button gets a one-line blurb. |
| Practice | Card list of every drill with a one-line blurb and current best: FOLLOW, HEAR ME, FIND IT (scale, on the map); FIND IT (halo, on a chord); TAP IT, HEAR ME, LISTEN (tune miner). Each card opens the existing feature with that mode pre-selected. |
| Learn | ROLLS, SLIDE LICKS, SONG AS TAB, STYLES (moved here from the chip row). |
| Tools | TUNER, TUNING FORGE, SKIN, LEFT-HANDED, 5TH STRING, KEEP AWAKE, SYNC status. Each is a full-width labelled row with its blurb; the header micro-buttons are removed. |

Hubs are plain views switched by the nav; existing overlays stay
`role="dialog"` and keep their open/close code. Practice and Tools are the only
new screens; they are card lists only.

### Hash routing

Every hub and overlay sets `location.hash` (`#chords`, `#practice`,
`#practice/findit`, `#learn/rolls`, `#tools/tuner`, …). One `hashchange`
listener maps a hash to "show hub" or "open overlay with mode". Closing an
overlay calls `history.back()`. Unknown or empty hash = `#chords`. Deep links
and the phone back gesture come from this. Target: ~20 lines plus the route
table.

## 2. Type, colour, targets

Tokens on `:root`:

| Token | Size | Use |
|---|---|---|
| `--fs-s` | 14px | Floor for anything read: legends, blurbs, counts, bests, options |
| `--fs-m` | 16px | Buttons, chips, inputs, body (16px avoids iOS focus zoom) |
| `--fs-l` | 20px | Section and hub headings |
| `--fs-xl` | existing clamps | Page and overlay titles, unchanged |

12px remains only for the BUILD line. Mono for data readouts (BPM, string
sequence lines, chord names); Rajdhani for labels and buttons, never below
weight 600 at 14–16px.

Contrast: `--dim` retuned per skin to ≥4.5:1 against both `--bg` and
`--panel`. `--line2` is never used as a text fill. The paper skin's
`--yellow` (4.26:1 today) is darkened to pass too. `tools/check-ui.mjs`
parses the five skin blocks from `index.html` and exits non-zero if
`--text`, `--dim`, `--yellow`, `--cyan` or `--red` fall under 4.5:1 against
`--bg`, `--bg2` or `--panel`; it also checks that every route in the hash
router's table names an element that exists in the markup. Runs alongside
`validate-chords.mjs`.

Targets: every button, chip, select and pager control has a 44px minimum hit
box. `:focus-visible` outline 2px in `--yellow`. `prefers-reduced-motion`
also disables the title glitch and scanline sweep.

Not changed: the five palettes beyond `--dim`, no new fonts, no auto
light/dark (SKIN already covers it).

## 3. SVG pass

### Learn tab (`renderLessonTab`)

- No rings. Each note is a panel-coloured rounded-rect knockout (no stroke)
  sized to the digit, with the fret digit in `--text`, bold, 16 units.
- Finger letters above the note: 13 bold, colours unchanged (T yellow,
  I cyan, M/F red, R dim).
- Lit note (`.lev.lit`): knockout fills `--yellow`, digit `--ink`. Playhead
  unchanged.
- Mute × 15, count labels 14, slide from-fret 13 in `--dim`.
- No shrinking: bars per row are derived from the panel width at a minimum
  step of 48 CSS px (`perRow = max(BAR, floor((cw - X0) / 48 / BAR) * BAR)`,
  capped at the lesson length). The SVG renders 1:1 (`width` set from the
  computed `W`, no `width:100%` downscale); rows wrap instead. A 16-slot roll
  on a 390px phone wraps. When a whole bar does not fit at 48px/step the row
  breaks at beat pairs instead (an 8-slot bar on a 390px phone is two rows
  of 4). The tab never scrolls sideways.

### Chord diagrams (grid cards and modal)

- Finger digits 10.5 → 12 bold; dot radius 8.5 → 9.5.
- Theory faces (R, ♭3, 5…) 9 → 11 bold.
- Open-string ring stroke 1.6 → 2; × 13 → 15 bold.
- Barre label 11 → 12 bold.
- Colour grammar and hollow/filled split unchanged.

### Map and halo

- Dot labels 10.5–11 → 13 bold; radii +1.
- Legends use `--fs-s`.

## 4. Galaxy Z Fold layouts

Two postures, no user toggle, both driven by viewport size:

- Cover screen (~370 CSS px wide, tall): bottom nav with five labels fits
  at 14px Rajdhani caps; the grid stays two across; learn tab wraps rolls
  (section 3) instead of shrinking.
- Unfolded inner screen (~820 × 710 CSS px, near-square): `gridLayout()`
  treats a near-square viewport (`w / h` between 0.85 and 1.25) with
  `w >= 760` as 3 columns × 3 rows instead of the landscape 3 × 2; the nav is
  the bottom bar (below the 1100px rail breakpoint). The left rail is not
  used on the inner screen.

The half-folded tabletop split (Device Posture / Viewport Segments) is out of
scope for this pass.

## Verification

- `node tools/check-contrast.mjs` and `node tools/validate-chords.mjs` pass.
- Screenshots of grid, learn tab (Forward Roll, and a SONG lesson), map and
  the Practice hub at 390px and 1280px on the dark and paper skins, pushed to
  the viewer with `show`, judged by Eoin.
- Phone back gesture closes an overlay; a pasted `#practice/findit` link opens
  the map with the quiz on.

## Out of scope

File split, router rewrite, new palettes or fonts, new features.
