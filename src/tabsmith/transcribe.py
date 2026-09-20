"""MuScriptor transcription with its Beat This! grid, optional BS-RoFormer vocal separation, GPU house rule."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path

import requests

from .leadsheet import Grid, RawNote

CACHE_VERSION = 3  # bump when beat_grid or note extraction changes, so stale caches are ignored


def gpu_wait(max_wait_s: int = 1800, poll_s: int = 30, progress=print) -> None:
    """House rule: never pile onto a running ComfyUI job. Waits while its queue is non-empty."""
    waited = 0
    while waited < max_wait_s:
        try:
            q = requests.get("http://127.0.0.1:8188/queue", timeout=3).json()
            busy = bool(q.get("queue_running") or q.get("queue_pending"))
        except Exception:  # noqa: BLE001 - ComfyUI down or unreachable means nobody else is on the GPU
            busy = False
        if not busy:
            return
        progress(f"GPU busy (ComfyUI queue), waiting {poll_s}s")
        time.sleep(poll_s)
        waited += poll_s
    raise RuntimeError(f"GPU busy with a ComfyUI job for over {max_wait_s // 60} minutes; retry later")


def _require_hf_token() -> None:
    if os.environ.get("HF_TOKEN") or (Path.home() / ".cache/huggingface/token").exists():
        return
    raise RuntimeError("MuScriptor weights need a HuggingFace login. Accept the license at "
                       "https://huggingface.co/MuScriptor/muscriptor-large then run: uvx hf auth login "
                       "(or export HF_TOKEN=hf_...)")


def separate_vocals(audio: Path, workdir: Path, progress=print) -> Path | None:
    from audio_separator.separator import Separator
    stems = Path(workdir) / "stems"
    stems.mkdir(parents=True, exist_ok=True)
    existing = [p for p in stems.glob("*Vocals*") if p.suffix.lower() in (".wav", ".flac")]
    if existing:
        return existing[0]
    progress("separating vocals (BS-RoFormer)")
    sep = Separator(output_dir=str(stems), model_file_dir=str(Path.home() / ".cache/audio-separator"),
                    output_format="WAV", log_level=logging.WARNING)
    sep.load_model()  # default: model_bs_roformer_ep_317_sdr_12.9755.ckpt (vocals / instrumental)
    for f in sep.separate(str(audio)):
        if "Vocals" in Path(f).name:
            p = Path(f)
            return p if p.is_absolute() else stems / p.name
    return None


def normalise_tempo(beats: list[float], lo: float = 70.0, hi: float = 200.0) -> list[float]:
    """Beat trackers pick a tempo octave; folk tunes live in [lo, hi] bpm. Too slow: insert
    midpoints (each beat becomes two). Too fast: keep every other beat."""
    import statistics
    while len(beats) > 2:
        bpm = 60.0 / statistics.median(b - a for a, b in zip(beats, beats[1:]))
        if bpm < lo:
            beats = [x for a, b in zip(beats, beats[1:]) for x in (a, (a + b) / 2)] + [beats[-1]]
        elif bpm > hi:
            beats = beats[::2]
        else:
            break
    return beats


def infer_meter(beats: list[float], downbeats: list[float]) -> tuple[int, float]:
    """(beats per bar, first downbeat time). Downbeat trackers drop phantom downbeats, so instead of
    counting beats between them we ask, for 3/4 and 4/4, which bar phase agrees with the most
    detected downbeats; the meter with the better agreement wins, 4/4 on a tie (cut-time folk)."""
    if not downbeats:
        return 4, beats[0]
    idx = [min(range(len(beats)), key=lambda i: abs(beats[i] - d)) for d in downbeats]
    best = (0.0, 4, 0)
    for bpb in (4, 3):
        for phase in range(bpb):
            agree = sum(1 for i in idx if i % bpb == phase) / len(idx)
            if agree > best[0] + 1e-9:
                best = (agree, bpb, phase)
    _, bpb, phase = best
    return bpb, beats[phase]


def beat_grid(audio: Path, progress=print) -> Grid:
    """Beat This! beats and downbeats. The tracked beat list follows tempo drift (live recordings),
    which MuScriptor's own constant-tempo grid refuses. Falls back to 120 bpm 4/4 on failure."""
    import statistics

    import torch
    from beat_this.inference import File2Beats
    try:
        beats, downbeats = File2Beats(checkpoint_path="final0", device="cuda" if torch.cuda.is_available() else "cpu")(str(audio))
        beats = [float(b) for b in beats]
        downbeats = [float(d) for d in downbeats]
        if len(beats) < 8:
            raise ValueError("too few beats")
        beats = normalise_tempo(beats)
        bpm = 60.0 / statistics.median(b - a for a, b in zip(beats, beats[1:]))
        bpb, first = infer_meter(beats, downbeats)
        progress(f"beat grid: {bpm:.1f} bpm, {bpb} beats per bar, first downbeat at {first:.2f}s")
        return Grid(bpm, bpb, first, beats)
    except Exception as e:  # noqa: BLE001 - any tracker failure means a constant guess, not a crash
        progress(f"beat tracking failed ({e.__class__.__name__}: {e}), assuming 120 bpm 4/4 (use --bpm/--meter)")
        return Grid(120.0, 4, 0.0, None)


