"""Public-URL guards: daily spend caps that survive container restarts, the real client IP, and media retention.

Counters live in SCANS_DIR/_budget.json (on the Modal Volume in production). The app runs in one process and these
functions never await between reading and writing the file, so there is no race inside the event loop.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from fastapi import HTTPException, Request

from app import config

MAX_SCANS_PER_DAY = int(os.environ.get("RISKLENS_MAX_SCANS_PER_DAY", "60"))
MAX_SCANS_PER_IP = int(os.environ.get("RISKLENS_MAX_SCANS_PER_IP", "10"))
MAX_FIXCARDS_PER_DAY = int(os.environ.get("RISKLENS_MAX_FIXCARDS_PER_DAY", "100"))
MAX_USD_PER_DAY = float(os.environ.get("RISKLENS_MAX_USD_PER_DAY", "15"))
RETENTION_DAYS = int(os.environ.get("RISKLENS_RETENTION_DAYS", "7"))
TRUST_CF_HEADER = os.environ.get("RISKLENS_TRUST_CF_HEADER") == "1"   # only behind our own Cloudflare tunnel


def client_ip(request: Request) -> str:
    """The socket peer (Modal passes the real client address). A cf-connecting-ip header is client-controlled
    unless a Cloudflare tunnel we run sets it, so it is only trusted when RISKLENS_TRUST_CF_HEADER=1."""
    if TRUST_CF_HEADER and request.headers.get("cf-connecting-ip"):
        return request.headers["cf-connecting-ip"]
    return request.client.host if request.client else "?"


def _path() -> Path:
    return config.SCANS_DIR / "_budget.json"


def _load() -> dict:
    today = time.strftime("%Y-%m-%d")
    try:
        state = json.loads(_path().read_text())
    except (OSError, ValueError):
        state = {}
    if state.get("day") != today:
        state = {"day": today, "scans": 0, "per_ip": {}, "fixcards": 0, "usd": 0.0}
    return state


def _save(state: dict) -> None:
    tmp = _path().with_suffix(".tmp")
    tmp.write_text(json.dumps(state))
    tmp.replace(_path())


def charge_scan(ip: str) -> None:
    """Count one scan (or verify) for today; refuse when the daily, per-IP or dollar cap is reached."""
    state = _load()
    if state["usd"] >= MAX_USD_PER_DAY or state["scans"] >= MAX_SCANS_PER_DAY:
        raise HTTPException(429, "Daily scan limit reached. Please try again tomorrow.")
    if state["per_ip"].get(ip, 0) >= MAX_SCANS_PER_IP:
        raise HTTPException(429, "Scan limit for this device reached today.")
    state["scans"] += 1
    state["per_ip"][ip] = state["per_ip"].get(ip, 0) + 1
    _save(state)


def charge_fixcard() -> None:
    state = _load()
    if state["usd"] >= MAX_USD_PER_DAY or state["fixcards"] >= MAX_FIXCARDS_PER_DAY:
        raise HTTPException(429, "Daily image limit reached. Please try again tomorrow.")
    state["fixcards"] += 1
    _save(state)


def add_spend(usd: float) -> None:
    """Record what a finished job actually cost, so the dollar cap tracks real spend."""
    state = _load()
    state["usd"] = round(state["usd"] + usd, 4)
    _save(state)


def featured_ids() -> set[str]:
    featured = config.SCANS_DIR / "featured.txt"
    return {i for i in featured.read_text().split() if i.isalnum()} if featured.exists() else set()


def purge_old_media(now: float | None = None) -> list[str]:
    """Delete the raw video, proxy and frames of scans older than RETENTION_DAYS (featured scans are kept).
    Reports and evidence images stay so a saved link still shows the survey."""
    cutoff = (now or time.time()) - RETENTION_DAYS * 86400
    keep, purged = featured_ids(), []
    for scan in config.SCANS_DIR.iterdir():
        if not scan.is_dir() or scan.name in keep or (scan / ".purged").exists():
            continue
        created = scan / "meta.json" if (scan / "meta.json").exists() else scan   # the folder mtime moves on edits
        if created.stat().st_mtime > cutoff:
            continue
        for root in [scan, *(scan / "verify").glob("*")]:
            for item in [*root.glob("source.*"), root / "proxy.mp4", root / "frames"]:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                elif item.exists():
                    item.unlink()
        (scan / ".purged").touch()
        purged.append(scan.name)
    return purged
