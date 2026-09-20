"""Pipeline runner (shared by CLI and web) and the `tabsmith` command."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .arrange import STYLES, arrange, check_invariants
from .ingest import ingest
from .leadsheet import Chord, Grid, LeadSheet, MelodyNote, notes_to_leadsheet, track_table
from .render import ascii_tab, render_audio, render_lilypond, slugify, write_midi
from .transcribe import transcribe


@dataclass
class Options:
    model: str = "large"
    separate: str = "auto"
    refine: bool = False
    key: str | None = None
    capo: int | None = None
    melody_track: str | None = None
    bpm: float | None = None
    meter: int | None = None


def run_pipeline(src: str, instrument: str, style: str, outdir: Path, opts: Options = Options(),
                 progress=lambda stage, msg: None) -> dict[str, Path]:
    if style not in STYLES.get(instrument, ()):
        raise ValueError(f"{instrument} styles are {STYLES.get(instrument)}, not {style!r}")
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    ing = ingest(src, outdir)
    if ing.sheet is not None:
        sheet = ing.sheet
    else:
        if ing.raw is not None:
            notes, grid = ing.raw
        else:
            progress("transcribe", f"transcribing {ing.audio.name} with MuScriptor {opts.model}")
            notes, grid = transcribe(ing.audio, outdir, model_size=opts.model, separate=opts.separate,
                                     progress=lambda m: progress("transcribe", m))
        if opts.bpm:
            grid = Grid(opts.bpm, grid.beats_per_bar, grid.first_downbeat, None)
        progress("leadsheet", "tracks: " + ", ".join(f"{n}({c})" for n, c, _ in track_table(notes)))
        sheet = notes_to_leadsheet(notes, grid, title=ing.title, source=src, instrument=instrument,
                                   melody_track=opts.melody_track, key=opts.key, capo=opts.capo, meter=opts.meter)
    sheet.save(outdir / "leadsheet.json")
    progress("leadsheet", f"key {sheet.key} {sheet.mode}, capo {sheet.capo}, {sheet.bars} bars at {sheet.tempo} bpm")
    progress("arrange", f"{instrument}/{style}")
    arr = arrange(sheet, instrument, style)
    if opts.refine:
        from .refine import apply_refinement, refine
        progress("refine", "asking the local LLM for section labels, rolls and ornaments")
        ref = refine(sheet, ascii_tab(arr), instrument, style)
        if ref is not None:
            arr = apply_refinement(arr, ref)
            arr.sheet.save(outdir / "leadsheet.json")
            progress("refine", ref.notes or "applied")
    check_invariants(arr)
    slug = f"{slugify(sheet.title)}-{instrument}-{style}"
    progress("render", "ASCII, LilyPond, MIDI, audio")
    out = {"leadsheet": outdir / "leadsheet.json", "txt": outdir / f"{slug}.txt",
           "mid": outdir / f"{slug}.mid", "mp3": outdir / f"{slug}.mp3", "ly": outdir / f"{slug}.ly"}
    out["txt"].write_text(ascii_tab(arr))
    write_midi(arr, out["mid"])
    out["pdf"], out["png"] = render_lilypond(arr, outdir, slug)
    render_audio(out["mid"], out["mp3"])
    progress("done", str(outdir))
    return out


def _show(paths: list[Path]) -> None:
    if shutil.which("show"):
        subprocess.run(["show", *map(str, paths)], check=False)


def check(args) -> int:
    """End to end on a synthetic 4-bar G C D G tune rendered with fluidsynth."""
    out = Path(args.outdir or "out/check")
    out.mkdir(parents=True, exist_ok=True)
    melody = [MelodyNote(i, 1, p) for i, p in
              enumerate([67, 69, 71, 72, 74, 76, 74, 72, 71, 69, 67, 66, 67, 71, 74, 79])]
    sheet = LeadSheet("Check", "synthetic", 120, (4, 4), "G", "major", 0, 4, melody,
                      [Chord(0, 0, "G"), Chord(1, 0, "C"), Chord(2, 0, "D"), Chord(3, 0, "G")], [])
    write_midi(arrange(sheet, "guitar", "travis"), out / "check.mid")
    render_audio(out / "check.mid", out / "check.mp3")
    res = run_pipeline(str(out / "check.mp3"), "banjo", "scruggs", out, Options(model=args.model, separate="off"),
                       progress=lambda s, m: print(f"[{s}] {m}"))
    got = [c.name for c in LeadSheet.load(res["leadsheet"]).chords]
    print("chords:", got)
    ok = got[:1] == ["G"] and "C" in got and "D" in got
    print("CHECK", "OK" if ok else "FAILED (expected G, C, D, G)")
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(prog="tabsmith", description="Song in, banjo/guitar arrangement out.")
    ap.add_argument("input", nargs="?", help="audio file, URL, .mid/.musicxml, or leadsheet.json")
    ap.add_argument("--instrument", "-i", choices=list(STYLES), default="banjo")
    ap.add_argument("--style", "-s", default=None, help="scruggs|clawhammer (banjo), travis|flatpick (guitar)")
    ap.add_argument("-o", "--outdir", default=None)
    ap.add_argument("--model", choices=["small", "medium", "large"], default="large")
    ap.add_argument("--separate", choices=["auto", "on", "off"], default="auto")
    ap.add_argument("--refine", action="store_true", help="local LLM pass for sections, rolls and ornaments")
    ap.add_argument("--key")
    ap.add_argument("--capo", type=int)
    ap.add_argument("--melody-track")
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--meter", type=int, choices=[3, 4])
    ap.add_argument("--list-tracks", action="store_true", help="transcribe only and print the track table")
    ap.add_argument("--check", action="store_true", help="end-to-end self test on a synthetic tune")
    a = ap.parse_args()
    if a.check:
        sys.exit(check(a))
    if not a.input:
        ap.error("input required")
    style = a.style or STYLES[a.instrument][0]
    default_slug = "url-" + str(int(time.time())) if a.input.startswith("http") else slugify(Path(a.input).stem)
    outdir = Path(a.outdir) if a.outdir else Path("out") / default_slug
    opts = Options(a.model, a.separate, a.refine, a.key, a.capo, a.melody_track, a.bpm, a.meter)
    if a.list_tracks:
        ing = ingest(a.input, outdir)
        notes, grid = ing.raw if ing.raw else transcribe(ing.audio, outdir, model_size=a.model, separate=a.separate)
        for name, count, mean in track_table(notes):
            print(f"{name:28s} {count:6d} notes  mean pitch {mean:5.1f}")
        return
    t0 = time.time()
    try:
        out = run_pipeline(a.input, a.instrument, style, outdir, opts,
                           progress=lambda s, m: print(f"[{s} {time.time() - t0:5.1f}s] {m}", file=sys.stderr))
    except (ValueError, FileNotFoundError, RuntimeError, AssertionError) as e:
        sys.exit(f"tabsmith: {e}")
    print(out["txt"].read_text())
    for k in ("pdf", "txt", "mid", "mp3", "leadsheet"):
        print(f"{k:9s} {out[k]}")
    _show([out["pdf"], out["mp3"]])
