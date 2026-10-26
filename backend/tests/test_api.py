import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app import config, jobs


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SCANS_DIR", tmp_path)

    async def fake_run_scan(src, narration, emit, scan_id):
        emit("ingest", {"scan_id": scan_id})
        await asyncio.sleep(0.05)
        emit("planner.done", {"concepts": ["bookshelf"], "narration": narration})
        report = {"scan_id": scan_id, "created_at": "now", "room": {"type": "bedroom", "risk_score": 25},
                  "hazards": [{"id": "h1"}]}
        (tmp_path / scan_id / "report.json").write_text(json.dumps(report))
        (tmp_path / scan_id / "evidence").mkdir()
        (tmp_path / scan_id / "evidence" / "h1.jpg").write_bytes(b"jpg")
        emit("done", {"scan_id": scan_id})

    monkeypatch.setattr(jobs, "run_scan", fake_run_scan)
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_upload_streams_timeline_then_serves_report(client):
    r = client.post("/api/scans", files={"video": ("room.mp4", b"\x00" * 10, "video/mp4")},
                    data={"narration": "kids sleep here"})
    scan_id = r.json()["scan_id"]

    with client.stream("GET", f"/api/scans/{scan_id}/events") as stream:
        events = [json.loads(line[6:]) for line in stream.iter_lines() if line.startswith("data: {\"")]
    assert [e["step"] for e in events] == ["ingest", "planner.done", "done"]
    assert events[1]["narration"] == "kids sleep here"

    assert client.get(f"/api/scans/{scan_id}").json()["report"]["room"]["risk_score"] == 25
    assert client.get(f"/api/scans/{scan_id}/files/evidence/h1.jpg").content == b"jpg"
    assert client.get("/api/scans").json()[0]["scan_id"] == scan_id


def test_rejects_non_video_and_path_escapes(client):
    assert client.post("/api/scans", files={"video": ("x.txt", b"hi", "text/plain")}).status_code == 415
    scan_id = client.post("/api/scans", files={"video": ("r.mp4", b"\x00", "video/mp4")}).json()["scan_id"]
    assert client.get(f"/api/scans/{scan_id}/files/source.mp4").status_code == 404   # raw video never served
    assert client.get(f"/api/scans/{scan_id}/files/../../etc/passwd").status_code == 404
    assert client.get("/api/scans/not-a-scan!").status_code in (400, 404)
