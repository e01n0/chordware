# tabsmith design (2026-09-20)

Feed it a song, get a banjo or guitar arrangement as engraved tab, ASCII tab, MIDI and audio. Everything runs locally on this box (RTX 5090). CLI first, web app + PWA on top of the same pipeline.

## Scope (v1, approved)

Inputs: audio file (mp3/wav/flac/m4a), YouTube/any yt-dlp URL, existing MIDI or MusicXML, or a previously produced `leadsheet.json`.

Instruments and styles:
- banjo, 5-string, open G (gDGBD): `scruggs` (three-finger rolls), `clawhammer` (bum-ditty)
- guitar, standard tuning: `travis` (alternating-bass fingerstyle), `flatpick` (melody line + chord names)

Outputs, all in one output directory: `leadsheet.json`, `<slug>.ly`, `<slug>.pdf`, `<slug>.png` (page 1, for the web UI), `<slug>.txt` (ASCII tab), `<slug>.mid`, `<slug>.mp3`.

Options: `--separate auto|on|off` (stem separation before transcription), `--refine` (local LLM variation/ornament pass), `--key`, `--capo`, `--melody-track`, `--bpm` (override detected tempo), `--meter 3|4` (override detected beats per bar), `--model small|medium|large` (MuScriptor size, default large).

Out of scope: MuseScore (LilyPond renders), training any model, DAW export, mandolin/uke (the fret mapper is tuning-agnostic, so adding one later is a tuning entry plus a style).

## Pipeline

```
ingest -> transcribe -> leadsheet -> arrange -> render
   |                        ^
   +-- MIDI/MusicXML -------+   (skips transcribe)
   +-- leadsheet.json ------+   (skips transcribe + leadsheet)
```

Each stage is a module with one public function; `leadsheet.json` is the contract between the analysis half and the arrangement half. Editing it by hand and re-running `tabsmith leadsheet.json ...` re-arranges without touching the GPU.

