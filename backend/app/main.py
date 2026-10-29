"""RiskLens web API: upload a room video, stream the agent timeline (SSE), fetch the report, live voice narration.

    uv run --env-file ../.env uvicorn app.main:app --reload
"""
from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app import config, guard, jobs
from app.meta import image, voice
from app.meta.clients import meta_client

MAX_UPLOAD_BYTES = 300 * 1024 * 1024
VIDEO_TYPES = {"video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm"}
FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "dist"
SERVED_DIRS = {"evidence", "marked", "fixcards"}     # plus verify/<id>/after; never source, proxy or raw frames
FIXCARD_LOCKS: dict[str, asyncio.Lock] = {}

app = FastAPI(title="RiskLens")
config.SCANS_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/api/scans")
async def create_scan(request: Request, video: UploadFile = File(...), narration: str = Form("")) -> dict:
    guard.purge_old_media()
    scan_id = jobs.new_scan_id()
    root = config.SCANS_DIR / scan_id
    src = await _save_upload(video, root, guard.client_ip(request))
    (root / "meta.json").write_text(json.dumps({"narration": narration, "filename": video.filename}, ensure_ascii=False))
    jobs.start_scan(scan_id, src, narration.strip() or None)
    return {"scan_id": scan_id}


@app.get("/api/scans")
def list_scans(ids: str = "") -> list[dict]:
    """Only the scans this browser created (ids it kept) plus featured demo scans: never everyone's homes."""
    wanted = [i for i in ids.split(",") if i.isalnum()][:50]
    wanted += sorted(guard.featured_ids() - set(wanted))
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
    if (root / "error.json").exists():   # the stored detail stays server-side
        return {"status": "error", "message": json.loads((root / "error.json").read_text())["message"]}
    return {"status": "running"}


@app.post("/api/scans/{scan_id}/verify")
async def verify_scan(scan_id: str, request: Request, video: UploadFile = File(...)) -> dict:
    """Re-filmed room after fixes -> per-hazard verdicts (job events stream under the returned verify_id)."""
    root = _scan_dir(scan_id)
    if not (root / "report.json").exists():
        raise HTTPException(409, "scan has no report yet")
    verify_id = f"{scan_id}v{jobs.new_scan_id()[:6]}"
    src = await _save_upload(video, root / "verify" / verify_id, guard.client_ip(request))
    jobs.start_verify(scan_id, verify_id, src)
    return {"verify_id": verify_id}


@app.post("/api/scans/{scan_id}/hazards/{hazard_id}/fixcard")
async def make_fix_card(scan_id: str, hazard_id: str) -> dict:
    """Muse Image edit of the evidence frame showing the fix. On demand (costs $0.01) and cached per hazard."""
    root = _scan_dir(scan_id)
    if not (root / "report.json").exists():
        raise HTTPException(409, "scan has no report yet")
    out = root / "fixcards" / f"{hazard_id}.jpg"
    lock = FIXCARD_LOCKS.setdefault(f"{scan_id}/{hazard_id}", asyncio.Lock())
    async with lock:                         # two taps must not pay for two images
        if not out.exists():
            report = json.loads((root / "report.json").read_text())
            hazard = next((h for h in report["hazards"] if h["id"] == hazard_id), None)
            if hazard is None:
                raise HTTPException(404, "hazard not found")
            frame = root / "frames" / f"{int(hazard['evidence_frame']):05d}.jpg"
            if not frame.exists():
                raise HTTPException(410, f"Video frames are deleted after {guard.RETENTION_DAYS} days.")
            guard.charge_fixcard()
            before = image.crop_around(frame, hazard.get("box"), root / "fixcards" / f"{hazard_id}_before.jpg")
            try:
                meta = await image.fix_card(meta_client(), before, image.fix_prompt(report["room"]["type"], hazard),
                                            out)
            except image.ImageRefused as exc:
                raise HTTPException(422, str(exc)) from exc
            guard.add_spend(meta["cost_usd"])
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
    if root not in target.parents or not target.is_file() or not _servable(target.relative_to(root).parts):
        raise HTTPException(404)
    return FileResponse(target)


@app.websocket("/api/voice")
async def voice_ws(ws: WebSocket) -> None:
    await voice.proxy(ws)


def _servable(parts: tuple[str, ...]) -> bool:
    """Evidence, marked keyframes, fix cards and verify 'after' images only: never the video or raw frames."""
    return (len(parts) == 2 and parts[0] in SERVED_DIRS) or (len(parts) == 4 and parts[0] == "verify"
                                                              and parts[2] == "after")


async def _save_upload(video: UploadFile, root: Path, ip: str) -> Path:
    """Validate and store the upload, then charge the daily budget (rejected files never use up quota)."""
    content_type = (video.content_type or "").split(";")[0]
    if content_type not in VIDEO_TYPES:     # some pickers send application/octet-stream: trust the extension
        suffix = Path(video.filename or "").suffix.lower()
        content_type = next((t for t, s in VIDEO_TYPES.items() if s == suffix), content_type)
    if content_type not in VIDEO_TYPES:
        raise HTTPException(415, f"unsupported video type {content_type!r}")
    root.mkdir(parents=True, exist_ok=True)
    src = root / f"source{VIDEO_TYPES[content_type]}"
    size = 0
    try:
        with src.open("wb") as f:
            while chunk := await video.read(1 << 20):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "video too large")
                f.write(chunk)
        guard.charge_scan(ip)
    except HTTPException:
        shutil.rmtree(root, ignore_errors=True)
        raise
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
