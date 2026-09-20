"""Turn a lead sheet into instrument-idiomatic tab notes. Melody first, fill second."""
from __future__ import annotations

from dataclasses import dataclass, replace

from .fretboard import TUNINGS, FretMapper, Shape, Tuning, shape_for, shape_position
from .leadsheet import LeadSheet, MelodyNote

STYLES = {"banjo": ("scruggs", "clawhammer"), "guitar": ("travis", "flatpick")}
# ponytail: a low ceiling pushes phrases into open position when an octave down still fits;
# travis keeps the melody on the top three strings so its floor is G3
RANGE = {"scruggs": (50, 71), "clawhammer": (50, 71), "travis": (55, 76), "flatpick": (40, 72)}
GRID = 0.25


@dataclass
class TabNote:
    t: float
    d: float
    string: int
    fret: int
    finger: str = ""
    tech: str = ""      # "h" / "p" / "s" into the next note on the same string
    melody: bool = False


@dataclass
class Arrangement:
    instrument: str
    style: str
    tuning: Tuning
    sheet: LeadSheet
    notes: list[TabNote]


def fit_range(sheet: LeadSheet, lo: int, hi: int) -> LeadSheet:
    """Octave-shift each phrase (notes separated by a gap >= 1 beat) into [lo, hi]."""
    out: list[MelodyNote] = []
    phrase: list[MelodyNote] = []

    def flush() -> None:
        if not phrase:
            return
        shift = 0
        top, bottom = max(n.p for n in phrase), min(n.p for n in phrase)
        while top + shift > hi and bottom + shift - 12 >= lo:
            shift -= 12
        while bottom + shift < lo and top + shift + 12 <= hi:
            shift += 12
        for n in phrase:
            p = n.p + shift
            while p < lo:          # last resort for a phrase wider than the window: move the stray note alone
                p += 12
            while p > hi + 8:
                p -= 12
            out.append(replace(n, p=p))

    for n in sorted(sheet.melody, key=lambda n: n.t):
        if phrase and n.t - (phrase[-1].t + phrase[-1].d) >= 1.0:
            flush()
            phrase = []
        phrase.append(n)
    flush()
    return replace(sheet, melody=out)


def quantise_melody(sheet: LeadSheet, step: float) -> LeadSheet:
    """Snap melody onsets to a coarser grid (roll styles think in 8ths). Two notes landing on the
    same slot keep the longer one: a vocal 16th-note ornament becomes one 8th on the banjo."""
    best: dict[int, MelodyNote] = {}
    for n in sheet.melody:
        k = round(n.t / step)
        if k not in best or n.d > best[k].d:
            best[k] = replace(n, t=k * step, d=max(step, round(n.d / step) * step))
    return replace(sheet, melody=[best[k] for k in sorted(best)])


def _melody_at(sheet: LeadSheet, t: float, window: float) -> MelodyNote | None:
    """Melody note starting in [t, t+window), earliest wins."""
    hits = [m for m in sheet.melody if t - 1e-9 <= m.t < t + window - 1e-9]
    return min(hits, key=lambda m: m.t) if hits else None


def _place_melody(tuning: Tuning, shape: Shape, pitch: int,
                  strings: tuple[int, ...] | None = None) -> tuple[int, int]:
    """A string whose shape fret already gives the pitch, else the mapper anchored at the shape."""
    for s, f in enumerate(shape, 1):
        if f >= 0 and tuning.pitch(s, f) == pitch and (strings is None or s in strings):
            return s, f
    return FretMapper(tuning, strings).assign([pitch], anchor=shape_position(shape))[0]


def _finger_banjo(string: int, prev: str) -> str:
    if string == 1:
        return "M"
    if string == 2:
        return "I"
    return "I" if prev == "T" and string == 3 else "T"


# Scruggs rolls: string per 8th note over a bar. 4/4 rolls have 8 slots, 3/4 rolls 6.
ROLLS = {
    "forward": (3, 2, 1, 5, 3, 2, 1, 5),
    "backward": (1, 2, 5, 1, 2, 5, 1, 2),
    "forward_backward": (3, 2, 1, 5, 1, 2, 3, 1),
    "alternating": (3, 2, 5, 1, 4, 2, 5, 1),
    "foggy": (2, 1, 5, 1, 5, 3, 2, 1),
}
WALTZ_ROLLS = {
    "forward": (3, 2, 1, 5, 2, 1),
    "backward": (1, 2, 5, 1, 2, 3),
    "forward_backward": (3, 2, 1, 5, 1, 2),
    "alternating": (3, 2, 5, 1, 4, 5),
    "foggy": (2, 1, 5, 1, 3, 2),
}
_ROLL_ROTATION = ("forward", "alternating", "forward_backward", "backward")


