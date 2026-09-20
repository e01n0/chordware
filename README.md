# tabsmith

Song in, banjo or guitar arrangement out. Everything runs locally on this box (RTX 5090).

Input: an audio file, a YouTube (or any yt-dlp) URL, a MIDI or MusicXML file, or a `leadsheet.json` from an earlier run.
Output, in one directory: `leadsheet.json`, engraved tab (`.pdf`, `.png`), ASCII tab (`.txt`), `.mid`, `.mp3`, and the LilyPond source.

Styles: banjo `scruggs` (three-finger rolls) and `clawhammer`; guitar `travis` (alternating-bass fingerstyle) and `flatpick` (melody with chord names).

## How it works

1. **Transcribe**: MuScriptor (Kyutai/Mirelo, 1.4B) turns the full mix into per-instrument notes. Its built-in Beat This! tracker gives the bar grid. With a vocal present, `audio-separator` (BS-RoFormer) isolates the voice and the melody is re-transcribed from the clean stem.
2. **Lead sheet**: melody by skyline on the vocal or lead track, chords per bar by pitch-class template matching anchored on the bass, key by Krumhansl, nearest instrument-friendly key with a capo suggestion. Saved as `leadsheet.json`.
3. **Arrange**: a fret mapper (cheapest string/fret path, banjo fifth string modelled as a thumb drone) plus one pattern engine per style. Melody notes are placed first, fill notes second. Invariants are checked before rendering: every melody note present, every fret playable, no string collisions, hand span within limits.
4. **Render**: LilyPond for the PDF/PNG, mido for MIDI, FluidSynth plus ffmpeg for the mp3.
5. **Refine** (optional, `--refine`): qwen3.6:27b via Ollama labels sections, picks a roll per section and suggests hammer-ons, pull-offs and slides. The engine validates every suggestion against the fretboard and drops the unplayable ones. The LLM never writes tab.

## Install

```bash
sudo apt install lilypond fluidsynth fluid-soundfont-gm ffmpeg
cd ~/tabsmith && uv sync
```

MuScriptor weights are gated (CC BY-NC 4.0, personal use). Accept the license once on the HuggingFace model pages, then `uvx hf auth login` or export `HF_TOKEN`. Weights download on first use (about 3 GB for `large`).

## CLI

```bash
uv run tabsmith song.mp3 -i banjo -s scruggs
uv run tabsmith "https://www.youtube.com/watch?v=..." -i guitar -s travis
uv run tabsmith tune.musicxml -i banjo -s clawhammer
uv run tabsmith out/song/leadsheet.json -i guitar -s flatpick     # re-arrange after editing chords by hand
uv run tabsmith song.mp3 --list-tracks                            # see what MuScriptor heard, pick --melody-track
uv run tabsmith --check                                           # end-to-end self test on a synthetic tune
```

Options: `--model small|medium|large`, `--separate auto|on|off`, `--refine`, `--key G`, `--capo 2`, `--melody-track voice`, `--bpm`, `--meter 3|4`, `-o DIR`.
Output defaults to `out/<slug>/`. Transcription is cached per input file in the output directory, so re-arranging is instant.

## Web app

- Local: http://127.0.0.1:8092 (user unit `tabsmith.service`).
- Tailnet: https://mrfantastic.tail969b8f.ts.net:10008 (installable as a PWA; Android share sheet accepts YouTube links).
- Upload or paste a URL, watch the job states, get the tab, audio and downloads. The chord row under a result is editable: change chords, pick another instrument or style, and re-arrange without re-transcribing.
- One worker, one GPU. Jobs live under `~/tabsmith/jobs/<id>/`. Before touching the GPU the worker waits while ComfyUI's queue is busy.

## Gotchas

- ComfyUI keeps about 24 GB of the 32 GB resident. MuScriptor `large` therefore loads on the CPU in bf16 and is moved over (2.8 GB). Separation and transcription never share the GPU at once.
- A tune MuScriptor hears in 2/4 is written as 4/4 (cut-time folk). Override with `--meter`.
- Rubato recordings quantise badly. `--bpm` forces a constant grid.
- Sevenths are penalised on purpose: a chord only becomes a 7th when the seventh carries real weight in the bar. Folk bias.
- The refine pass needs Ollama with `qwen3.6:27b` (env `TABSMITH_LLM` to change). With ComfyUI resident the model partly runs on CPU, about 30 to 45 s per call.
