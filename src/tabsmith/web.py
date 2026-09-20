"""FastAPI web app: upload or URL in, job queue (one GPU, one worker), results + chord editor, PWA."""
from __future__ import annotations

import json
import os
import queue
import re
import threading
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from .arrange import STYLES
from .cli import Options, run_pipeline
from .ingest import AUDIO_EXT, SCORE_EXT
from .leadsheet import LeadSheet

JOBS_DIR = Path(os.environ.get("TABSMITH_JOBS", Path.home() / "tabsmith/jobs"))
STATIC = Path(__file__).parent / "static"
MAX_UPLOAD = 200 * 1024 * 1024
DEFAULT_OPTS = {"model": "large", "separate": "auto", "refine": False, "key": None, "capo": None}
app = FastAPI(title="tabsmith")
_q: queue.Queue[str] = queue.Queue()
_lock = threading.Lock()


def _path(jid: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{12}", jid):
        raise HTTPException(404)
    return JOBS_DIR / jid


def _read(jid: str) -> dict:
    p = _path(jid) / "job.json"
    if not p.exists():
        raise HTTPException(404)
    return json.loads(p.read_text())


def _write(job: dict) -> None:
    with _lock:
        (JOBS_DIR / job["id"] / "job.json").write_text(json.dumps(job))


def _new_job(jid: str, src: str, title: str, instrument: str, style: str, opts: dict) -> str:
    if style not in STYLES.get(instrument, ()):
        raise HTTPException(400, f"{instrument} styles: {STYLES.get(instrument)}")
    (JOBS_DIR / jid).mkdir(parents=True, exist_ok=True)
    _write({"id": jid, "src": src, "title": title, "instrument": instrument, "style": style, "opts": opts,
            "state": "queued", "log": [], "error": None, "created": time.time(), "files": {}})
    _q.put(jid)
    return jid


def worker_once(block: bool = False) -> None:
    try:
        jid = _q.get(block=block)
    except queue.Empty:
        return
    job = _read(jid)

    def progress(stage: str, msg: str) -> None:
        job["state"] = {"transcribe": "transcribing", "arrange": "arranging", "refine": "arranging",
                        "render": "rendering"}.get(stage, job["state"])
        if "GPU busy" in msg:
            job["state"] = "waiting_gpu"
        job["log"].append(f"{time.strftime('%H:%M:%S')} [{stage}] {msg}")
        _write(job)

    try:
        job["state"] = "transcribing"
        _write(job)
        out = run_pipeline(job["src"], job["instrument"], job["style"], JOBS_DIR / jid, Options(**job["opts"]), progress)
        job["files"] = {k: v.name for k, v in out.items()}
        job["title"] = LeadSheet.load(out["leadsheet"]).title
        job["state"] = "done"
    except Exception as e:  # any failure is the job's failure; the worker must survive
        job["state"], job["error"] = "failed", f"{e.__class__.__name__}: {e}"
    _write(job)


def _worker_loop() -> None:
    while True:
        worker_once(block=True)


@asynccontextmanager
async def _lifespan(_app):
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    for p in sorted(JOBS_DIR.glob("*/job.json")):  # requeue anything interrupted by a restart
        j = json.loads(p.read_text())
        if j["state"] not in ("done", "failed"):
            _q.put(j["id"])
    threading.Thread(target=_worker_loop, daemon=True).start()
    yield


app.router.lifespan_context = _lifespan


def _wants_html(req: Request) -> bool:
    return "text/html" in req.headers.get("accept", "")


@app.post("/jobs")
async def create_job(req: Request, file: UploadFile | None = File(None), url: str = Form(""),
                     instrument: str = Form("banjo"), style: str = Form(""), separate: str = Form("auto"),
                     refine: str = Form("0"), key: str = Form(""), capo: str = Form(""), model: str = Form("large")):
    style = style or STYLES[instrument][0]
    opts = {"model": model, "separate": separate, "refine": refine == "1", "key": key or None,
            "capo": int(capo) if capo else None}
    jid = uuid.uuid4().hex[:12]
    if file and file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in AUDIO_EXT | SCORE_EXT | {".json"}:
            raise HTTPException(400, f"unsupported file type {ext}")
        data = await file.read()
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "file too large")
        (JOBS_DIR / jid).mkdir(parents=True, exist_ok=True)
        src = JOBS_DIR / jid / f"input{ext}"
        src.write_bytes(data)
        title = Path(file.filename).stem
    elif url.startswith(("http://", "https://")):
        src, title = url, url
    else:
        raise HTTPException(400, "upload a file or give a URL")
    _new_job(jid, str(src), title, instrument, style, opts)
    return RedirectResponse(f"/#job/{jid}", status_code=303) if _wants_html(req) else {"id": jid}


@app.get("/jobs")
def list_jobs():
    jobs = [json.loads(p.read_text()) for p in JOBS_DIR.glob("*/job.json")]
    jobs.sort(key=lambda j: -j["created"])
    return [{k: j[k] for k in ("id", "title", "instrument", "style", "state", "created")} for j in jobs[:50]]


@app.get("/jobs/{jid}")
def get_job(jid: str):
    return _read(jid)


@app.get("/jobs/{jid}/{name}")
def get_file(jid: str, name: str):
    p = _path(jid) / name
    if "/" in name or ".." in name or not p.is_file():
        raise HTTPException(404)
    return FileResponse(p)


@app.post("/jobs/{jid}/rearrange")
def rearrange(jid: str, body: dict):
    old = _read(jid)
    sheet = LeadSheet.from_json(json.dumps(body["leadsheet"]))
    sheet.chords.sort(key=lambda c: (c.bar, c.beat))
    instrument, style = body.get("instrument", old["instrument"]), body.get("style", old["style"])
    new = uuid.uuid4().hex[:12]
    (JOBS_DIR / new).mkdir(parents=True)
    src = JOBS_DIR / new / "input.json"
    sheet.save(src)
    opts = dict(old["opts"])
    opts["refine"] = bool(body.get("refine", False))
    return {"id": _new_job(new, str(src), sheet.title, instrument, style, opts)}


@app.api_route("/share", methods=["GET", "POST"])
async def share(req: Request):
    form = await req.form() if req.method == "POST" else req.query_params
    m = re.search(r"https?://\S+", " ".join(str(form.get(k) or "") for k in ("url", "text", "title")))
    if not m:
        raise HTTPException(400, "share a link")
    jid = _new_job(uuid.uuid4().hex[:12], m.group(0), m.group(0), "banjo", "scruggs", dict(DEFAULT_OPTS))
    return RedirectResponse(f"/#job/{jid}", status_code=303)


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "index.html").read_text()


@app.get("/manifest.webmanifest")
def manifest():
    return JSONResponse(json.loads((STATIC / "manifest.webmanifest").read_text()),
                        media_type="application/manifest+json")


@app.get("/sw.js")
def sw():
    return FileResponse(STATIC / "sw.js", media_type="application/javascript")


@app.get("/icon-{size}.png")
def icon(size: int):
    p = STATIC / f"icon-{size}.png"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


def main() -> None:
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("TABSMITH_PORT", 8092)))
