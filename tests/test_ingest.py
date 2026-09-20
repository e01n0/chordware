import music21

from tabsmith.ingest import ingest
from tabsmith.leadsheet import Chord, LeadSheet, MelodyNote, notes_to_leadsheet


def test_audio_path(tmp_path):
    p = tmp_path / "My Song.mp3"
    p.write_bytes(b"x")
    r = ingest(str(p), tmp_path)
    assert r.audio == p and r.title == "My Song" and r.sheet is None


def test_leadsheet_json(tmp_path):
    s = LeadSheet("T", "t", 100, (4, 4), "G", "major", 0, 1, [MelodyNote(0, 1, 67)], [Chord(0, 0, "G")], [])
    p = tmp_path / "leadsheet.json"
    s.save(p)
    assert ingest(str(p), tmp_path).sheet == s


def test_midi_and_musicxml(tmp_path):
    sc = music21.stream.Score()
    mel = music21.stream.Part()
    mel.partName = "Melody"
    mel.append(music21.meter.TimeSignature("4/4"))
    mel.append(music21.tempo.MetronomeMark(number=100))
    for p in ["G4", "A4", "B4", "D5"]:
        mel.append(music21.note.Note(p, quarterLength=1))
    acc = music21.stream.Part()
    acc.partName = "Piano"
    acc.append(music21.chord.Chord(["G3", "B3", "D4"], quarterLength=4))
    sc.insert(0, mel)
    sc.insert(0, acc)
    for ext in ("mid", "musicxml"):
        f = tmp_path / f"x.{ext}"
        sc.write("midi" if ext == "mid" else "musicxml", fp=str(f))
        r = ingest(str(f), tmp_path)
        notes, grid = r.raw
        assert grid.bpm == 100 and grid.beats_per_bar == 4
        s = notes_to_leadsheet(notes, grid, title=r.title, source=str(f), instrument="banjo")
        assert [m.p for m in s.melody] == [67, 69, 71, 74] and s.chords[0].name == "G"