def _scruggs(sheet: LeadSheet, tuning: Tuning, patterns: dict[str, str]) -> list[TabNote]:
    notes: list[TabNote] = []
    labels = {s["bar"]: s["label"] for s in sheet.sections}
    label = "A"
    rolls = WALTZ_ROLLS if sheet.bpb == 3 else ROLLS
    for bar in range(sheet.bars):
        label = labels.get(bar, label)
        roll = rolls[patterns.get(label, _ROLL_ROTATION[bar % len(_ROLL_ROTATION)])]
        prev = ""
        for slot in range(sheet.bpb * 2):
            t = bar * sheet.bpb + slot * 0.5
            shape = shape_for(tuning, sheet.chord_at(t))
            m = _melody_at(sheet, t, 0.5)
            if m:
                s, f = _place_melody(tuning, shape, m.p)
                notes.append(TabNote(t, 0.5, s, f, _finger_banjo(s, prev), melody=True))
            else:
                s = roll[slot % len(roll)]
                notes.append(TabNote(t, 0.5, s, max(shape[s - 1], 0), _finger_banjo(s, prev)))
            prev = notes[-1].finger
    return _ornament_banjo(notes)


def _ornament_banjo(notes: list[TabNote]) -> list[TabNote]:
    """Scruggs vocabulary from the melody's own motion on one string within an 8th:
    open to fret 1-2 is a hammer-on, fretted up 1-2 is a slide, down 1-2 is a pull-off."""
    melody = [n for n in notes if n.melody]
    for a, b in zip(melody, melody[1:]):
        if a.string != b.string or b.t - a.t > 0.5 + 1e-9 or a.tech:
            continue
        diff = b.fret - a.fret
        if 1 <= diff <= 2:
            a.tech = "h" if a.fret == 0 else "s"
        elif -2 <= diff <= -1:
            a.tech = "p"
    return notes


def _clawhammer(sheet: LeadSheet, tuning: Tuning) -> list[TabNote]:
    """bum-ditty per beat: bum on the beat (melody or top string), brush on the 'and',
    thumb on the fifth at the 'a'. Drop-thumb: a melody note on the 'and' goes to the thumb."""
    notes: list[TabNote] = []
    for bar in range(sheet.bars):
        for beat in range(sheet.bpb):
            t = bar * sheet.bpb + beat
            shape = shape_for(tuning, sheet.chord_at(t))
            m = _melody_at(sheet, t, 0.5)
            if m:
                s, f = _place_melody(tuning, shape, m.p, strings=(1, 2, 3, 4))
                notes.append(TabNote(t, 0.5, s, f, "D", melody=True))
            else:
                notes.append(TabNote(t, 0.5, 1, max(shape[0], 0), "D"))
            m2 = _melody_at(sheet, t + 0.5, 0.25)
            if m2:
                s, f = _place_melody(tuning, shape, m2.p, strings=(2, 3, 4))
                notes.append(TabNote(t + 0.5, 0.25, s, f, "T", melody=True))
            else:
                notes.extend(TabNote(t + 0.5, 0.25, s, max(shape[s - 1], 0), "B") for s in (1, 2, 3))
            notes.append(TabNote(t + 0.75, 0.25, 5, 0, "T"))
    return _ornament_banjo(notes)