def _run_model(model, audio: Path, instruments: list[str] | None, progress) -> list[RawNote]:
    from muscriptor import NoteEndEvent
    notes: list[RawNote] = []
    last = -1
    for ev in model.transcribe(str(audio), instruments=instruments):
        if isinstance(ev, NoteEndEvent):
            s = ev.start_event
            notes.append(RawNote(s.instrument, s.pitch, s.start_time, ev.end_time))
        elif hasattr(ev, "completed") and ev.total and ev.completed * 10 // ev.total != last:
            last = ev.completed * 10 // ev.total
            progress(f"transcribing {audio.name}: {last * 10}%")
    return notes


def transcribe(audio: Path, workdir: Path, *, model_size: str = "large", separate: str = "auto",
               progress=print) -> tuple[list[RawNote], Grid]:
    audio, workdir = Path(audio), Path(workdir)
    key = hashlib.sha256(audio.read_bytes()).hexdigest()[:16] + f"-{model_size}-{separate}-v{CACHE_VERSION}"
    cache = workdir / "transcription.json"
    if cache.exists():
        d = json.loads(cache.read_text())
        if d.get("key") == key:
            progress("transcription cached")
            return [RawNote(**n) for n in d["notes"]], Grid(**d["grid"])
    _require_hf_token()
    gpu_wait(progress=progress)
    import torch
    from muscriptor import TranscriptionModel

    def load():
        progress(f"loading MuScriptor {model_size}")
        if not torch.cuda.is_available():
            return TranscriptionModel.load_model(model_size, device="cpu")
        # MuScriptor builds the fp32 model on the target device before casting, which needs
        # 5.6 GB for large; ComfyUI keeps ~24 GB resident on this box. Build on CPU in bf16
        # (2.8 GB), then move. Uses the public constructor with the loaded parts.
        cpu = TranscriptionModel.load_model(model_size, device="cpu", dtype="bfloat16")
        gpu = torch.device("cuda")
        lm = cpu._model.to(gpu)
        lm.device_type = "cuda"  # autocast context
        for m in lm.modules():   # conditioners cache the device they were built on
            if "device" in vars(m):
                m.device = gpu
        return TranscriptionModel(lm, cpu._tokenizer, gpu)

    grid = beat_grid(audio, progress)
    model = load()
    notes = _run_model(model, audio, None, progress)
    has_voice = sum(n.instrument == "voice" for n in notes) >= 8
    if separate == "on" or (separate == "auto" and has_voice):
        del model  # separation and transcription never share the GPU at once
        torch.cuda.empty_cache()
        stem = separate_vocals(audio, workdir, progress)
        torch.cuda.empty_cache()
        if stem is not None:
            model = load()
            vocal = _run_model(model, stem, ["voice"], progress)
            if len(vocal) >= 8:
                notes = [n for n in notes if n.instrument != "voice"] + vocal
            del model
    torch.cuda.empty_cache()
    if grid.beats is not None:  # a fallback grid is a guess: never cache it, so the tracker is retried
        cache.write_text(json.dumps({"key": key, "grid": grid.__dict__, "notes": [n.__dict__ for n in notes]}))
    return notes, grid
