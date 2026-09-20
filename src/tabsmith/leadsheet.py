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