def _travis(sheet: LeadSheet, tuning: Tuning) -> list[TabNote]:
    """Alternating bass on the beats from the chord shape, melody on strings 1-3,
    shape fill on empty off-beats."""
    notes: list[TabNote] = []
    for bar in range(sheet.bars):
        for beat in range(sheet.bpb):
            t = bar * sheet.bpb + beat
            shape = shape_for(tuning, sheet.chord_at(t))
            bass_strings = [s for s in range(tuning.n, 0, -1) if shape[s - 1] >= 0][:2]
            s = bass_strings[beat % len(bass_strings)]
            notes.append(TabNote(t, 1.0, s, shape[s - 1], "p"))
            if not _melody_at(sheet, t + 0.5, 0.5) and not _melody_at(sheet, t, 0.5):
                notes.append(TabNote(t + 0.5, 0.5, 2, max(shape[1], 0), "i"))
    for m in sorted(sheet.melody, key=lambda m: m.t):
        shape = shape_for(tuning, sheet.chord_at(m.t))
        s, f = _place_melody(tuning, shape, m.p, strings=(1, 2, 3))
        notes.append(TabNote(m.t, m.d, s, f, {1: "a", 2: "m"}.get(s, "i"), melody=True))
    return notes


def _flatpick(sheet: LeadSheet, tuning: Tuning) -> list[TabNote]:
    mel = sorted(sheet.melody, key=lambda m: m.t)
    pos = FretMapper(tuning).assign([m.p for m in mel], anchor=0)
    return [TabNote(m.t, m.d, s, f, melody=True) for m, (s, f) in zip(mel, pos)]


def arrange(sheet: LeadSheet, instrument: str, style: str,
            patterns: dict[str, str] | None = None) -> Arrangement:
    if style not in STYLES.get(instrument, ()):
        raise ValueError(f"unknown {instrument} style {style!r}; choose from {STYLES.get(instrument)}")
    tuning = TUNINGS[instrument]
    sheet = fit_range(sheet, *RANGE[style])
    if style in ("scruggs", "clawhammer"):
        sheet = quantise_melody(sheet, 0.5)
    if style == "scruggs":
        notes = _scruggs(sheet, tuning, patterns or {})
    elif style == "clawhammer":
        notes = _clawhammer(sheet, tuning)
    elif style == "travis":
        notes = _travis(sheet, tuning)
    else:
        notes = _flatpick(sheet, tuning)
    # a fill note never collides with a melody note on the same string at the same time
    taken = {(round(n.t / GRID), n.string) for n in notes if n.melody}
    notes = [n for n in notes if n.melody or (round(n.t / GRID), n.string) not in taken]
    notes = _enforce_span(notes, SPAN[instrument])
    notes.sort(key=lambda n: (n.t, n.string))
    return Arrangement(instrument, style, tuning, sheet, notes)


SPAN = {"banjo": 4, "guitar": 5}


def _enforce_span(notes: list[TabNote], limit: int) -> list[TabNote]:
    """Melody wins: a fretted fill note struck together with a fretted melody note and more than
    the hand span away from its fret is dropped (same rule as check_invariants)."""
    melody = [n for n in notes if n.melody and n.fret > 0]
    drop = set()
    for i, n in enumerate(notes):
        if n.melody or n.fret <= 0:
            continue
        if any(abs(m.t - n.t) < 1e-9 and abs(m.fret - n.fret) > limit for m in melody):
            drop.add(i)
    return [n for i, n in enumerate(notes) if i not in drop]


def check_invariants(arr: Arrangement) -> None:
    t, sheet = arr.tuning, arr.sheet
    span_limit = 4 if arr.instrument == "banjo" else 5
    for n in arr.notes:
        assert t.ok(n.string, n.fret), f"bar {sheet.bar_of(n.t)}: string {n.string} fret {n.fret} not playable"
    seen = set()
    for n in arr.notes:
        key = (round(n.t / GRID), n.string)
        assert key not in seen, f"bar {sheet.bar_of(n.t)}: two notes on string {n.string} at beat {n.t}"
        seen.add(key)
    for m in sheet.melody:
        hit = [n for n in arr.notes if abs(n.t - m.t) < 1e-6 and n.melody]
        assert hit, f"bar {sheet.bar_of(m.t)}: melody note {m.p} at {m.t} missing"
        assert t.pitch(hit[0].string, hit[0].fret) % 12 == m.p % 12, \
            f"bar {sheet.bar_of(m.t)}: wrong pitch class at {m.t}"
    # hand span applies to notes struck together; a shift between successive notes is allowed
    fretted = [n for n in arr.notes if n.fret > 0]
    for a in fretted:
        window = [b.fret for b in fretted if abs(b.t - a.t) < 1e-9]
        assert max(window) - min(window) <= span_limit, \
            f"bar {sheet.bar_of(a.t)}: fret span {min(window)}-{max(window)} at {a.t}"
