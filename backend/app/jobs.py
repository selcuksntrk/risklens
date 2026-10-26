"""In-process scan jobs. Each job keeps its event log so a late (or reconnecting) client can replay the timeline."""
from __future__ import annotations

import asyncio
import json
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app import config
from app.pipeline import run_scan


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


def start_scan(scan_id: str, src: Path, narration: str | None) -> Job:
    job = JOBS[scan_id] = Job(scan_id)

    async def run() -> None:
        try:
            await run_scan(src, narration, emit=job.emit, scan_id=scan_id)
            job.status = "done"
        except Exception as exc:  # surface the failure in the timeline instead of a silent dead job
            traceback.print_exc()
            job.status = "error"
            job.emit("error", {"message": str(exc)[:500]})
            (config.SCANS_DIR / scan_id / "error.json").write_text(json.dumps({"message": str(exc)}))

    asyncio.get_running_loop().create_task(run())
    return job


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
