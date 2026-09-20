"""ASCII tab, LilyPond engraving, MIDI and audio from an Arrangement."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import mido

from .arrange import GRID, Arrangement

SOUNDFONT = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
PROGRAM = {"banjo": 105, "guitar": 25}
_LY_TUNING = {"banjo-open-g": "banjo-open-g-tuning", "guitar-standard": "guitar-tuning"}
_LABELS = {"banjo": ["d", "B", "G", "D", "g"], "guitar": list("eBGDAE")}


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "untitled"


def ascii_tab(arr: Arrangement, bars_per_line: int = 4) -> str:
    sheet, n = arr.sheet, arr.tuning.n
    slots_per_bar = int(sheet.bpb / GRID)
    cell = 3
    by_slot = {(round(x.t / GRID), x.string): x for x in arr.notes}
    out = []
    for first in range(0, sheet.bars, bars_per_line):
        chord_line, fing = "  ", "  "
        rows = [lab + "|" for lab in _LABELS[arr.instrument]]
        for bar in range(first, min(first + bars_per_line, sheet.bars)):
            for slot in range(slots_per_bar):
                g = bar * slots_per_bar + slot
                t = g * GRID
                change = any(c.bar == bar and abs(c.beat - slot * GRID) < 1e-9 for c in sheet.chords)
                chord_line += (sheet.chord_at(t) if change else "").ljust(cell)
                finger = ""
                for s in range(1, n + 1):
                    x = by_slot.get((g, s))
                    rows[s - 1] += (str(x.fret) + x.tech).ljust(cell, "-") if x else "-" * cell
                    if x and x.finger and not finger:
                        finger = x.finger
                fing += finger.ljust(cell)
            chord_line += " "
            fing += " "
            rows = [r + "|" for r in rows]
        out.append(chord_line.rstrip())
        out.extend(rows)
        out.append(fing.rstrip())
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _ly_pitch(midi: int) -> str:
    names = ["c", "cis", "d", "dis", "e", "f", "fis", "g", "gis", "a", "ais", "b"]
    octave = midi // 12 - 4
    return names[midi % 12] + ("'" * octave if octave > 0 else "," * -octave)


_DUR = {4.0: "1", 3.0: "2.", 2.0: "2", 1.5: "4.", 1.0: "4", 0.75: "8.", 0.5: "8", 0.25: "16"}


def _ly_dur(beats: float) -> list[str]:
    """Split a length in beats into LilyPond durations, largest first."""
    out = []
    for b, d in sorted(_DUR.items(), reverse=True):
        while beats >= b - 1e-9:
            out.append(d)
            beats -= b
    return out or ["16"]


def _ly_root(name: str) -> tuple[str, str]:
    root = name[:2] if len(name) > 1 and name[1] in "#b" else name[:1]
    ly = root[0].lower() + root[1:].replace("#", "is").replace("b", "es")
    return ly, {"": "", "m": ":m", "7": ":7", "m7": ":m7"}[name[len(root):]]


def lilypond_source(arr: Arrangement) -> str:
    sheet, t = arr.sheet, arr.tuning
    groups: dict[int, list] = {}
    for x in arr.notes:
        groups.setdefault(round(x.t / GRID), []).append(x)
    total = int(sheet.bars * sheet.bpb / GRID)
    body: list[str] = []
    g = 0
    slur_open = False
    while g < total:
        nxt = min((k for k in groups if k > g), default=total)
        if g in groups:
            notes = groups[g]
            length = max(1, min(round(min(x.d for x in notes) / GRID), nxt - g))
            inner = " ".join(f"{_ly_pitch(t.pitch(x.string, x.fret))}\\{x.string}" for x in notes)
            durs = _ly_dur(length * GRID)
            chord = f"<{inner}>{durs[0]}" + "".join(f"~ <{inner}>{dd}" for dd in durs[1:])
            tech = next((x.tech for x in notes if x.tech), "")
            if slur_open:
                chord += ")"
                slur_open = False
            if tech in ("h", "p"):
                chord += "("
                slur_open = True
            elif tech == "s":
                chord += "\\glissando"
            body.append(chord)
            g += length
        else:
            body.extend("r" + d for d in _ly_dur((nxt - g) * GRID))
            g = nxt
    if slur_open:
        body[-1] += ")"
    chords = []
    bpb = sheet.bpb
    for i, c in enumerate(sheet.chords):
        start = c.bar * bpb + c.beat
        end = sheet.chords[i + 1] if i + 1 < len(sheet.chords) else None
        stop = (end.bar * bpb + end.beat) if end else sheet.bars * bpb
        root, mod = _ly_root(c.name)
        chords.extend(f"{root}{d}{mod}" for d in _ly_dur(stop - start))
    capo = f" (Capo {sheet.capo})" if sheet.capo else ""
    key, _ = _ly_root(sheet.key)
    banjo = "      tablatureFormat = #fret-number-tablature-format-banjo\n" if arr.instrument == "banjo" else ""
    return f"""\\version "2.24.0"
