"""RiskLens on Modal: one live URL serving the API, the SSE agent timeline, the voice proxy and the PWA build.

    (cd frontend && npm run build) && modal deploy deploy/modal_app.py
    RISKLENS_MIN_CONTAINERS=1 modal deploy deploy/modal_app.py      # judging window: no cold starts

Jobs and their event logs live in process memory, so the app runs in a single container that handles many
concurrent requests. Scans (reports, evidence, fix cards) persist on a Modal Volume.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]
REMOTE = "/root/risklens"
SCANS = "/data/scans"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg")
    .pip_install_from_pyproject(str(ROOT / "backend" / "pyproject.toml"))
    .env({"RISKLENS_SCANS": SCANS})
    .add_local_dir(ROOT / "backend" / "app", f"{REMOTE}/backend/app", ignore=["**/__pycache__"])
    .add_local_dir(ROOT / "frontend" / "dist", f"{REMOTE}/frontend/dist")
)
scans = modal.Volume.from_name("risklens-scans", create_if_missing=True)
app = modal.App("risklens")


@app.function(image=image, volumes={SCANS: scans}, secrets=[modal.Secret.from_name("risklens-meta")],
              cpu=1.0, memory=2048, max_containers=1, scaledown_window=1200, timeout=3600,
              min_containers=int(os.environ.get("RISKLENS_MIN_CONTAINERS", "0")))
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def web():
    sys.path.insert(0, f"{REMOTE}/backend")
    from app.main import app as fastapi_app
    return fastapi_app
