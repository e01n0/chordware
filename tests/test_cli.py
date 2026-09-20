from pathlib import Path
import shutil
import pytest
from tabsmith import cli
from tabsmith.leadsheet import RawNote, Grid, LeadSheet, MelodyNote, Chord


def fake_transcribe(audio, workdir, **kw):
    spb = 0.5
    notes = [RawNote("voice", p, i * spb, i * spb + 0.45) for i, p in enumerate([67, 69, 71, 74, 71, 69, 67, 64])]
    notes += [RawNote("acoustic_piano", p, 0, 4 * spb) for p in (55, 59, 62)]
    notes += [RawNote("acoustic_piano", p, 4 * spb, 8 * spb) for p in (48, 52, 55)]
    return notes, Grid(120.0, 4, 0.0, None)


@pytest.mark.skipif(shutil.which("lilypond") is None or shutil.which("fluidsynth") is None, reason="renderers missing")
def test_pipeline_from_audio(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "transcribe", fake_transcribe)
    a = tmp_path / "tune.wav"
    a.write_bytes(b"RIFF")
    out = cli.run_pipeline(str(a), "banjo", "scruggs", tmp_path / "out", cli.Options(model="small", separate="off"))
    for k in ("leadsheet", "ly", "pdf", "png", "txt", "mid", "mp3"):
        assert out[k].exists(), k
    assert "G" in out["txt"].read_text()


def test_pipeline_from_leadsheet_skips_gpu(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "transcribe", lambda *a, **k: pytest.fail("should not transcribe"))
    monkeypatch.setattr(cli, "render_lilypond", lambda arr, d, s: (Path(d) / f"{s}.pdf", Path(d) / f"{s}.png"))
    monkeypatch.setattr(cli, "render_audio", lambda m, p: None)
    s = LeadSheet("Lead", "t", 110, (4, 4), "G", "major", 0, 1,
                  [MelodyNote(0, 1, 67), MelodyNote(2, 1, 71)], [Chord(0, 0, "G")], [])
    p = tmp_path / "leadsheet.json"
    s.save(p)
    out = cli.run_pipeline(str(p), "guitar", "travis", tmp_path / "out")
    assert out["txt"].exists() and out["mid"].exists()


def test_bad_style_rejected(tmp_path):
    with pytest.raises(ValueError):
        cli.run_pipeline("x.wav", "banjo", "travis", tmp_path)
