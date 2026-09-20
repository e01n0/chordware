import json
from pathlib import Path
from fastapi.testclient import TestClient
from tabsmith import web
from tabsmith.leadsheet import LeadSheet, MelodyNote, Chord


def fake_pipeline(src, instrument, style, outdir, opts, progress):
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True, parents=True)
    progress("transcribe", "fake")
    progress("render", "fake")
    s = LeadSheet("Fake", src, 120, (4, 4), "G", "major", 0, 1, [MelodyNote(0, 1, 67)], [Chord(0, 0, "G")], [])
    s.save(outdir / "leadsheet.json")
    files = {}
    for k in ("txt", "pdf", "png", "mid", "mp3", "ly"):
        (outdir / f"fake.{k}").write_bytes(b"x")
        files[k] = outdir / f"fake.{k}"
    files["leadsheet"] = outdir / "leadsheet.json"
    return files


def client(tmp_path, monkeypatch):
    monkeypatch.setattr(web, "run_pipeline", fake_pipeline)
    monkeypatch.setattr(web, "JOBS_DIR", tmp_path)
    return TestClient(web.app)


def test_job_lifecycle(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    r = c.post("/jobs", data={"instrument": "banjo", "style": "scruggs"},
               files={"file": ("t.mp3", b"abc", "audio/mpeg")}, headers={"accept": "application/json"})
    jid = r.json()["id"]
    web.worker_once()
    j = c.get(f"/jobs/{jid}").json()
    assert j["state"] == "done" and j["title"] == "Fake"
    assert c.get(f"/jobs/{jid}/fake.txt").content == b"x"
    assert c.get("/jobs").json()[0]["id"] == jid
    assert c.get(f"/jobs/{jid}/..%2F..%2Fetc%2Fpasswd").status_code in (400, 404)


def test_rearrange_creates_new_job(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    jid = c.post("/jobs", data={"url": "https://example.com/x", "instrument": "guitar", "style": "travis"},
                 headers={"accept": "application/json"}).json()["id"]
    web.worker_once()
    sheet = json.loads((tmp_path / jid / "leadsheet.json").read_text())
    sheet["chords"] = [{"bar": 0, "beat": 0, "name": "Em"}]
    r = c.post(f"/jobs/{jid}/rearrange", json={"leadsheet": sheet, "instrument": "banjo", "style": "clawhammer", "refine": False})
    new = r.json()["id"]
    assert new != jid
    web.worker_once()
    assert c.get(f"/jobs/{new}").json()["state"] == "done"
    assert json.loads((tmp_path / new / "input.json").read_text())["chords"][0]["name"] == "Em"


def test_rejects_bad_upload(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    r = c.post("/jobs", data={"instrument": "banjo", "style": "scruggs"},
               files={"file": ("evil.exe", b"MZ", "application/octet-stream")}, headers={"accept": "application/json"})
    assert r.status_code == 400


def test_pwa_assets(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    assert c.get("/").status_code == 200 and "manifest" in c.get("/").text
    m = c.get("/manifest.webmanifest").json()
    assert m["id"] == "/tabsmith-mrfantastic" and m["share_target"]["action"] == "/share"
    assert c.get("/sw.js").status_code == 200
