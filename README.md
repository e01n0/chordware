# CHORDWARE //

Cyberpunk-terminal chord chart reference for **banjolele / ukulele / guitar**.
Single-file PWA — the entire app lives in `index.html` (no build step, no framework).

Four tunings ship with full chord libraries — a hand-curated core (with
hammer-on/pull-off ornament data) plus machine-searched voicings covering all
12 roots × major, minor, 7, m7, maj7, 6, m6, sus2, sus4, add9, dim7 and aug:

- **gCEA** — standard reentrant uke
- **DGBE** — baritone uke (top four guitar strings)
- **DGBD** — open G (banjo); the open strings are a G chord and any straight barre is a major chord
- **EADGBE** — standard 6-string guitar: the classic open shapes hand-curated (C, D, E, F-barre, G, A, the minors and 7ths, sus and add9), the rest machine-searched with guitar rules — bass strings may be muted (shown as ×) and the root is preferred in the bass

Everything is string-count-agnostic: diagrams, the fretboard map, key filtering,
auto-ornaments and the voicing search all adapt, so a five-string or alternate
guitar tuning is just another `TUNINGS` + `CHORD_LIBRARY` entry away.

## Files

| File | Purpose |
|---|---|
| `index.html` | The whole app: styles, SVG chord renderer, chord library, PWA manifest (built at runtime) |
| `sw.js` | Tiny cache-first service worker for offline use (browsers refuse inline service workers — this is the only sidecar) |
| `render.yaml` | Render blueprint: deploys as a zero-build static site |
| `tools/generate-voicings.mjs` | Voicing generator: fills any missing root × quality combos per tuning (dry run by default, `--write` to insert) |
| `tools/validate-chords.mjs` | Library linter: checks every voicing spells its named chord and every ornament's frets, direction and colour-tone label against chord theory |

## Features

