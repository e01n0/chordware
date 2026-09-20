# CHORDWARE //

Cyberpunk-terminal chord chart reference for **banjolele / ukulele / banjo / guitar**.
Single-file PWA — the entire app lives in `index.html` (no build step, no framework).

Six tunings ship with full chord libraries — a hand-curated core (with
hammer-on/pull-off ornament data) plus machine-searched voicings covering all
12 roots × major, minor, 7, m7, maj7, 6, m6, sus2, sus4, add9, dim7 and aug:

- **gCEA** — standard reentrant uke
- **DGBE** — baritone uke (top four guitar strings)
- **DGBD** — open G (banjo); the open strings are a G chord and any straight barre is a major chord
- **DGB♭D** — open Gm / cross-note; the open strings are a G minor chord, any straight barre is a minor chord, and one finger on the B♭ string turns the whole thing major
- **gDGBD** — the 5-string banjo in open G: the four-string open G with the short drone bolted on. The drone's own nut sits at the 5th fret, so it sounds open or from the 6th fret up and nowhere in between — the app knows that everywhere (see *Short strings* below), and the curated core marks it × on the chords where its G would clash (D, A, F, E…) and leaves it open where the G belongs (G, C, Em, Am7, C7…)
- **EADGBE** — standard 6-string guitar: the classic open shapes hand-curated (C, D, E, F-barre, G, A, the minors and 7ths, sus and add9), the rest machine-searched with guitar rules — bass strings may be muted (shown as ×) and the root is preferred in the bass

Everything is string-count-agnostic: diagrams, the fretboard map, key filtering,
auto-ornaments and the voicing search all adapt, so a five-string or alternate
guitar tuning is just another `TUNINGS` + `CHORD_LIBRARY` entry away.

**Short strings.** A tuning can declare a `drone: { s, nut }` — a string bolted
to the neck partway up, like the banjo's 5th. One predicate (`fretExists`) gates
every fret sweep in the app, so the voicing search never writes an unplayable
shape, the fretboard map and halo never plot a note that isn't there, the scale
drills and the tune miner skip it, and a barre below the drone's nut sounds it
open — because that's what your finger actually does. Diagrams draw the missing
stretch dashed with the drone's own nut where it really starts, and the main nut
stops short of it. `tools/validate-chords.mjs` fails the build on any voicing
that reaches past it.

## Files

| File | Purpose |
|---|---|
| `index.html` | The whole app: styles, SVG chord renderer, chord library, PWA manifest (built at runtime) |
| `sw.js` | Tiny cache-first service worker for offline use (browsers refuse inline service workers — this is the only sidecar) |
| `render.yaml` | Render blueprint: deploys as a zero-build static site |
| `tools/generate-voicings.mjs` | Voicing generator: fills any missing root × quality combos per tuning (dry run by default, `--write` to insert) |
| `tools/validate-chords.mjs` | Library linter: checks every voicing spells its named chord, that its fingering is one a hand could actually make, and every ornament's frets, direction and colour-tone label against chord theory |

## Features

