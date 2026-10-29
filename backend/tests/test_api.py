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
    from app import main
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
    assert client.get(f"/api/scans?ids={scan_id}").json()[0]["scan_id"] == scan_id
    assert client.get("/api/scans").json() == []          # other people's scans are never listed


def test_rejects_non_video_and_path_escapes(client):
    assert client.post("/api/scans", files={"video": ("x.txt", b"hi", "text/plain")}).status_code == 415
    assert client.post("/api/scans", files={"video": ("x.bin", b"hi", "application/octet-stream")}).status_code == 415
    assert client.post("/api/scans", files={"video": ("room.MOV", b"\x00", "application/octet-stream")}).status_code == 200
    scan_id = client.post("/api/scans", files={"video": ("r.mp4", b"\x00", "video/mp4")}).json()["scan_id"]
    assert client.get(f"/api/scans/{scan_id}/files/source.mp4").status_code == 404   # raw video never served
    assert client.get(f"/api/scans/{scan_id}/files/../../etc/passwd").status_code == 404
    assert client.get("/api/scans/not-a-scan!").status_code in (400, 404)


def test_scan_budget_per_ip_ignores_spoofed_header_and_survives_restart(client, monkeypatch):
    from app import guard
    monkeypatch.setattr(guard, "MAX_SCANS_PER_IP", 1)
    ok = client.post("/api/scans", files={"video": ("r.mp4", b"\x00", "video/mp4")})
    spoofed = client.post("/api/scans", files={"video": ("r.mp4", b"\x00", "video/mp4")},
                          headers={"cf-connecting-ip": "1.2.3.4"})
    assert ok.status_code == 200 and spoofed.status_code == 429
    assert guard._load()["scans"] == 1                    # counted on disk, not in process memory


def test_rejected_upload_uses_no_quota_and_dollar_cap_blocks(client):
    from app import guard
    client.post("/api/scans", files={"video": ("x.txt", b"hi", "text/plain")})
    assert guard._load()["scans"] == 0
    guard.add_spend(guard.MAX_USD_PER_DAY)
    assert client.post("/api/scans", files={"video": ("r.mp4", b"\x00", "video/mp4")}).status_code == 429


def test_only_evidence_images_are_served(client, tmp_path):
    scan_id = client.post("/api/scans", files={"video": ("r.mp4", b"\x00", "video/mp4")}).json()["scan_id"]
    root = tmp_path / scan_id
    for rel in ["proxy.mp4", "frames/00001.jpg", "marked/00001.jpg", "verify/abcv1/after/h1.jpg",
                "verify/abcv1/proxy.mp4"]:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(b"x")
    get = lambda rel: client.get(f"/api/scans/{scan_id}/files/{rel}").status_code
    assert get("proxy.mp4") == get("frames/00001.jpg") == get("verify/abcv1/proxy.mp4") == 404
    assert get("marked/00001.jpg") == get("verify/abcv1/after/h1.jpg") == 200


def test_fixcard_needs_a_report(client, tmp_path):
    (tmp_path / "abc123").mkdir()
    assert client.post("/api/scans/abc123/hazards/h1/fixcard").status_code == 409


def test_purge_keeps_reports_and_featured_scans(tmp_path, monkeypatch):
    import os
    from app import config, guard
    monkeypatch.setattr(config, "SCANS_DIR", tmp_path)
    for scan in ("old", "fresh", "feat"):
        (tmp_path / scan / "frames").mkdir(parents=True)
        for name in ("source.mp4", "proxy.mp4", "report.json", "meta.json", "frames/00001.jpg"):
            (tmp_path / scan / name).write_bytes(b"x")
    (tmp_path / "featured.txt").write_text("feat")
    for scan in ("old", "feat"):
        os.utime(tmp_path / scan / "meta.json", (0, 1_000_000))
    assert guard.purge_old_media(now=1_000_000 + 8 * 86400) == ["old"]
    assert not (tmp_path / "old" / "source.mp4").exists() and not (tmp_path / "old" / "frames").exists()
    assert (tmp_path / "old" / "report.json").exists() and (tmp_path / "feat" / "source.mp4").exists()


def test_voice_proxy_rejects_other_origins(client):
    from starlette.websockets import WebSocketDisconnect
    for headers in ({}, {"origin": "https://evil.example"}):
        with pytest.raises(WebSocketDisconnect) as closed:
            with client.websocket_connect("/api/voice", headers=headers) as ws:
                ws.receive_text()
        assert closed.value.code == 1008


def test_scan_without_a_live_job_reports_interrupted(client, tmp_path):
    (tmp_path / "abc123").mkdir()
    state = client.get("/api/scans/abc123").json()
    assert state["status"] == "error" and "interrupted" in state["message"]
