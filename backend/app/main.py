"""RiskLens web API: upload a room video, stream the agent timeline (SSE), fetch the report, live voice narration.

    uv run --env-file ../.env uvicorn app.main:app --reload
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app import config, jobs
from app.meta import image, voice
from app.meta.clients import meta_client

MAX_UPLOAD_BYTES = 300 * 1024 * 1024
VIDEO_TYPES = {"video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm"}
FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "dist"
MAX_SCANS_PER_DAY = int(os.environ.get("RISKLENS_MAX_SCANS_PER_DAY", "60"))   # ≈ $15/day at ≈ $0.25/scan
MAX_SCANS_PER_IP = int(os.environ.get("RISKLENS_MAX_SCANS_PER_IP", "10"))
SCAN_LOG: dict = {"day": "", "total": 0, "per_ip": {}}

app = FastAPI(title="RiskLens")
config.SCANS_DIR.mkdir(parents=True, exist_ok=True)


def check_budget(ip: str) -> None:
    """Every scan spends Meta credit: cap scans per day overall and per client IP (public URL safety)."""
    today = time.strftime("%Y-%m-%d")
    if SCAN_LOG["day"] != today:
        SCAN_LOG.update(day=today, total=0, per_ip={})
    if SCAN_LOG["total"] >= MAX_SCANS_PER_DAY:
        raise HTTPException(429, "Daily scan limit reached. Please try again tomorrow.")
    if SCAN_LOG["per_ip"].get(ip, 0) >= MAX_SCANS_PER_IP:
        raise HTTPException(429, "Scan limit for this device reached today.")
    SCAN_LOG["total"] += 1
    SCAN_LOG["per_ip"][ip] = SCAN_LOG["per_ip"].get(ip, 0) + 1


@app.post("/api/scans")
async def create_scan(request: Request, video: UploadFile = File(...), narration: str = Form("")) -> dict:
    ip = request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "?")
    check_budget(ip)
    scan_id = jobs.new_scan_id()
    root = config.SCANS_DIR / scan_id
    src = await _save_upload(video, root)
    (root / "meta.json").write_text(json.dumps({"narration": narration, "filename": video.filename}, ensure_ascii=False))
    jobs.start_scan(scan_id, src, narration.strip() or None)
    return {"scan_id": scan_id}


@app.get("/api/scans")
def list_scans(ids: str = "") -> list[dict]:
    """Only the scans this browser created (ids it kept) plus featured demo scans: never everyone's homes."""
    featured = config.SCANS_DIR / "featured.txt"
    wanted = [i for i in ids.split(",") if i.isalnum()][:50]
    if featured.exists():
        wanted += [i for i in featured.read_text().split() if i.isalnum() and i not in wanted]
    rows = []
    for scan_id in wanted:
        report = config.SCANS_DIR / scan_id / "report.json"
        if report.exists():
            r = json.loads(report.read_text())
            rows.append({"scan_id": r["scan_id"], "created_at": r["created_at"], "room": r["room"]["type"],
                         "risk_score": r["room"]["risk_score"], "hazards": len(r["hazards"])})
    return sorted(rows, key=lambda r: r["created_at"], reverse=True)


@app.get("/api/scans/{scan_id}")
def get_scan(scan_id: str) -> dict:
    root = _scan_dir(scan_id)
    if (root / "report.json").exists():
        fixcards = sorted(p.stem for p in (root / "fixcards").glob("h*.jpg") if not p.stem.endswith("_before")) \
            if (root / "fixcards").is_dir() else []
        verification = root / "verification.json"
        return {"status": "done", "report": json.loads((root / "report.json").read_text()), "fixcards": fixcards,
                "verification": json.loads(verification.read_text()) if verification.exists() else None}
    if (root / "error.json").exists():
        return {"status": "error", **json.loads((root / "error.json").read_text())}
    return {"status": "running"}


@app.post("/api/scans/{scan_id}/verify")
async def verify_scan(scan_id: str, request: Request, video: UploadFile = File(...)) -> dict:
    """Re-filmed room after fixes -> per-hazard verdicts (job events stream under the returned verify_id)."""
    root = _scan_dir(scan_id)
    if not (root / "report.json").exists():
        raise HTTPException(409, "scan has no report yet")
    check_budget(request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "?"))
    verify_id = f"{scan_id}v{jobs.new_scan_id()[:6]}"
    src = await _save_upload(video, root / "verify" / verify_id)
    jobs.start_verify(scan_id, verify_id, src)
    return {"verify_id": verify_id}


@app.post("/api/scans/{scan_id}/hazards/{hazard_id}/fixcard")
async def make_fix_card(scan_id: str, hazard_id: str) -> dict:
    """Muse Image edit of the evidence frame showing the fix. On demand (costs $0.01) and cached per hazard."""
    root = _scan_dir(scan_id)
    out = root / "fixcards" / f"{hazard_id}.jpg"
    if not out.exists():
        report = json.loads((root / "report.json").read_text())
        hazard = next((h for h in report["hazards"] if h["id"] == hazard_id), None)
        if hazard is None:
            raise HTTPException(404, "hazard not found")
        frame = root / "frames" / f"{int(hazard['evidence_frame']):05d}.jpg"
        before = image.crop_around(frame, hazard.get("box"), root / "fixcards" / f"{hazard_id}_before.jpg")
        meta = await image.fix_card(meta_client(), before, image.fix_prompt(report["room"]["type"], hazard), out)
        (root / "fixcards" / f"{hazard_id}.json").write_text(json.dumps(meta, ensure_ascii=False))
    return {"image": f"fixcards/{hazard_id}.jpg", "before": f"fixcards/{hazard_id}_before.jpg"}


@app.get("/api/scans/{scan_id}/events")
async def scan_events(scan_id: str) -> StreamingResponse:
    job = jobs.JOBS.get(scan_id)
    if job is None:
        _scan_dir(scan_id)
        raise HTTPException(404, "no live job for this scan (finished before this server started?)")

    async def stream():
        async for event in jobs.follow(job):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/scans/{scan_id}/files/{path:path}")
def scan_file(scan_id: str, path: str) -> FileResponse:
    root = _scan_dir(scan_id).resolve()
    target = (root / path).resolve()
    if root not in target.parents or not target.is_file() or target.name.startswith("source"):
        raise HTTPException(404)
    return FileResponse(target)


@app.websocket("/api/voice")
async def voice_ws(ws: WebSocket) -> None:
    await voice.proxy(ws)


async def _save_upload(video: UploadFile, root: Path) -> Path:
    content_type = (video.content_type or "").split(";")[0]
    if content_type not in VIDEO_TYPES:     # some pickers send application/octet-stream: trust the extension
        suffix = Path(video.filename or "").suffix.lower()
        content_type = next((t for t, s in VIDEO_TYPES.items() if s == suffix), content_type)
    if content_type not in VIDEO_TYPES:
        raise HTTPException(415, f"unsupported video type {content_type!r}")
    root.mkdir(parents=True, exist_ok=True)
    src = root / f"source{VIDEO_TYPES[content_type]}"
    size = 0
    with src.open("wb") as f:
        while chunk := await video.read(1 << 20):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "video too large")
            f.write(chunk)
    return src


def _scan_dir(scan_id: str) -> Path:
    if not scan_id.isalnum():
        raise HTTPException(400, "bad scan id")
    root = config.SCANS_DIR / scan_id
    if not root.is_dir():
        raise HTTPException(404, "scan not found")
    return root


if FRONTEND.is_dir():  # production: one URL serves the built PWA too
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