- **Barres drawn as barres** — one finger across several strings is one bar, not a row of dots that each claim to be finger 1. A barre is the lowest fretted fret held by two or more strings with nothing ringing open inside its span; everything above stacks on top, which is how a guitar F or an open-G bar up the neck actually works. About 365 of the 866 shipped voicings are barred. The fingerings underneath were rebuilt to match — the old rule (finger = fret offset + 1) handed the same number to every string sharing a fret, which read as one finger in three places wherever that fret wasn't the bar, and it was wrong in two thirds of the machine-searched library. The voicing searches now also reject any shape needing more than four fingers, and `validate-chords.mjs` fails the build on either fault
- **Dots: fingers / notes / degrees** — the diagram dots cycle between the fingering view (which finger goes where) and two theory views (what note, or what degree of the chord). The theory views borrow the fretboard map's colour grammar — root yellow, chord tone cyan, colour tone red and hollow — so the grid and the map teach each other, and hollow-vs-filled carries the same split as the colour so the reading survives a flattened palette. A barre keeps a faint rail under the dots there, since one label can't cover strings that say different things
- **Position inlays** — chord diagrams plot the same 3 · 5 · 7 · 10 · 12 landmarks as the fretboard map, so a shape up the neck lands somewhere your eye already knows
- **Chord grid** — SVG diagrams paged to fit the screen: 2×3 on a portrait phone, 3×2 landscape, growing with the display (4×2 on an iPad on its side, up to 6×3 on a big monitor — the wide layouts also pull the controls into one row and put the detail view's diagram and ornament notes side by side); swipe or arrow-key paging, and rotating/resizing re-fits the grid without losing your place
- **Ornament overlay** — hammer-ons (red filled dots) and pull-offs (red hollow dots, red O for open-string targets) with connecting arcs. The toggle cycles **OFF → dots/arcs → dots/arcs + colour-tone labels** (`H: sus4`, `P: maj7`, …); the fullscreen view always shows labels. Chords without hand-curated ornament data get **auto-derived** ornaments computed from the voicing — a hand-written `ornaments` array always wins
- **Search + category chips** — Major / Minor / 7th / Colour (sus, add9, 6ths, dim7, aug)
- **Key filter** — pick a key and only chords whose voicings sit inside that scale remain (computed from the actual frets, so your own chords are key-filtered automatically)
- **Fretboard map** — the MAP chip opens the whole neck (frets 0–12) with every in-key note plotted and coloured by degree: root (yellow), chord tones 3rd/5th (cyan), colour tones (red outline). A scale selector swaps the key scale for major/minor pentatonic, country (maj pent + ♭3) or blues (min pent + ♭5). Landscape/desktop lie the neck on its side; portrait hangs it nut-up like the chord diagrams (and it redraws live when you rotate)
- **Scale practice** — three drills built into the fretboard map, per key × scale × position box (open, pos 2/5/7 or the full neck). **FOLLOW** walks the scale at a chosen tempo (40–240 BPM), lighting each note and plucking it, up from the lowest root and back down. **HEAR ME** listens on the mic (same pitch detection as the tuner) and only advances the target when you actually play that note — clean-pass times are kept as personal bests. **FIND IT** is a quiz: the map goes dark except the roots and you tap the asked scale degree; wrong answers reveal every correct spot, rounds are 10 prompts, best scores persist. All bests live in localStorage per tuning × key × scale × box
- **Learn** — technique lessons as animated tab (the LEARN chip), split into a ROLLS / SLIDE LICKS toggle. **Rolls**: two dozen right-hand patterns for *every* tuning — the bluegrass rolls (forward, backward, forward-reverse, Foggy Mountain, the fill-in lick roll, index-lead, Osborne's middle-lead, alternating thumb), backup patterns (pinch, pinch & roll, boom-chick), fingerstyle engines (Travis pattern, Cotten picking, classical PIMA climb and PAMI fall, tremolo), 6/8 and 3/4 patterns (folk arpeggio, lullaby, waltz pinch, waltz arpeggio), a 12/8 slow-blues heartbeat, and three clawhammer patterns (bum-ditty, double thumbing, drop-thumb) whose thumb catches land on the 5th-string drone on an instrument that has one — on *every* chord, including the ones whose diagram mutes it, because a × there means "leave it out of the strum", not "the 5th string stopped working", and the g rubbing against a D or an F is the old-time sound rather than a mistake. Drop-thumb's *drops* still take the chord's fret on the inside string; only the catches are the drone. On a reentrant uke the high g does the same job and on a guitar the thumb takes the bass, so those tunings are unchanged. Patterns name strings by role ("1st/2nd/3rd from the top", `5|x` for the 5th-string drone with the role to use instead where there isn't one, bass, alternate bass) rather than absolute index, so the same roll lands on a 4-string uke and a 6-string guitar — the bass roles follow the held chord past its muted strings, which is what turns the alternating-thumb patterns into real Travis picking on guitar, and on a 5-string banjo the thumb roles land on the drone by themselves (Foggy Mountain finally rolls 2-1-**5**-1 instead of borrowing the 3rd string; on a chord that mutes the drone it falls back to the 3rd exactly as a picker would). A roll is string order + timing, so pick any chord from the library and the tab's frets follow what you're holding, with T/I/M/R/F finger badges (F = frail) coloured by picking finger — thumb in the accent colour, since the thumb is what every pattern is built around. Above the tab each roll also carries its **canonical written form** — `STRINGS 2-1-5-1-2-1-5-1 · FINGERS I-M-T-M-I-M-T-M` — because that sequence *is* the roll: the frets under it belong to whichever chord you're holding, and the string-and-finger line is the part worth memorising. Notes struck together (a brush, a pinch) join with `+`. The bar is counted out under the tab the way you'd count it aloud — `1 & 2 & 3 & 4 &`, or `1 & a 2 & a` in the 6/8 and 12/8 lessons — so the offbeats where the clawhammer "ditty" lives are labelled instead of blank. Clawhammer brushes are bracketed, marking the simultaneous notes as one stroke rather than three picks, and clawhammer tab follows its own convention for the thumb: **it's assumed to be on the 5th string, and a T marks only a *drop* to another string** — so in Drop-Thumb the drops are the only T's on the page, which is the entire lesson. Rolls keep their full T/I/M fingering, and necks without a 5th string keep every T. **Slide licks**: twelve per tuning (thirteen on the 5-string), headed by three progression lessons that stitch the licks into real changes with chord names riding over the tab — a 2-bar question-and-answer, the last four bars of the 12-bar, and a full 12-bar slide blues (the tab scrolls through the whole form, one bar in the window) — followed by nine authored blues phrases per tuning — C blues on gCEA, G blues on DGBD, DGB♭D and gDGBD (the banjo inherits the four-string's vocabulary, every string one index across, and adds a tenth of its own — the Drone Roll-Off, where the open g answers every melody note), and open-position E blues on DGBE and guitar: the ♭3 slide, the major-minor rub (Skip James' cross-note rub on DGB♭D), a double-stop slide into the IV, the V–IV ending fall, the ♭5 wobble, a boogie shuffle bass, the down-home run (the full blues scale falling home), a train-whistle fall, and the turnaround walk-down — slides drawn as connected fret pairs and sounded as chromatic re-attack runs. Playback loops at 40–240 BPM with the tab scrolling continuously past a fixed playhead, each note lighting as it sounds (reduced-motion users get a static strip with a sweeping playhead instead); SND toggles between hearing the pattern and a bare metronome tick to play over
- **Halo view** — every chord's fullscreen view has a HALO toggle: the fretboard shrunk to the five frets under your hand, showing the held shape (ringed) plus every in-reach melody note around it, coloured by degree from the chord root in the map's grammar (root yellow, chord tones cyan, colour tones red outline). The scale follows the chord's quality — natural minor under minor chords, mixolydian under plain 7ths, major elsewhere — with the voicing's own tones always merged in. Tap any dot to hear it. The whole neck is a lot to look at; the halo is the part your hand can actually reach. **FIND IT** beside the halo toggle turns it into a quiz: the dots go dark (roots and the shape's rings stay as anchors), you tap the asked degree, ten prompts a round, best scores kept per tuning × chord
- **Tune miner** — the MINE chip is a chord-melody trainer built on the halo: pluck a melody out of chord shapes, one lit note at a time. Built-in tunes (Twinkle Twinkle, Ode to Joy, Row Your Boat, Happy Birthday) are authored as roman-numeral chords + scale degrees and *mined* onto whatever tuning you're in — chords resolve in the tuning's home key, the tonic octave that lands the most notes wins, and each note is placed on the string/fret nearest the hand inside the held shape's window. Three modes: **TAP IT** advances when you tap the right dot (mined notes keep their glow, so the vein you've dug through the shape stays visible), **HEAR ME** listens on the mic and only advances when you actually play the note, and **▶ LISTEN** plays the whole arrangement — melody over soft strums — looping at 40–240 BPM. Clean-pass times persist per tuning × tune × mode
- **ABC paste** — the miner's ABC button takes a pasted ABC tune (thesession.org, abcnotation.com…): a single-voice reader handles `T:`/`L:`/`K:` headers, modal keys (Em, Ador, Dmix…), accidentals to the bar line, octave marks, durations and `"G"`-style chord annotations — the chords become the halos the tune is mined onto (no chords → the key's home chord), the melody is octave-folded toward the instrument and placed note by note, and the result lands as a saved song, instantly drillable and re-mineable in any tuning
- **Melody editor** — any saved song can carry its own melody: the MELODY button in the song editor steps through the song's chords and you tap the tune onto each chord's halo (undo/clear per chord, ◄ ► or arrow keys to move). Melodies are stored per tuning, ride along in song export/import, and appear under MY SONGS in the MINE list — so any song you know becomes a tune-miner drill
- **Tuning everywhere** — the tuning picker lives in every overlay (map, styles, learn, mine, tuner) as well as the header, all kept in sync, and the choice persists across visits — open-G players land straight back in open G
- **Tuning forge** — the picker's **+ CUSTOM TUNING…** entry opens an in-app tuning creator: name it, pick each open string's note (3–8 strings, reentrant welcome — a string higher than its neighbour gets the lowercase label automatically), and FORGE machine-searches a complete chord library client-side — all 12 roots × the same twelve qualities as the built-ins, same search rules and scoring as `tools/generate-voicings.mjs`. The tuning and its library persist in localStorage (the library is cached, re-forged only if the strings change) and every feature — diagrams, ornaments, alternate voicings, the map, drills, rolls, the miner, the tuner — treats it as just another tuning. DADGAD is thirty seconds away
- **Slide barres** — in an open tuning a straight bar *is* a chord, so the MAP and STYLES overlays add a barre strip for any tuning whose open strings spell a triad (open G, cross-note Gm, forged open tunings…): every fret 0–12 named with its barre chord, the picked key's I / IV / V bars highlighted (in open G, key G: OPEN & 12 · 5 · 7) and the ♭III / ♭VII passing bars slide players lean on marked in red. Tap any fret to hear the bar. Cross-note gives the same strip in minors — i / iv / v
- **Styles** — the STYLES chip is a genre primer: pick blues / country / folk and a key, get the genre's scale drawn on the neck plus its standard progressions (12-bar and quick-change blues, minor blues, country standard/ballad/waltz, outlaw, campfire, 50s, Andalusian, Wagon Wheel…) resolved to real chords in that key, with roman-numeral degrees shown. One tap loads the whole form into the grid or straight into performance mode
- **Songs with lyrics** — **+ SONG** opens a paste-first song editor: **paste a song straight from a tab/chord site** (a 📋 Paste button reads the clipboard in one tap) — chord lines sitting above the lyrics are auto-converted to inline `[Am]` tags (each chord lands on the syllable its column pointed at), `[Verse]`/`[Chorus]` headers become section labels, the chord list fills itself in from the tags, and slash chords like `G/B` fall back to their root's diagram. Prefer typing? A space-separated chord list (`Am F C G`) or hand-tagged lyrics work too. Everything persists in localStorage; legacy chord-list-only songs still load
- **Performance mode** — ▶ goes fullscreen for playing live: current chord huge with its diagram, next chord on deck, and if the lyrics carry `[Chord]` tags the words scroll with you, highlighting the active change. Advance by tapping the chord, arrow keys, space or PageDown — so Bluetooth page-turner pedals just work. Keeps the screen awake (Wake Lock) while you play
- **Fullscreen detail view** — tap any card for a large diagram and prose descriptions of every ornament, plus a **voicing pager**: up to two alternate shapes per chord, machine-searched on the spot at positions at least two frets from the shapes already shown (◄ ► buttons, arrow keys or swipe; alternates get auto-derived ornaments)
- **Colour schemes** — the SKIN button cycles Night City, Amber Term, Phosphor, Synthwave and Field Mode (high-contrast light, for playing in the sun — the default). Pure CSS-variable swaps — even the SVG diagrams re-theme — and the choice persists
- **Sound** — tap any chord's fullscreen diagram (or switch voicings) to hear it: Karplus–Strong plucked-string synthesis, no samples, works offline. Notes on the fretboard map are tappable too, and performance mode strums each change (♫ toggles it)
- **Auto-advance** — performance mode can drive itself: set a tempo (40–240 BPM) and AUTO steps one chord every four beats with a visual pulse
- **Transpose** — T± in performance mode shifts the whole song (chord list, lyric tags, diagrams) by semitones, respelled to match the chord DB
- **Tuner** — the TUNER chip listens on the mic (autocorrelation pitch detection, all client-side) and shows note, cents needle, and the nearest string of the current tuning
- **Set lists** — build named, ordered sets of saved songs; performance mode plays through the whole set, rolling from one song into the next
- **Backup** — export every song + set list as one JSON file and import it on any device (merge, imported entries win)
- **ChordPro** — the song editor's IMPORT button also takes `.pro`/`.chopro`/`.txt` files: `{title}` names the song, section directives become `[Verse]`/`[Chorus]` labels, `{comment}`s stay, metadata is dropped, and inline `[Am]` chords are already chordware's native format — chord-lines-above-lyrics text files convert too. **.pro ↓** exports the open song back out as ChordPro for every other songbook app
- **Print** — a black-on-white print sheet for any song: used-chord diagrams plus lyrics with boxed chord tags
- **Left-handed mode** — LH mirrors every diagram and the fretboard map (labels move with their strings; persisted)
- **5th string, shown or hidden** — printed banjo charts leave the 5th string out, since it's open on nearly every chord. CHORDWARE shows it by default, because the × / open mark carries information a four-string chart throws away — but the **5TH** button (which only appears on a tuning that has a drone) drops it from chord diagrams for players who'd rather read the familiar four-string shape. The map, halo, tab and rolls always show it
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
