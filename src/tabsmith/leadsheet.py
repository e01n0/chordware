"""Lead sheet: the contract between the analysis half and the arrangement half."""
from __future__ import annotations

import json
import math
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path

PC_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_FLATS = {"Db": 1, "Eb": 3, "Gb": 6, "Ab": 8, "Bb": 10}
QUALITIES = {"": "maj", "m": "min", "7": "dom7", "m7": "min7",
             "maj": "maj", "min": "min", "dom7": "dom7", "min7": "min7"}
_SUFFIX = {"maj": "", "min": "m", "dom7": "7", "min7": "m7"}
GRID = 0.25


def parse_chord(name: str) -> tuple[int, str]:
    name = name.strip()
    root = name[:2] if len(name) > 1 and name[1] in "#b" else name[:1]
    pc = _FLATS[root] if root in _FLATS else PC_NAMES.index(root)
    return pc, QUALITIES[name[len(root):]]


def chord_name(root_pc: int, quality: str) -> str:
    return PC_NAMES[root_pc % 12] + _SUFFIX[quality]


@dataclass
class MelodyNote:
    t: float
    d: float
    p: int


@dataclass
class Chord:
    bar: int
    beat: float
    name: str


@dataclass
class LeadSheet:
    title: str
    source: str
    tempo: float
    meter: tuple[int, int]
    key: str
    mode: str
    capo: int
    bars: int
    melody: list[MelodyNote]
    chords: list[Chord]
    sections: list[dict] = field(default_factory=list)

    @property
    def bpb(self) -> int:
        return self.meter[0]

    def bar_of(self, t: float) -> int:
        return int(t // self.bpb)

    def chord_at(self, t: float) -> str:
        cur = self.chords[0].name
        for c in self.chords:
            if c.bar * self.bpb + c.beat <= t + 1e-9:
                cur = c.name
            else:
                break
        return cur

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=1)

    @classmethod
    def from_json(cls, s: str) -> "LeadSheet":
        d = json.loads(s)
        d["meter"] = tuple(d["meter"])
        d["melody"] = [MelodyNote(**n) for n in d["melody"]]
        d["chords"] = [Chord(**c) for c in d["chords"]]
        return cls(**d)

    def save(self, path: Path) -> None:
        Path(path).write_text(self.to_json())

    @classmethod
    def load(cls, path: Path) -> "LeadSheet":
        return cls.from_json(Path(path).read_text())


# ---------------------------------------------------------------- extraction

@dataclass
class RawNote:
    instrument: str
    pitch: int
    onset: float
    offset: float


@dataclass
class Grid:
    bpm: float
    beats_per_bar: int | None
    first_downbeat: float
    beats: list[float] | None = None

    def beat_of(self, t: float) -> float:
        b = self.beats
        if b and len(b) > 1:
            if t <= b[0]:
                return (t - b[0]) / (b[1] - b[0])
            if t >= b[-1]:
                return len(b) - 1 + (t - b[-1]) / (b[-1] - b[-2])
            for i in range(len(b) - 1):
                if b[i] <= t < b[i + 1]:
                    return i + (t - b[i]) / (b[i + 1] - b[i])
        return t * self.bpm / 60.0


