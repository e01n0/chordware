from pathlib import Path

from tabsmith.leadsheet import Chord, LeadSheet, MelodyNote, chord_name, parse_chord


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


from tabsmith.leadsheet import (
    Grid,
    RawNote,
    choose_capo,
    detect_key,
    notes_to_leadsheet,
    pick_melody_track,
)


def synth_song(bpm=120.0):
    """4 bars at 120 bpm: chords G C D G as piano block chords, bass roots, melody on voice."""
    spb = 60 / bpm
    notes = []
    for bar, (root, third, fifth) in enumerate([(55, 59, 62), (48, 52, 55), (50, 54, 57), (55, 59, 62)]):
        t0 = bar * 4 * spb
        for p in (root + 12, third + 12, fifth + 12):
            notes.append(RawNote("acoustic_piano", p, t0, t0 + 4 * spb))
        notes.append(RawNote("acoustic_bass", root - 12, t0, t0 + 2 * spb))
        notes.append(RawNote("acoustic_bass", fifth - 12, t0 + 2 * spb, t0 + 4 * spb))
    for i, p in enumerate([67, 69, 71, 72, 74, 76, 74, 72, 71, 69, 67, 66, 67, 71, 74, 79]):
        notes.append(RawNote("voice", p, i * spb, i * spb + spb * 0.9))
    return notes, Grid(bpm, 4, 0.0, None)


def test_extract_chords_key_melody():
    notes, grid = synth_song()
    s = notes_to_leadsheet(notes, grid, title="Synth", source="t", instrument="banjo")
    assert s.key == "G" and s.mode == "major" and s.capo == 0 and s.bars == 4
    assert [c.name for c in s.chords] == ["G", "C", "D", "G"]
    assert len(s.melody) == 16 and s.melody[0].p == 67 and abs(s.melody[1].t - 1.0) < 1e-9


def test_pickup_notes_get_their_own_bar():
    notes, grid = synth_song()
    grid = Grid(120.0, 4, 0.5, None)   # downbeat one beat late: first note is a pickup
    s = notes_to_leadsheet(notes, grid, title="S", source="t", instrument="guitar")
    assert s.melody[0].t >= 0 and s.bars == 5


def test_detect_key_minor():
    hist = [0] * 12
    for pc, w in [(9, 5), (0, 4), (4, 4), (2, 2), (7, 2), (11, 1), (5, 1)]:  # A minor
        hist[pc] = w
    assert detect_key(hist) == (9, "minor")


def test_choose_capo():
    assert choose_capo(7, "major", "banjo") == (7, 0)      # G stays
    assert choose_capo(9, "major", "banjo") == (7, 2)      # A: G shapes capo 2
    assert choose_capo(10, "major", "banjo") == (7, 3)     # Bb: capo 3
    assert choose_capo(4, "minor", "banjo") == (4, 0)      # E minor is relative of G: no capo
    assert choose_capo(1, "major", "guitar") == (0, 1)     # Db: C shapes capo 1


def test_pick_melody_track_prefers_voice_then_lead_register():
    notes, _ = synth_song()
    assert pick_melody_track(notes) == "voice"
    notes = [n for n in notes if n.instrument != "voice"] + [RawNote("acoustic_guitar", 72, 0, 1)] * 10
    assert pick_melody_track(notes) == "acoustic_guitar"
    assert pick_melody_track(notes, "acoustic_piano") == "acoustic_piano"


def test_parse_chord_is_forgiving_and_loud():
    import pytest
    assert parse_chord("Gmaj7") == (7, "maj") and parse_chord("G/B") == (7, "maj")
    assert parse_chord("Asus4") == (9, "maj") and parse_chord("Bdim") == (11, "min") and parse_chord("D9") == (2, "dom7")
    for bad in ("", "H", "Gxyz", "G#b"):
        with pytest.raises(ValueError):
            parse_chord(bad)


def test_half_bar_change_when_one_half_agrees_with_whole():
    spb = 0.5
    notes = []
    # bar 0: G for two beats then C for two beats, with bass roots; bar 1: G throughout
    for t0, (r, third, fifth) in ((0, (55, 59, 62)), (1.0, (60, 64, 67)), (2.0, (55, 59, 62)), (3.0, (55, 59, 62))):
        notes += [RawNote("acoustic_piano", p + 12, t0, t0 + 2 * spb) for p in (r, third, fifth)]
        notes.append(RawNote("acoustic_bass", r - 12, t0, t0 + 2 * spb))
    notes += [RawNote("voice", p, i * spb, i * spb + 0.4) for i, p in enumerate([67, 71, 72, 76, 67, 71, 74, 71])]
    s = notes_to_leadsheet(notes, Grid(120.0, 4, 0.0, None), title="S", source="t", instrument="banjo")
    assert [(c.bar, c.beat, c.name) for c in s.chords] == [(0, 0.0, "G"), (0, 2.0, "C"), (1, 0.0, "G")]