### ingest.py
- Audio path: returned as-is.
- URL: `yt-dlp -x --audio-format wav` into the output dir. yt-dlp is a Python dep.
- `.mid/.midi/.musicxml/.xml/.mxl`: parsed with music21 straight to a `LeadSheet` (melody = highest part or the part named melody/vocal/lead; chords from music21's chordify per bar; key from `analyze('key')`).
- `.json`: loaded as a `LeadSheet`.

### transcribe.py
1. Optional separation with `audio-separator` (Mel-Band RoFormer vocals model). `auto` runs it, then keeps the vocal stem as the melody source only if MuScriptor reports a vocal/lead track on the full mix; otherwise the full-mix lead instrument is used. Output: `stems/` dir, cached by input hash.
2. Beat This! (`beat_this.inference.File2Beats`, cuda) on the full mix: beats and downbeats. Time signature inferred from downbeat spacing (3 or 4 beats per bar; others rejected with a clear error and the `--bpm`/`--meter` override). Tempo = median beat interval.
3. MuScriptor (`muscriptor.load_model(size)`) on the full mix, and on the vocal stem when separated. Output: per-instrument note lists (pitch, onset s, offset s, velocity).
4. Notes snapped to a 16th-note grid built from the beats (nearest gridline, notes shorter than a 32nd dropped). Triplet feel is not detected in v1.

GPU house rule: before loading models, poll `http://127.0.0.1:8188/queue`; if ComfyUI is busy, wait and re-poll (30 s) up to a configurable limit, then proceed. The web app surfaces "waiting for GPU" as a job state.

MuScriptor weights need a HuggingFace login and license accept (CC BY-NC 4.0). If no token, the CLI fails fast with the two commands to run.

### leadsheet.py
`LeadSheet` dataclass, JSON-serialisable:

```
{
  "title": "...", "source": "...",
  "tempo": 120.0, "meter": [4, 4], "key": "G", "mode": "major",
  "capo": 0,
  "bars": 32,
  "melody": [ {"t": 0.0, "d": 0.5, "p": 67} ... ],   # t, d in beats from bar 1; p = MIDI pitch
  "chords": [ {"bar": 0, "beat": 0, "name": "G"} ... ],
  "sections": [ {"bar": 0, "label": "A"} ... ]        # optional, filled by --refine
}
```

- Melody track choice: MuScriptor track named vocal/voice/lead/melody if present, else the non-bass, non-drum, non-keyboard track with the most notes in the top register. `--melody-track NAME` overrides; the CLI prints the track list with note counts so the user can pick.
- Melody line: skyline (highest sounding note per grid slot) on the chosen track, then monophonic cleanup (drop notes fully covered by a higher note, merge repeated pitches across a slot when no re-onset).
- Chords: per bar (per half-bar in 4/4 when the pitch-class histogram of the two halves differs enough), duration-weighted pitch-class histogram over all non-drum tracks plus a bonus for the bass track's lowest note as root; template match against major, minor, dominant 7, minor 7. Ties resolved towards the diatonic chord of the detected key.
- Key: music21 Krumhansl on the melody+chords. Transposition: nearest key from the instrument's friendly set (banjo: G, C, D, A; guitar: G, C, D, A, E) via capo (0 to 5) first, transposing only when no capo fits. `--key`/`--capo` override.
- Melody range fit: if the melody spans more than the instrument comfortably plays (banjo: D3 on the open 4th string up to about D5 at fret 12 on the 1st; guitar: E2 to E5), shift by octaves per phrase, never mid-phrase.

### arrange.py
Shared core:
- `Tuning`: list of open-string MIDI pitches low to high plus per-string min fret (banjo 5th string min fret 0 but playable frets are 0 and 5+ only, modelled as an allowed-frets set).
- `ChordShape` library per tuning: name -> fretting (one fret per string, -1 muted). Banjo open G: G, C, D, D7, Em, Am, A, E, F, Bm, plus barre forms up the neck. Guitar: open cowboy chords plus E-shape and A-shape barres.
- `FretMapper.assign(notes, anchor_shape)`: dynamic programming over candidate (string, fret) positions per note, cost = fret span from the anchor shape + hand movement between consecutive notes + string switches + a penalty for high frets, a bonus for open strings. Positions outside the instrument's allowed fret set are not candidates. This is the only place geometry decisions are made.

Style functions all share the signature `arrange(leadsheet, tuning, shapes, opts) -> Arrangement`, where `Arrangement` is a list of `TabNote(t, d, string, fret, technique)` plus chord names per bar and the tuning. Melody notes are placed first, fill notes second, and a fill note is dropped whenever it would collide with a melody note on the same string at the same time.

- `scruggs`: grid of 8ths. For each bar, choose a roll (forward, backward, forward-backward, alternating thumb, foggy mountain) by a fixed rotation per section, with the roll's strings mapped onto the current chord shape. Each melody note replaces the roll note nearest in time on the string that carries the melody pitch under the shape, or the mapper picks the string if the shape cannot. Thumb (T) index (I) middle (M) fingering annotated. Slides 2-3 on the 3rd string and hammer-ons 0-2 on the 4th string added where the melody moves by those intervals (Scruggs licks, hard-coded table).
- `clawhammer`: bum-ditty per beat in 4/4 (quarter, 8th, 8th): bum = melody note (or the shape's highest string if no melody note), ditty = brush of the top three strings then 5th string thumb. Drop-thumb when a melody note falls on the "and": thumb plays it on the 2nd or 3rd string. 3/4: bum-ditty-ditty.
- `travis`: alternating bass on beats (root, fifth, root, third from the chord shape, string 6/5/4), melody on strings 1 to 3 at its own beats, pinch when they coincide, 8th-note fill from the shape on empty off-beats. Thumb/fingers annotated p i m a.
- `flatpick`: melody only through the mapper anchored to the open position, chord names above the staff, crosspicking not attempted.

Invariants (asserted in tests):
1. Every melody note in the lead sheet appears in the arrangement at its time with the same pitch class (octave may shift as a whole phrase).
2. Every fret is in the tuning's allowed set for that string; banjo 5th string only 0 or >= 5.
3. No two notes on the same string at the same time.
4. Fret span within a 16th-note window never exceeds 5 frets (4 on banjo).

### refine.py (`--refine`)
Local LLM pass via Ollama (`qwen3.6:27b`, env `TABSMITH_LLM` to override), HTTP to 127.0.0.1:11434. The model never emits tab. Prompt = lead sheet (chords per bar, melody as note names per bar, key, meter, style) + the list of allowed roll/pattern names + the ASCII tab of the plain arrangement. Required reply: JSON `{"sections":[{"bar":0,"label":"A"}], "pattern_by_section":{"A":"forward","B":"foggy"}, "ornaments":[{"bar":3,"beat":1.5,"kind":"hammer","from":0,"to":2}], "notes":"..."}`. Ollama's JSON mode (`format: json`) is used; a reply that fails to parse or names an unknown pattern is logged and ignored, the plain arrangement stands. Ornaments are re-validated by the fret mapper (same string, frets within the allowed set and within span). The engine then re-arranges with the chosen patterns. Whole pass is best-effort: any Ollama error = warning, not failure.

### render.py
- ASCII: one line per string, top string first, 16th-note columns, bar lines, chord names above, fingering letters below, wrapped at 80 chars. Written to `<slug>.txt` and printed by the CLI.
- LilyPond: `\new TabStaff` with `\set TabStaff.stringTunings = #banjo-open-g-tuning` (or `#guitar-tuning`), `\tabFullNotation`, chord names in a `ChordNames` context above, tempo and key/capo in the header, `\midi {}` block so `lilypond` emits the `.mid` alongside the `.pdf`. Notes are emitted as `<pitch>\<string>` with explicit string numbers so LilyPond never re-fingers. Rendered with `lilypond --png --pdf -o <slug> <slug>.ly`. Techniques: hammer-on/pull-off as slurs, slides as `\glissando`.
- Audio: `fluidsynth -ni <soundfont> <slug>.mid -F <slug>.wav -r 44100` with the GM soundfont from apt (`/usr/share/sounds/sf2/FluidR3_GM.sf2`, program 105 banjo / 25 steel guitar set in the LilyPond `midiInstrument`), then `ffmpeg -i wav -codec:a libmp3lame -q:a 4 slug.mp3`. wav deleted.
- CLI ends by running `show <pdf> <mp3>` (the box's viewer push, ignored if missing) and printing the output paths.

### cli.py
`tabsmith INPUT --instrument banjo|guitar --style scruggs|clawhammer|travis|flatpick [-o DIR] [options]`. Output dir defaults to `./out/<slug>/`. Exit non-zero on: missing HF token, unsupported input, no melody found, LilyPond failure. Every stage logs one line with timing. `tabsmith --list-tracks INPUT` runs only transcription and prints the track table.

## Web app + PWA (web.py + static/)
- FastAPI + uvicorn on 127.0.0.1:8092, user unit `~/.config/systemd/user/tabsmith.service` (`uv run --project ~/tabsmith tabsmith-web`), tailnet: `sudo tailscale serve --bg --https=10008 http://127.0.0.1:8092`. Tailnet-only, no auth of its own (same as every other service on the box).
- Routes: `GET /` (single page), `POST /jobs` (multipart file or `url` field + instrument/style/options) -> `{id}`, `GET /jobs/{id}` (state: queued | waiting_gpu | separating | transcribing | arranging | rendering | done | failed, plus log tail), `GET /jobs/{id}/<file>` (pdf/png/txt/mid/mp3/leadsheet.json), `POST /jobs/{id}/rearrange` (body: edited leadsheet JSON + instrument/style/options) -> new job that skips transcription, `GET /jobs` (recent list), `GET /manifest.webmanifest`, `GET /sw.js`, icons.
- Jobs: in-process queue, one worker thread (single GPU), job dir `~/tabsmith/jobs/<id>/` holding the input and all outputs. Pipeline stages are the same functions the CLI calls; a `progress(stage)` callback updates the state. Restart loses queued jobs, finished ones stay on disk and are listed from the directory.
- Page: upload/URL form with instrument, style, separate, refine, key/capo; job list with live state (2 s polling); result view with the PNG tab (link to PDF), ASCII in `<pre>`, `<audio>` player, and a chord row (one input per bar, prefilled from leadsheet.json) with "re-arrange". Plain HTML/JS in `static/index.html`, no build step. Manifest id `/tabsmith-mrfantastic`, icons generated once with PIL (same as the other PWAs on the box), service worker caches the shell only (never job results).
- Share target: the PWA manifest declares a `share_target` accepting audio files and URLs, so an Android share sheet can send a YouTube link or an mp3 straight to `/share`, which creates a job with defaults (banjo/scruggs) and redirects to it.

## Error handling
- Trust boundary is the web upload: file type checked by extension and ffprobe, size capped at 200 MB, filenames replaced by the job id, URLs handed to yt-dlp only (never a shell).
- Model download failures, GPU busy, Ollama down: each reported as a job/CLI error with the fix in the message. Ollama down with `--refine` is a warning, not a failure.
- Rubato: Beat This! confidence is not exposed, so the heuristic is beat-interval variance; above a threshold the CLI warns "tempo unstable, results may be off, try --bpm".

## Testing
- `tests/test_arrange.py`: hand-written lead sheets (Cripple Creek A part in G, a 3/4 waltz fragment, a melody with out-of-shape notes) through all four styles, asserting the four invariants above plus "every bar has notes".
- `tests/test_leadsheet.py`: synthetic MIDI (chords + melody generated with music21) round-trips to the expected chord names and key.
- `tests/test_render.py`: ASCII output for a two-bar arrangement matches a golden string; LilyPond source compiles (skipped if lilypond missing).
- Web: `tests/test_web.py` with FastAPI TestClient, pipeline monkeypatched to a stub that writes fake outputs, covering job creation, state polling, file serving, rearrange.
- End to end: `tabsmith --check` runs a bundled 8-second synthetic wav (rendered from a known MIDI via fluidsynth at first run) through the full GPU pipeline and asserts the chords come back as G C D G. Not part of the unit suite.

## Layout
```
~/tabsmith/
  pyproject.toml         uv project, python 3.12, deps: muscriptor beat-this audio-separator music21 yt-dlp fastapi uvicorn python-multipart requests pillow
  tabsmith/{__init__,ingest,transcribe,leadsheet,arrange,refine,render,cli,web}.py
  tabsmith/static/{index.html,manifest.webmanifest,sw.js,icon-192.png,icon-512.png}
  tests/
  docs/superpowers/{specs,plans}/
  jobs/                  gitignored
```
Deps are installed into the project venv only (`uv sync`); torch comes with muscriptor. Nothing touches the ComfyUI or system Python.
