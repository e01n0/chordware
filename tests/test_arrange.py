import pytest

from tabsmith.arrange import STYLES, TabNote, arrange, check_invariants, fit_range
from tabsmith.leadsheet import Chord, LeadSheet, MelodyNote


def sheet_4_4():
    melody = [MelodyNote(t, 0.5, p) for t, p in
              [(0, 67), (0.5, 69), (1, 71), (1.5, 74), (2, 71), (2.5, 69), (3, 67), (3.5, 64),
               (4, 62), (4.5, 64), (5, 67), (5.5, 69), (6, 67), (7, 62)]]
    return LeadSheet("Cripple Creek", "t", 120, (4, 4), "G", "major", 0, 2, melody,
                     [Chord(0, 0, "G"), Chord(1, 0, "C"), Chord(1, 2, "G")], [])


def sheet_3_4():
    melody = [MelodyNote(0, 1, 62), MelodyNote(1, 1, 66), MelodyNote(2, 1, 69),
              MelodyNote(3, 2, 74), MelodyNote(5, 1, 71)]
    return LeadSheet("Waltz", "t", 100, (3, 4), "D", "major", 0, 2, melody,
                     [Chord(0, 0, "D"), Chord(1, 0, "A7")], [])


def sheet_out_of_shape():
    # melody notes not in the chord shape (B and A over G, F# over C)
    melody = [MelodyNote(0, 1, 71), MelodyNote(1, 1, 69), MelodyNote(2, 1, 72), MelodyNote(3, 1, 66)]
    return LeadSheet("Odd", "t", 90, (4, 4), "G", "major", 0, 1, melody,
                     [Chord(0, 0, "G"), Chord(0, 2, "C")], [])


ALL = [(i, s) for i, ss in STYLES.items() for s in ss]


@pytest.mark.parametrize("instrument,style", ALL)
@pytest.mark.parametrize("sheet", [sheet_4_4, sheet_3_4, sheet_out_of_shape])
def test_invariants_hold(instrument, style, sheet):
    arr = arrange(sheet(), instrument, style)
    check_invariants(arr)
    bars = {int(n.t // arr.sheet.bpb) for n in arr.notes}
    assert bars == set(range(arr.sheet.bars)), "every bar has notes"


def test_melody_notes_present_with_pitch_class():
    arr = arrange(sheet_4_4(), "banjo", "scruggs")
    for m in arr.sheet.melody:
        hits = [n for n in arr.notes if abs(n.t - m.t) < 1e-6 and n.melody]
        assert hits, f"melody note at {m.t} missing"
        assert arr.tuning.pitch(hits[0].string, hits[0].fret) % 12 == m.p % 12


def test_scruggs_is_eighths_and_uses_fifth_string():
    arr = arrange(sheet_4_4(), "banjo", "scruggs")
    assert all(abs((n.t * 2) - round(n.t * 2)) < 1e-9 for n in arr.notes)
    assert all(n.finger in ("T", "I", "M") for n in arr.notes)
    sparse = arrange(sheet_out_of_shape(), "banjo", "scruggs")   # quarter-note melody leaves roll slots
    assert any(n.string == 5 for n in sparse.notes)


def test_flatpick_is_melody_only():
    arr = arrange(sheet_4_4(), "guitar", "flatpick")
    assert len(arr.notes) == len(arr.sheet.melody)


def test_invariants_catch_bad_fret():
    arr = arrange(sheet_4_4(), "banjo", "scruggs")
    arr.notes.append(TabNote(0, 0.5, 5, 2))
    with pytest.raises(AssertionError):
        check_invariants(arr)


def test_fit_range_shifts_whole_phrase():
    s = sheet_4_4()
    s.melody = [MelodyNote(n.t, n.d, n.p + 24) for n in s.melody]  # two octaves up, all one phrase
    out = fit_range(s, 50, 71)
    assert all(50 <= n.p <= 71 for n in out.melody)
    assert len({n.p - o.p for n, o in zip(out.melody, s.melody)}) == 1


def test_clawhammer_frame():
    arr = arrange(sheet_4_4(), "banjo", "clawhammer")
    fifths = [n for n in arr.notes if n.string == 5]
    assert len(fifths) == 8, "one thumb on the fifth string per beat over two bars"
    assert all(abs(n.t % 1 - 0.75) < 1e-9 for n in fifths)
    assert any(n.finger == "B" for n in arr.notes)


def test_travis_alternates_bass():
    arr = arrange(sheet_4_4(), "guitar", "travis")
    bass = [n for n in arr.notes if n.finger == "p" and abs(n.t - round(n.t)) < 1e-9]
    assert len(bass) == 8
    assert bass[0].string != bass[1].string, "bass alternates strings"
    assert all(n.string <= 3 for n in arr.notes if n.melody)


def test_span_enforced_by_dropping_fill():
    from tabsmith.arrange import _enforce_span
    notes = [TabNote(0, 1, 1, 7, melody=True), TabNote(0, 1, 5, 1, "p"), TabNote(0, 1, 2, 5, "i")]
    out = _enforce_span(notes, 5)
    assert [n.fret for n in out] == [7, 5], "the fret-1 bass is dropped, the melody stays"


def test_roll_styles_survive_sixteenth_ornaments():
    s = sheet_4_4()
    s.melody = s.melody + [MelodyNote(6.75, 0.25, 64), MelodyNote(0.25, 0.25, 69)]  # 16th ornaments
    for style in ("scruggs", "clawhammer"):
        arr = arrange(s, "banjo", style)
        check_invariants(arr)
        assert all(abs(m.t * 2 - round(m.t * 2)) < 1e-9 for m in arr.sheet.melody), "melody on the 8th grid"