- **Chord grid** — 6 SVG diagrams per page (2×3 portrait, 3×2 landscape/desktop), swipe or arrow-key paging
- **Ornament overlay** — hammer-ons (red filled dots) and pull-offs (red hollow dots, red O for open-string targets) with connecting arcs. The toggle cycles **OFF → dots/arcs → dots/arcs + colour-tone labels** (`H: sus4`, `P: maj7`, …); the fullscreen view always shows labels. Chords without hand-curated ornament data get **auto-derived** ornaments computed from the voicing — a hand-written `ornaments` array always wins
- **Search + category chips** — Major / Minor / 7th / Colour (sus, add9, 6ths, dim7, aug)
- **Key filter** — pick a key and only chords whose voicings sit inside that scale remain (computed from the actual frets, so your own chords are key-filtered automatically)
- **Fretboard map** — the MAP chip opens the whole neck (frets 0–12) with every in-key note plotted and coloured by degree: root (yellow), chord tones 3rd/5th (cyan), colour tones (red outline). A scale selector swaps the key scale for major/minor pentatonic, country (maj pent + ♭3) or blues (min pent + ♭5). Landscape/desktop lie the neck on its side; portrait hangs it nut-up like the chord diagrams (and it redraws live when you rotate)
- **Styles** — the STYLES chip is a genre primer: pick blues / country / folk and a key, get the genre's scale drawn on the neck plus its standard progressions (12-bar and quick-change blues, minor blues, country standard/ballad/waltz, outlaw, campfire, 50s, Andalusian, Wagon Wheel…) resolved to real chords in that key, with roman-numeral degrees shown. One tap loads the whole form into the grid or straight into performance mode
- **Songs with lyrics** — SAVE opens a song editor: a chord list (`Am F C G`) plus optional lyrics with inline `[Am]` chord tags. **Paste a song straight from a tab/chord site** — chord lines sitting above the lyrics are auto-converted to inline tags (each chord lands on the syllable its column pointed at), `[Verse]`/`[Chorus]` headers become section labels, and slash chords like `G/B` fall back to their root's diagram. Everything persists in localStorage; legacy chord-list-only songs still load
- **Performance mode** — ▶ goes fullscreen for playing live: current chord huge with its diagram, next chord on deck, and if the lyrics carry `[Chord]` tags the words scroll with you, highlighting the active change. Advance by tapping the chord, arrow keys, space or PageDown — so Bluetooth page-turner pedals just work. Keeps the screen awake (Wake Lock) while you play
- **Fullscreen detail view** — tap any card for a large diagram and prose descriptions of every ornament, plus a **voicing pager**: up to two alternate shapes per chord, machine-searched on the spot at positions at least two frets from the shapes already shown (◄ ► buttons, arrow keys or swipe; alternates get auto-derived ornaments)
- **Colour schemes** — the SKIN button cycles Night City (default), Amber Term, Phosphor, Synthwave and Field Mode (high-contrast light, for playing in the sun). Pure CSS-variable swaps — even the SVG diagrams re-theme — and the choice persists
- **Sound** — tap any chord's fullscreen diagram (or switch voicings) to hear it: Karplus–Strong plucked-string synthesis, no samples, works offline. Notes on the fretboard map are tappable too, and performance mode strums each change (♫ toggles it)
- **Auto-advance** — performance mode can drive itself: set a tempo (40–240 BPM) and AUTO steps one chord every four beats with a visual pulse
- **Transpose** — T± in performance mode shifts the whole song (chord list, lyric tags, diagrams) by semitones, respelled to match the chord DB
- **Tuner** — the TUNER chip listens on the mic (autocorrelation pitch detection, all client-side) and shows note, cents needle, and the nearest string of the current tuning
- **Set lists** — build named, ordered sets of saved songs; performance mode plays through the whole set, rolling from one song into the next
- **Backup** — export every song + set list as one JSON file and import it on any device (merge, imported entries win)
- **Print** — a black-on-white print sheet for any song: used-chord diagrams plus lyrics with boxed chord tags
- **Left-handed mode** — LH mirrors every diagram and the fretboard map (labels move with their strings; persisted)
- **Animated ornaments** — in the fullscreen view a dot travels each hammer/pull arc, so the move reads at a glance (honours reduced-motion)
- **Offline PWA** — installable, works with no connection once loaded (the tuner and mic are the only features that need permissions)

## Extending the chord library

Everything is data-driven. In `index.html`, edit `CHORD_LIBRARY.gCEA`:

```js
{ name:"Csus4", full:"C suspended 4", frets:[0,0,1,3], fingers:[0,0,1,3],
  cats:["colour"],
  ornaments:[
    // s: string index (0=g … 3=A), from: fret in the shape, to: target fret (0 = open)
    { s:2, from:1, to:0, type:"pull", label:"maj3" },
  ]},
```

Leave `ornaments` empty and the app derives sensible hammer/pull colour tones
automatically. To bulk-add every missing root × quality combo (for a new tuning,
or after adding a quality to the tool's table):

```sh
node tools/generate-voicings.mjs          # dry run — prints what it would add
node tools/generate-voicings.mjs --write  # inserts into index.html
```

After editing the library, lint it — every voicing must spell its named chord
and every ornament label must match the note it lands on:

```sh
node tools/validate-chords.mjs
```

## Alternate tunings

Add an entry to `TUNINGS` (string names + semitone offsets from C) and a matching
key in `CHORD_LIBRARY` — the tuning picker, string labels, key filter, and ornament
note-naming all follow automatically:

```js
aDFsB: { label:"aDF#B · D-tuning", strings:["a","D","F#","B"], pitches:[9,2,6,11] },
```

## Deploy on Render

Push this repo and create a **Blueprint** instance from `render.yaml`. Its build
command stamps the git commit SHA over `__BUILD__` in `index.html` and `sw.js` —
that versions the service-worker cache per deploy (forcing the update cycle and
purging stale copies) and shows as `BUILD://<sha>` at the bottom of the chord
grid, so you can always check which version a device is running.

Any other static host works too — replicate the one-line sed from `render.yaml`,
or don't: the app still updates via its network-first shell, just without the
visible build tag.
