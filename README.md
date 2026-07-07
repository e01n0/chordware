# CHORDWARE //

Cyberpunk-terminal chord chart reference for **banjolele / ukulele in reentrant gCEA**.
Single-file PWA — the entire app lives in `index.html` (no build step, no framework).

## Files

| File | Purpose |
|---|---|
| `index.html` | The whole app: styles, SVG chord renderer, chord library, PWA manifest (built at runtime) |
| `sw.js` | Tiny cache-first service worker for offline use (browsers refuse inline service workers — this is the only sidecar) |
| `render.yaml` | Render blueprint: deploys as a zero-build static site |

## Features

- **Chord grid** — 6 SVG diagrams per page (2×3 portrait, 3×2 landscape/desktop), swipe or arrow-key paging
- **Ornament overlay** — hammer-ons (red filled dots) and pull-offs (red hollow dots, red O for open-string targets) with connecting arcs. The toggle cycles **OFF → dots/arcs → dots/arcs + colour-tone labels** (`H: sus4`, `P: maj7`, …); the fullscreen view always shows labels
- **Search + category chips** — Major / Minor / 7th / Dark Folk
- **Key filter** — pick a key and only chords whose voicings sit inside that scale remain (computed from the actual frets, so your own chords are key-filtered automatically)
- **Songs** — type a space-separated chord list (`Am F C G`) to see exactly those chords in order, then **SAVE** it as a named song (persisted in localStorage); reload it any time from the SONG selector
- **Fullscreen detail view** — tap any card for a large diagram and prose descriptions of every ornament
- **Offline PWA** — installable, works with no connection once loaded

## Extending the chord library

Everything is data-driven. In `index.html`, edit `CHORD_LIBRARY.gCEA`:

```js
{ name:"Csus4", full:"C suspended 4", frets:[0,0,1,3], fingers:[0,0,1,3],
  cats:["darkfolk"],
  ornaments:[
    // s: string index (0=g … 3=A), from: fret in the shape, to: target fret (0 = open)
    { s:2, from:1, to:0, type:"pull", label:"maj3" },
  ]},
```

## Alternate tunings

Add an entry to `TUNINGS` (string names + semitone offsets from C) and a matching
key in `CHORD_LIBRARY` — the tuning picker, string labels, and ornament note-naming
all follow automatically:

```js
DGBE: { label:"DGBE · baritone", strings:["D","G","B","E"], pitches:[2,7,11,4] },
```

## Deploy on Render

Push this repo and create a **Blueprint** instance from `render.yaml`, or create a
Static Site by hand (publish directory `.`, no build command). Any static host works.
