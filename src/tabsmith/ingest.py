"""Turn whatever the user gave us (audio path, URL, MIDI/MusicXML, leadsheet.json) into pipeline input."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .leadsheet import Grid, LeadSheet, RawNote

AUDIO_EXT = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".opus", ".aac"}
SCORE_EXT = {".mid", ".midi", ".xml", ".musicxml", ".mxl"}


@dataclass
class Ingested:
    title: str
    audio: Path | None = None
    sheet: LeadSheet | None = None
    raw: tuple[list[RawNote], Grid] | None = None


def _download(url: str, workdir: Path) -> Ingested:
    import yt_dlp
    opts = {"format": "bestaudio/best", "outtmpl": str(workdir / "source.%(ext)s"), "quiet": True,
            "noplaylist": True, "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}]}
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(url, download=True)
    return Ingested(info.get("title") or "untitled", audio=workdir / "source.wav")


def _mean_pitch(part) -> float:
    ns = [n for n in part.flatten().notes if n.isNote]
    return sum(n.pitch.midi for n in ns) / len(ns) if ns else 0.0


def _score(path: Path) -> Ingested:
    import music21
    sc = music21.converter.parse(str(path))
    parts = list(sc.parts) or [sc]
    mel = next((p for p in parts if re.search(r"melod|vocal|voice|lead", (p.partName or "").lower())), None)
    if mel is None:
        mel = max(parts, key=_mean_pitch)
    others = [p for p in parts if p is not mel]
    bass = min(others, key=_mean_pitch) if others else None
    mm = sc.flatten().getElementsByClass(music21.tempo.MetronomeMark)
    bpm = float(mm[0].number) if mm and mm[0].number else 120.0
    ts = sc.flatten().getElementsByClass(music21.meter.TimeSignature)
    # onsets are in quarter notes, so the bar length must be too (6/8 -> 3 quarter beats)
    bpb = max(1, round(float(ts[0].barDuration.quarterLength))) if ts else 4
    spb = 60.0 / bpm
    notes: list[RawNote] = []
    for p in parts:
        inst = "voice" if p is mel else "acoustic_bass" if p is bass else "acoustic_piano"
        for el in p.flatten().notes:
            for pitch in getattr(el, "pitches", ()):  # Unpitched / percussion elements have none
                notes.append(RawNote(inst, pitch.midi, float(el.offset) * spb,
                                     float(el.offset + el.quarterLength) * spb))
    title = sc.metadata.title if sc.metadata and sc.metadata.title else path.stem
    return Ingested(title, raw=(notes, Grid(bpm, bpb, 0.0, None)))


def ingest(src: str, workdir: Path) -> Ingested:
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    if re.match(r"https?://", src):
        return _download(src, workdir)
    p = Path(src)
    if not p.exists():
        raise FileNotFoundError(src)
    ext = p.suffix.lower()
    if ext == ".json":
        sheet = LeadSheet.load(p)
        return Ingested(sheet.title, sheet=sheet)
    if ext in SCORE_EXT:
        return _score(p)
    if ext in AUDIO_EXT:
        return Ingested(p.stem, audio=p)
    raise ValueError(f"unsupported input {p.name}; want audio {sorted(AUDIO_EXT)}, "
                     f"score {sorted(SCORE_EXT)}, .json or a URL")
