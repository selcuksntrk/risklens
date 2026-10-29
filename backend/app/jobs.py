"""In-process scan jobs. Each job keeps its event log so a late (or reconnecting) client can replay the timeline."""
from __future__ import annotations

import asyncio
import json
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app import config, guard
from app.pipeline import run_scan
from app.verify import run_verify


@dataclass
class Job:
    scan_id: str
    status: str = "running"                 # running | done | error
    events: list[dict] = field(default_factory=list)
    started: float = field(default_factory=time.perf_counter)
    changed: asyncio.Event = field(default_factory=asyncio.Event)

    def emit(self, step: str, data: dict) -> None:
        self.events.append({"step": step, "t": round(time.perf_counter() - self.started, 1), **data})
        self.changed.set()                  # wake every waiting subscriber; they re-arm with a fresh Event
        self.changed = asyncio.Event()


JOBS: dict[str, Job] = {}


def new_scan_id() -> str:
    return uuid.uuid4().hex[:12]


def _start(job_id: str, work, error_dir: Path) -> Job:
    job = JOBS[job_id] = Job(job_id)

    async def run() -> None:
        try:
            result = await work(job.emit)
            cost = result.get("cost_usd", 0) if isinstance(result, dict) else 0
            guard.add_spend(cost["total"] if isinstance(cost, dict) else cost)
            job.status = "done"
        except Exception as exc:  # surface the failure in the timeline instead of a silent dead job
            traceback.print_exc()
            job.status = "error"
            message = f"The scan failed ({type(exc).__name__}). Please try again."   # details stay server-side
            job.emit("error", {"message": message})
            error_dir.mkdir(parents=True, exist_ok=True)
            (error_dir / "error.json").write_text(json.dumps({"message": message, "detail": str(exc)[:2000]}))

    asyncio.get_running_loop().create_task(run())
    return job


def start_scan(scan_id: str, src: Path, narration: str | None) -> Job:
    return _start(scan_id, lambda emit: run_scan(src, narration, emit=emit, scan_id=scan_id),
                  config.SCANS_DIR / scan_id)


def start_verify(scan_id: str, verify_id: str, src: Path) -> Job:
    root = config.SCANS_DIR / scan_id
    return _start(verify_id, lambda emit: run_verify(root, src, verify_id, emit), root / "verify" / verify_id)


async def follow(job: Job):
    """Yield every event so far, then new ones as they arrive, until the job ends."""
    sent = 0
    while True:
        waiter = job.changed
        while sent < len(job.events):
            yield job.events[sent]
            sent += 1
        if job.status != "running":
            return
        await waiter.wait()