BASS = {"acoustic_bass", "electric_bass", "contrabass"}
NOT_MELODY = BASS | {"drums", "acoustic_piano", "electric_piano", "organ", "chromatic_percussion", "timpani"}
FRIENDLY = {"banjo": (7, 0, 2), "guitar": (7, 0, 2, 9, 4)}   # banjo G C D; guitar adds A E
_TEMPLATES = {"maj": (0, 4, 7), "min": (0, 3, 7), "dom7": (0, 4, 7, 10), "min7": (0, 3, 7, 10)}
_KRUMHANSL = {
    "major": [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
    "minor": [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
}


def track_table(notes: list[RawNote]) -> list[tuple[str, int, float]]:
    by: dict[str, list[int]] = {}
    for n in notes:
        by.setdefault(n.instrument, []).append(n.pitch)
    return sorted(((k, len(v), statistics.fmean(v)) for k, v in by.items()), key=lambda r: -r[1])


def pick_melody_track(notes: list[RawNote], override: str | None = None) -> str:
    table = track_table(notes)
    if override:
        if override not in {r[0] for r in table}:
            raise ValueError(f"no track {override!r}; have {[r[0] for r in table]}")
        return override
    if any(r[0] == "voice" and r[1] >= 8 for r in table):
        return "voice"
    cands = [r for r in table if r[0] not in NOT_MELODY] or table
    return max(cands, key=lambda r: r[1] * (1.5 if r[2] > 60 else 1.0))[0]


def detect_key(pc_hist: list[float]) -> tuple[int, str]:
    def corr(a, b):
        ma, mb = sum(a) / 12, sum(b) / 12
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) or 1e-9
        return num / den
    best = max((corr(pc_hist, prof[-k:] + prof[:-k]), k, mode)
               for mode, prof in _KRUMHANSL.items() for k in range(12))
    return best[1], best[2]


def choose_capo(key_pc: int, mode: str, instrument: str) -> tuple[int, int]:
    """(written key pc, semitones the written part sits below the sounding key).
    A result <= 5 is a capo; otherwise the song is transposed to the nearest friendly key."""
    major = key_pc if mode == "major" else (key_pc + 3) % 12
    fits = [((major - t) % 12, t) for t in FRIENDLY[instrument] if (major - t) % 12 <= 5]
    if fits:
        down = min(fits)[0]
        return (key_pc - down) % 12, down
    shift = min((((t - major + 6) % 12) - 6 for t in FRIENDLY[instrument]), key=abs)
    return (key_pc + shift) % 12, -shift


def _hist(notes: list[RawNote], start: float, end: float) -> tuple[list[float], int | None, int | None]:
    """Duration-weighted pitch-class histogram of beat-domain notes in [start, end),
    plus the lowest bass-track pitch and the lowest pitch of any track."""
    h = [0.0] * 12
    bass_lowest = lowest = None
    for n in notes:
        if n.instrument == "drums":
            continue
        a, b = max(n.onset, start), min(n.offset, end)
        if b <= a:
            continue
        h[n.pitch % 12] += b - a
        if lowest is None or n.pitch < lowest:
            lowest = n.pitch
        if n.instrument in BASS and (bass_lowest is None or n.pitch < bass_lowest):
            bass_lowest = n.pitch
    return h, bass_lowest, lowest


def _best_chord(h: list[float], bass: int | None, lowest: int | None, key_pc: int, mode: str) -> tuple[str, float]:
    steps = (0, 2, 4, 5, 7, 9, 11) if mode == "major" else (0, 2, 3, 5, 7, 8, 10)
    scale = {(key_pc + i) % 12 for i in steps}
    total = sum(h)
    best = ("", -1e9)
    for root in range(12):
        for q, tpl in _TEMPLATES.items():
            inside = {(root + i) % 12 for i in tpl}
            score = sum(h[pc] for pc in inside) - 0.5 * sum(h[pc] for pc in range(12) if pc not in inside)
            score += 0.2 * (root in scale)
            if bass is not None:
                score += 2.0 * (bass % 12 == root)
            elif lowest is not None:
                score += 0.7 * (lowest % 12 == root)
            # a four-note template covers more of the bar for free: charge it 30% of the bar's weight,
            # so a seventh only appears when its pitch class carries real weight (folk bias, on purpose)
            if len(tpl) == 4:
                score -= 0.3 * total
            if score > best[1]:
                best = (chord_name(root, q), score)
    return best


def notes_to_leadsheet(notes: list[RawNote], grid: Grid, *, title: str, source: str, instrument: str,
                       melody_track: str | None = None, key: str | None = None, capo: int | None = None,
                       meter: int | None = None) -> LeadSheet:
    if not notes:
        raise ValueError("no notes transcribed")
    bpb = meter or grid.beats_per_bar or 4
    origin = grid.beat_of(grid.first_downbeat)
    beat_notes = [RawNote(n.instrument, n.pitch, grid.beat_of(n.onset) - origin, grid.beat_of(n.offset) - origin)
                  for n in notes]
    track = pick_melody_track(notes, melody_track)
    mel_raw = [n for n in beat_notes if n.instrument == track]
    if not mel_raw:
        raise ValueError(f"melody track {track!r} has no notes")
    if min(n.onset for n in mel_raw) < -GRID:   # pickup notes get a bar of their own
        beat_notes = [RawNote(n.instrument, n.pitch, n.onset + bpb, n.offset + bpb) for n in beat_notes]
        mel_raw = [n for n in beat_notes if n.instrument == track]
    # skyline: highest note starting in each 16th slot; duration up to the next melody onset
    slots: dict[int, RawNote] = {}
    for n in mel_raw:
        k = round(n.onset / GRID)
        if k >= 0 and (k not in slots or n.pitch > slots[k].pitch):
            slots[k] = n
    keys = sorted(slots)
    melody: list[MelodyNote] = []
    for i, k in enumerate(keys):
        n = slots[k]
        end = round(n.offset / GRID) * GRID
        nxt = keys[i + 1] * GRID if i + 1 < len(keys) else end
        melody.append(MelodyNote(k * GRID, max(GRID, min(end, nxt) - k * GRID), n.pitch))
    if not melody:
        raise ValueError("melody track has no notes after the first downbeat")
    if len(melody) >= 8:
        # spike: a single polyphonic track (fingerstyle guitar, piano) leaks its bass notes into the
        # skyline wherever the tune rests; drop anything far below the melody's median register
        med = statistics.median(m.p for m in melody)
        melody = [m for m in melody if m.p >= med - 9]
    # the arrangement ends where the melody ends; stray accompaniment tails do not add bars
    bars = max(1, math.ceil((melody[-1].t + melody[-1].d) / bpb - 1e-6))
    key_pc, mode = detect_key(_hist(beat_notes, 0, bars * bpb)[0])
    chords: list[Chord] = []
    for bar in range(bars):
        s0 = bar * bpb
        whole, whole_score = _best_chord(*_hist(beat_notes, s0, s0 + bpb), key_pc, mode)
        halves = []
        for half in (0, 1):
            a = s0 + half * bpb / 2
            halves.append(_best_chord(*_hist(beat_notes, a, a + bpb / 2), key_pc, mode))
        if halves[0][0] != halves[1][0] and all(hc != whole and sc > whole_score / 2 + 0.3 for hc, sc in halves):
            chords.append(Chord(bar, 0.0, halves[0][0]))
            chords.append(Chord(bar, bpb / 2, halves[1][0]))
        else:
            chords.append(Chord(bar, 0.0, whole))
    merged = [c for i, c in enumerate(chords) if i == 0 or c.name != chords[i - 1].name]
    if key is not None:
        written_pc = parse_chord(key)[0]
        down = (key_pc - written_pc) % 12
        down = down if down <= 5 else down - 12
    elif capo is not None:
        written_pc, down = (key_pc - capo) % 12, capo
    else:
        written_pc, down = choose_capo(key_pc, mode, instrument)
    melody = [MelodyNote(m.t, m.d, m.p - down) for m in melody]
    merged = [Chord(c.bar, c.beat, chord_name((parse_chord(c.name)[0] - down) % 12, parse_chord(c.name)[1]))
              for c in merged]
    return LeadSheet(title, source, round(grid.bpm, 1), (bpb, 4), PC_NAMES[written_pc], mode,
                     max(down, 0), bars, melody, merged, [])
