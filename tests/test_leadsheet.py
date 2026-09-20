from pathlib import Path
from tabsmith.leadsheet import LeadSheet, MelodyNote, Chord, parse_chord, chord_name


def cripple_creek():
    # A part of Cripple Creek in G, 4/4, two bars, melody on 8ths
    melody = [MelodyNote(t, 0.5, p) for t, p in
              [(0, 67), (0.5, 69), (1, 71), (1.5, 74), (2, 71), (2.5, 69), (3, 67), (3.5, 64),
               (4, 62), (4.5, 64), (5, 67), (5.5, 69), (6, 67), (7, 62)]]
    chords = [Chord(0, 0, "G"), Chord(1, 0, "C"), Chord(1, 2, "G")]
    return LeadSheet("Cripple Creek", "test", 120.0, (4, 4), "G", "major", 0, 2, melody, chords, [])


def test_json_round_trip(tmp_path: Path):
    s = cripple_creek()
    p = tmp_path / "leadsheet.json"
    s.save(p)
    back = LeadSheet.load(p)
    assert back == s
    assert back.meter == (4, 4)


def test_chord_at():
    s = cripple_creek()
    assert s.chord_at(0) == "G"
    assert s.chord_at(4.5) == "C"
    assert s.chord_at(6) == "G"
    assert s.bar_of(6.5) == 1


def test_parse_and_name():
    assert parse_chord("G") == (7, "maj")
    assert parse_chord("Em") == (4, "min")
    assert parse_chord("D7") == (2, "dom7")
    assert parse_chord("Am7") == (9, "min7")
    assert parse_chord("F#m") == (6, "min")
    assert parse_chord("Bb") == (10, "maj")
    assert chord_name(6, "min") == "F#m"
    assert chord_name(0, "dom7") == "C7"
