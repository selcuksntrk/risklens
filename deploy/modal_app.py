"""RiskLens on Modal: one live URL serving the API, the SSE agent timeline, the voice proxy and the PWA build.

    (cd frontend && npm run build) && modal deploy deploy/modal_app.py
    RISKLENS_MIN_CONTAINERS=1 modal deploy deploy/modal_app.py      # judging window: no cold starts

Jobs and their event logs live in process memory, so the app runs in a single container that handles many
concurrent requests. Scans (reports, evidence, fix cards) persist on a Modal Volume.
"""
from __future__ import annotations

import os
import json
import hashlib
import runpy
import sys
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]
REMOTE = "/root/risklens"
SCANS = "/data/scans"
VERSION = os.environ.get('RISKLENS_VERSION', 'development')
if modal.is_local():
    VERSION = (ROOT / 'VERSION').read_text().strip()
    manifest = json.loads((ROOT / 'release.json').read_text())
    expected = runpy.run_path(str(ROOT / 'scripts/build_release.py'))['release_id']()
    if manifest['version'] != expected or (ROOT / 'VERSION').read_text().strip() != expected:
        raise RuntimeError('Sources changed after release build. Run scripts/build_release.py again.')
    for relative, digest in manifest['assets'].items():
        if hashlib.sha256((ROOT / 'frontend/dist' / relative).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Frontend assets do not match the release manifest.')

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg")
    .pip_install_from_requirements(str(ROOT / "deploy" / "requirements.txt"))
    .env({"RISKLENS_SCANS": SCANS, "RISKLENS_COOKIE_SECURE": "1",
          "RISKLENS_VERSION": VERSION})
    .add_local_dir(ROOT / "backend" / "app", f"{REMOTE}/backend/app", ignore=["**/__pycache__"])
    .add_local_dir(ROOT / "frontend" / "dist", f"{REMOTE}/frontend/dist")
    .add_local_dir(ROOT / "examples" / "generated", f"{REMOTE}/examples/generated")
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
    from app import storage
    storage.COMMIT = scans.commit
    from app.main import app as fastapi_app
    return fastapi_app
