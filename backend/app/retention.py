"""Timestamp-based retention. Verification age is independent of its parent scan's raw media."""
import json
import shutil
import time
from pathlib import Path
from app import config, guard
from app.storage import durable


def created(root: Path) -> float:
    try:
        return float(json.loads((root / 'meta.json').read_text())['created_at_unix'])
    except (OSError, ValueError, KeyError, TypeError):
        anchor = root / 'meta.json'
        return (anchor if anchor.exists() else root).stat().st_mtime


def raw_expired(root: Path, now=None) -> bool:
    return (time.time() if now is None else now) - created(root) >= guard.RETENTION_DAYS * 86400


def report_expired(root: Path, now=None) -> bool:
    # Legacy records are quarantined rather than silently deleted by a new policy.
    try:
        meta = json.loads((root / 'meta.json').read_text())
        if 'created_at_unix' not in meta:
            return False
    except (OSError, ValueError):
        return False
    return (time.time() if now is None else now) - created(root) >= guard.REPORT_RETENTION_DAYS * 86400


def purge(now=None) -> list[str]:
    from app import jobs
    purged = []
    for root in config.SCANS_DIR.iterdir():
        if not root.is_dir() or root.name.startswith('_') or root.name in guard.featured_ids():
            continue
        if jobs.busy(root.name) or jobs.AUX_TASKS.get(root.name):
            continue
        if report_expired(root, now):
            shutil.rmtree(root)
            purged.append(root.name)
            continue
        changed = False
        for folder in [root, *(root / 'verify').glob('*')]:
            if not folder.is_dir() or not raw_expired(folder, now):
                continue
            for item in [*folder.glob('source.*'), folder / 'proxy.mp4', folder / 'frames']:
                if item.is_dir():
                    shutil.rmtree(item)
                    changed = True
                elif item.exists():
                    item.unlink()
                    changed = True
        if changed:
            purged.append(root.name)
    if purged:
        durable()
    return purged
