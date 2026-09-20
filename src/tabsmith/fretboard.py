"""Tunings, chord shapes and the fret mapper: the only place string/fret geometry is decided."""
from __future__ import annotations

from dataclasses import dataclass

from .leadsheet import parse_chord

MAX_FRET = 17


@dataclass(frozen=True)
class Tuning:
    name: str
    open: tuple[int, ...]                      # index 0 = string 1 (highest)
    allowed: tuple[frozenset[int] | None, ...]  # per string; None = 0..MAX_FRET

    @property
    def n(self) -> int:
        return len(self.open)

    def pitch(self, string: int, fret: int) -> int:
        return self.open[string - 1] + fret

    def ok(self, string: int, fret: int) -> bool:
        if fret < 0 or fret > MAX_FRET:
            return False
        a = self.allowed[string - 1]
        return True if a is None else fret in a

    def positions(self, pitch: int) -> list[tuple[int, int]]:
        return [(s, pitch - o) for s, o in enumerate(self.open, 1) if self.ok(s, pitch - o)]


BANJO_G = Tuning("banjo-open-g", (62, 59, 55, 50, 67),
                 (None, None, None, None, frozenset({0, *range(5, MAX_FRET + 1)})))
GUITAR = Tuning("guitar-standard", (64, 59, 55, 50, 45, 40), (None,) * 6)
TUNINGS = {"banjo": BANJO_G, "guitar": GUITAR}

Shape = tuple[int, ...]

# spike: hand-typed open shapes; extend as songs demand
SHAPES: dict[str, dict[str, Shape]] = {
    "banjo-open-g": {
        "G": (0, 0, 0, 0, 0), "C": (2, 1, 0, 2, 0), "D": (4, 3, 2, 0, 0), "D7": (4, 1, 2, 0, 0),
        "Em": (2, 0, 0, 2, 0), "Am": (2, 1, 2, 2, 0), "A": (2, 2, 2, 2, 0), "E": (2, 1, 1, 2, 0),
        "F": (3, 1, 2, 3, 0), "Bm": (4, 3, 4, 4, 0), "G7": (0, 0, 0, 3, 0), "C7": (2, 1, 3, 2, 0),
        "A7": (2, 2, 2, 2, 0), "Dm": (3, 3, 2, 0, 0), "Em7": (2, 0, 0, 0, 0),
    },
    "guitar-standard": {
        "E": (0, 0, 1, 2, 2, 0), "A": (0, 2, 2, 2, 0, -1), "D": (2, 3, 2, 0, -1, -1), "G": (3, 0, 0, 0, 2, 3),
        "C": (0, 1, 0, 2, 3, -1), "Em": (0, 0, 0, 2, 2, 0), "Am": (0, 1, 2, 2, 0, -1), "Dm": (1, 3, 2, 0, -1, -1),
        "E7": (0, 0, 1, 0, 2, 0), "A7": (0, 2, 0, 2, 0, -1), "D7": (2, 1, 2, 0, -1, -1), "G7": (1, 0, 0, 0, 2, 3),
        "C7": (0, 1, 3, 2, 3, -1), "B7": (2, 0, 2, 1, 2, -1), "F": (1, 1, 2, 3, 3, 1), "Bm": (2, 3, 4, 4, 2, -1),
        "Am7": (0, 1, 0, 2, 0, -1), "Em7": (0, 3, 0, 2, 2, 0), "Dm7": (1, 1, 2, 0, -1, -1),
    },
}
# movable shapes: (root pitch class of the shape at fret 0, shape) per quality
_BARRE: dict[str, dict[str, tuple[int, Shape]]] = {
    "banjo-open-g": {"maj": (7, (0, 0, 0, 0, 0)), "min": (9, (2, 1, 2, 2, 0)),
                     "dom7": (7, (0, 0, 0, 3, 0)), "min7": (4, (2, 0, 0, 0, 0))},
    "guitar-standard": {"maj": (4, (0, 0, 1, 2, 2, 0)), "min": (4, (0, 0, 0, 2, 2, 0)),
                        "dom7": (4, (0, 0, 1, 0, 2, 0)), "min7": (4, (0, 3, 0, 2, 2, 0))},
}


def shape_for(tuning: Tuning, chord: str) -> Shape:
    lib = SHAPES[tuning.name]
    if chord in lib:
        return lib[chord]
    root, quality = parse_chord(chord)
    base_root, shape = _BARRE[tuning.name][quality]
    up = (root - base_root) % 12
    moved = tuple(f + up if f >= 0 else -1 for f in shape)
    if tuning.name == "banjo-open-g":
        moved = moved[:4] + (0,)  # fifth string stays open
    return moved


def shape_position(shape: Shape) -> int:
    fretted = [f for f in shape if f > 0]
    return min(fretted) if fretted else 0


class FretMapper:
    """Cheapest string/fret path for a pitch sequence.
    ponytail: full DP over all candidates, O(n * strings); fine for song-length input."""
    W_ANCHOR, W_MOVE, W_SWITCH, W_HIGH, OPEN_BONUS = 1.0, 1.5, 0.3, 0.15, -0.8

    def __init__(self, tuning: Tuning, strings: tuple[int, ...] | None = None):
        self.t = tuning
        self.strings = strings

    def _cands(self, pitch: int) -> list[tuple[int, int]]:
        c = [(s, f) for s, f in self.t.positions(pitch) if self.strings is None or s in self.strings]
        return c or self.t.positions(pitch) or [(1, -1)]  # fret -1 = unplayable marker

    def _cost(self, prev: tuple[int, int] | None, cur: tuple[int, int], anchor: int) -> float:
        s, f = cur
        c = self.W_HIGH * f + (self.OPEN_BONUS if f == 0 else self.W_ANCHOR * abs(f - anchor))
        if prev and f > 0 and prev[1] > 0:
            c += self.W_MOVE * abs(f - prev[1])
        if prev and prev[0] != s:
            c += self.W_SWITCH
        return c

    def assign(self, pitches: list[int], anchor: int = 0) -> list[tuple[int, int]]:
        if not pitches:
            return []
        layers = [self._cands(p) for p in pitches]
        back: list[list[tuple[float, int | None]]] = [[(self._cost(None, c, anchor), None) for c in layers[0]]]
        for i in range(1, len(layers)):
            row = []
            for c in layers[i]:
                j, cost = min(((j, back[-1][j][0] + self._cost(prev, c, anchor))
                               for j, prev in enumerate(layers[i - 1])), key=lambda x: x[1])
                row.append((cost, j))
            back.append(row)
        j = min(range(len(back[-1])), key=lambda k: back[-1][k][0])
        out = []
        for i in range(len(layers) - 1, -1, -1):
            out.append(layers[i][j])
            j = back[i][j][1]
        return out[::-1]
