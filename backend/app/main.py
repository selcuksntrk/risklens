"""RiskLens web API: upload a room video, stream the agent timeline (SSE), fetch the report, live voice narration.

    uv run --env-file ../.env uvicorn app.main:app --reload
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app import config, jobs
from app.meta import voice

MAX_UPLOAD_BYTES = 300 * 1024 * 1024
VIDEO_TYPES = {"video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm"}
FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "dist"

app = FastAPI(title="RiskLens")
config.SCANS_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/api/scans")
async def create_scan(video: UploadFile = File(...), narration: str = Form("")) -> dict:
    content_type = (video.content_type or "").split(";")[0]
    if content_type not in VIDEO_TYPES:
        raise HTTPException(415, f"unsupported video type {content_type!r}")
    scan_id = jobs.new_scan_id()
    root = config.SCANS_DIR / scan_id
    root.mkdir(parents=True)
    src = root / f"source{VIDEO_TYPES[content_type]}"
    size = 0
    with src.open("wb") as f:
        while chunk := await video.read(1 << 20):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "video too large")
            f.write(chunk)
    (root / "meta.json").write_text(json.dumps({"narration": narration, "filename": video.filename}, ensure_ascii=False))
    jobs.start_scan(scan_id, src, narration.strip() or None)
    return {"scan_id": scan_id}


@app.get("/api/scans")
def list_scans() -> list[dict]:
    rows = []
    for report in sorted(config.SCANS_DIR.glob("*/report.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        r = json.loads(report.read_text())
        rows.append({"scan_id": r["scan_id"], "created_at": r["created_at"], "room": r["room"]["type"],
                     "risk_score": r["room"]["risk_score"], "hazards": len(r["hazards"])})
    return rows


@app.get("/api/scans/{scan_id}")
def get_scan(scan_id: str) -> dict:
    root = _scan_dir(scan_id)
    if (root / "report.json").exists():
        return {"status": "done", "report": json.loads((root / "report.json").read_text())}
    if (root / "error.json").exists():
        return {"status": "error", **json.loads((root / "error.json").read_text())}
    return {"status": "running"}


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


def _scan_dir(scan_id: str) -> Path:
    if not scan_id.isalnum():
        raise HTTPException(400, "bad scan id")
    root = config.SCANS_DIR / scan_id
    if not root.is_dir():
        raise HTTPException(404, "scan not found")
    return root


if FRONTEND.is_dir():  # production: one URL serves the built PWA too
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
