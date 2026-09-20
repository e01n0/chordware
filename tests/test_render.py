import shutil

import pytest

from tabsmith.arrange import Arrangement, TabNote, arrange
from tabsmith.fretboard import BANJO_G
from tabsmith.leadsheet import Chord, LeadSheet, MelodyNote
from tabsmith.render import (
    ascii_tab,
    lilypond_source,
    render_lilypond,
    slugify,
    write_midi,
)


def two_bar():
    melody = [MelodyNote(0, 1, 67), MelodyNote(1, 1, 71), MelodyNote(2, 2, 74), MelodyNote(4, 4, 72)]
    return LeadSheet("Test Tune", "t", 120, (4, 4), "G", "major", 2, 2, melody,
                     [Chord(0, 0, "G"), Chord(1, 0, "C")], [])


def test_ascii_shape():
    txt = ascii_tab(arrange(two_bar(), "guitar", "flatpick"))
    lines = txt.splitlines()
    assert lines[0].strip().startswith("G") and "C" in lines[0]  # chord line
    assert [l[0] for l in lines[1:7]] == ["e", "B", "G", "D", "A", "E"]
    assert lines[1].count("|") == 3                              # start, bar, end
    body = "\n".join(lines[1:7])
    assert "0" in body and "-" in body


def test_ascii_banjo_has_five_strings():
    lines = ascii_tab(arrange(two_bar(), "banjo", "scruggs")).splitlines()
    assert [l[0] for l in lines[1:6]] == ["d", "B", "G", "D", "g"]


def test_lilypond_source_mentions_tuning_and_strings():
    src = lilypond_source(arrange(two_bar(), "banjo", "scruggs"))
    assert "banjo-open-g-tuning" in src and "\\5" in src and "\\time 4/4" in src and "Capo 2" in src


def test_midi_written(tmp_path):
    p = tmp_path / "x.mid"
    write_midi(arrange(two_bar(), "guitar", "travis"), p)
    assert p.stat().st_size > 50


@pytest.mark.skipif(shutil.which("lilypond") is None, reason="lilypond not installed")
def test_lilypond_compiles(tmp_path):
    pdf, png = render_lilypond(arrange(two_bar(), "banjo", "clawhammer"), tmp_path, "t")
    assert pdf.exists() and png.exists()


def test_slugify():
    assert slugify("Cripple Creek (live) ") == "cripple-creek-live"


def test_tech_in_ascii_and_ly():
    s = two_bar()
    arr = Arrangement("banjo", "scruggs", BANJO_G, s,
                      [TabNote(0, 0.5, 1, 0, "M", "h", True), TabNote(0.5, 0.5, 1, 2, "M", "", True)])
    assert "0h" in ascii_tab(arr)
    assert "(" in lilypond_source(arr)


def test_title_with_quotes_is_escaped():
    s = two_bar()
    s.title = 'Bob - "Don\'t" \\ Twice'
    src = lilypond_source(arrange(s, "guitar", "flatpick"))
    assert 'title = "Bob - \\"Don\'t\\" \\\\ Twice"' in src


def test_lilypond_handles_forgiving_chord_names():
    s = two_bar()
    s.chords = [Chord(0, 0, "G/B"), Chord(1, 0, "Csus4")]
    src = lilypond_source(arrange(s, "banjo", "scruggs"))
    assert "g1" in src and "c1" in src