\\header {{ title = "{sheet.title}" subtitle = "{arr.instrument} / {arr.style}{capo}" tagline = "tabsmith" }}
\\score {{
  <<
    \\new ChordNames {{ \\set chordChanges = ##t \\chordmode {{ {' '.join(chords)} }} }}
    \\new TabStaff \\with {{
      stringTunings = #{_LY_TUNING[t.name]}
{banjo}    }} {{
      \\tabFullNotation
      \\tempo 4 = {int(sheet.tempo)}
      \\key {key} \\{sheet.mode}
      \\time {sheet.meter[0]}/{sheet.meter[1]}
      {' '.join(body)}
    }}
  >>
  \\layout {{ }}
}}
"""


def render_lilypond(arr: Arrangement, outdir: Path, slug: str) -> tuple[Path, Path]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    ly = outdir / f"{slug}.ly"
    ly.write_text(lilypond_source(arr))
    r = subprocess.run(["lilypond", "--pdf", "--png", "-dresolution=150", "-o", str(outdir / slug), str(ly)],
                       capture_output=True, text=True)
    pdf, png = outdir / f"{slug}.pdf", outdir / f"{slug}.png"
    if r.returncode != 0 or not pdf.exists():
        raise RuntimeError(f"lilypond failed:\n{r.stderr[-2000:]}")
    if not png.exists():  # multi-page output is named slug-page1.png
        first = sorted(outdir.glob(f"{slug}-page1.png"))
        if first:
            first[0].rename(png)
    return pdf, png


def write_midi(arr: Arrangement, path: Path) -> None:
    mid = mido.MidiFile(ticks_per_beat=480)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(arr.sheet.tempo)))
    tr.append(mido.Message("program_change", program=PROGRAM[arr.instrument], time=0))
    events = []
    for x in arr.notes:
        p = arr.tuning.pitch(x.string, x.fret) + arr.sheet.capo
        events.append((x.t, 1, mido.Message("note_on", note=p, velocity=90 if x.melody else 70)))
        events.append((x.t + x.d, 0, mido.Message("note_off", note=p)))
    events.sort(key=lambda e: (e[0], e[1]))
    last = 0.0
    for t, _, msg in events:
        msg.time = round((t - last) * 480)
        last = t
        tr.append(msg)
    mid.save(str(path))


def render_audio(midi: Path, mp3: Path) -> None:
    wav = Path(mp3).with_suffix(".wav")
    r = subprocess.run(["fluidsynth", "-ni", "-r", "44100", "-F", str(wav), SOUNDFONT, str(midi)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"fluidsynth failed: {r.stderr[-500:]}")
    # fluidsynth pads several seconds of silence after the last note: trim it, keep a 1 s tail
    trim = "areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse,apad=pad_dur=1"
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af", trim,
                        "-codec:a", "libmp3lame", "-q:a", "4", str(mp3)], capture_output=True, text=True)
    wav.unlink(missing_ok=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {r.stderr[-500:]}")
