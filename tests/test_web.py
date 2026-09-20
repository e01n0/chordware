import json
from pathlib import Path

from fastapi.testclient import TestClient

from tabsmith import web
from tabsmith.leadsheet import Chord, LeadSheet, MelodyNote


def fake_pipeline(src, instrument, style, outdir, opts, progress, title=None):
    outdir = Path(outdir)
    outdir.mkdir(exist_ok=True, parents=True)
    progress("transcribe", "fake")
    progress("render", "fake")
    s = LeadSheet(title or "Fake", src, 120, (4, 4), "G", "major", 0, 1, [MelodyNote(0, 1, 67)], [Chord(0, 0, "G")], [])
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
    while not web._q.empty():  # jobs queued by earlier tests point at other tmp dirs
        web._q.get()
    return TestClient(web.app)


def test_job_lifecycle(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    r = c.post("/jobs", data={"instrument": "banjo", "style": "scruggs"},
               files={"file": ("t.mp3", b"abc", "audio/mpeg")}, headers={"accept": "application/json"})
    jid = r.json()["id"]
    web.worker_once()
    j = c.get(f"/jobs/{jid}").json()
    assert j["state"] == "done" and j["title"] == "t", "an upload keeps its own file name as the title"
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
    assert c.get("/tabsmith/").status_code == 200 and "manifest" in c.get("/tabsmith/").text
    m = c.get("/tabsmith/manifest.webmanifest").json()
    assert m["id"] == "/tabsmith-mrfantastic" and m["share_target"]["action"] == "/share"
    assert c.get("/tabsmith/sw.js").status_code == 200


def test_root_serves_chordware_when_present(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    monkeypatch.setattr(web, "CHORDWARE_DIR", tmp_path / "nowhere")
    assert c.get("/", follow_redirects=False).status_code == 302
    cw = tmp_path / "cw"
    cw.mkdir()
    (cw / "index.html").write_text("<title>CHORDWARE</title>BUILD://__BUILD__")
    (cw / "sw.js").write_text('const CACHE = "chordware-__BUILD__";')
    monkeypatch.setattr(web, "CHORDWARE_DIR", cw)
    r = c.get("/")
    assert r.status_code == 200 and "CHORDWARE" in r.text and "__BUILD__" not in r.text
    assert r.headers["cache-control"] == "no-store"
    sw = c.get("/sw.js")
    assert "__BUILD__" not in sw.text and "javascript" in sw.headers["content-type"]


def test_share_target_and_bad_capo(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    r = c.get("/share?text=look%20https://youtu.be/abc%20nice", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/tabsmith/#job/")
    r = c.post("/jobs", data={"url": "https://x/y", "instrument": "banjo", "style": "scruggs", "capo": "two"},
               headers={"accept": "application/json"})
    assert r.status_code == 400
    r = c.post("/jobs", data={"url": "https://x/y", "instrument": "banjo", "style": "travis"},
               headers={"accept": "application/json"})
    assert r.status_code == 400


def test_rearrange_rejects_bad_chord(tmp_path, monkeypatch):
    c = client(tmp_path, monkeypatch)
    jid = c.post("/jobs", data={"url": "https://e/x", "instrument": "banjo", "style": "scruggs"},
                 headers={"accept": "application/json"}).json()["id"]
    web.worker_once()
    sheet = json.loads((tmp_path / jid / "leadsheet.json").read_text())
    sheet["chords"] = [{"bar": 0, "beat": 0, "name": "Gxyz"}]
    r = c.post(f"/jobs/{jid}/rearrange", json={"leadsheet": sheet})
    assert r.status_code == 400 and "Gxyz" in r.json()["detail"]
    assert not (tmp_path / jid / "job.json.tmp").exists()
