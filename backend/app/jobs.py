"""One active heavy job and two waiting jobs. No silent paid restart; cancellation joins writers."""
from __future__ import annotations
import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from fastapi import HTTPException
from app import config
from app.storage import write_json
from app.pipeline import run_scan
from app.verify import run_verify


@dataclass
class Job:
    scan_id: str
    status: str = 'running'
    events: list[dict] = field(default_factory=list)
    started: float = field(default_factory=time.perf_counter)
    changed: asyncio.Event = field(default_factory=asyncio.Event)
    parent_id: str = ''
    task: asyncio.Task | None = None
    finished: float | None = None

    def emit(self, step: str, data: dict):
        self.events.append({'step': step, 't': round(time.perf_counter()-self.started, 1), **data})
        self.changed.set()
        self.changed = asyncio.Event()


JOBS: dict[str, Job] = {}
AUX_TASKS: dict[str, set[asyncio.Task]] = {}
SLOT: asyncio.Semaphore | None = None


def reset_runtime():
    global SLOT
    SLOT = asyncio.Semaphore(1)
    JOBS.clear()


def new_scan_id():
    return uuid.uuid4().hex[:12]


def busy(scan_id):
    return any((j.parent_id or j.scan_id) == scan_id and j.status in ('queued', 'running') for j in JOBS.values())


def ensure_capacity(parent_id: str | None = None):
    clean_finished()
    if sum(j.status in ('queued', 'running') for j in JOBS.values()) >= 3:
        raise HTTPException(429, 'The analysis queue is full. Keep your video and retry shortly.')
    if parent_id and busy(parent_id):
        raise HTTPException(409, 'This scan already has an active analysis. Wait for it to finish.')


def clean_finished():
    now = time.monotonic()
    for key, job in list(JOBS.items()):
        if job.finished is not None and now-job.finished > 300:
            JOBS.pop(key, None)


def _start(job_id, parent_id, work, folder):
    global SLOT
    ensure_capacity(parent_id)
    if SLOT is None:
        SLOT = asyncio.Semaphore(1)
    job = JOBS[job_id] = Job(job_id, status='queued', parent_id=parent_id)
    write_json(folder / 'job.json', {'status': 'queued', 'job_id': job_id, 'parent_id': parent_id})
    job.emit('queued', {'message': 'Waiting for the current analysis to finish.'})

    async def run():
        try:
            async with SLOT:
                job.status = 'running'
                write_json(folder / 'job.json', {'status': 'running', 'job_id': job_id, 'parent_id': parent_id})
                await work(job.emit)
                job.status = 'done'
        except asyncio.CancelledError:
            job.status = 'interrupted'
            job.emit('error', {'message': 'Analysis cancelled.'})
            raise
        except Exception as exc:
            job.status = 'error'
            message = 'The analysis failed. Please retry with a clear room video.'
            if isinstance(exc, HTTPException):
                message = str(exc.detail)
            job.emit('error', {'message': message})
            write_json(folder / 'error.json', {'message': message, 'error_type': type(exc).__name__})
        finally:
            job.finished = time.monotonic()
            job.changed.set()
    job.task = asyncio.create_task(run())
    return job


def start_scan(scan_id, src, narration):
    return _start(scan_id, scan_id, lambda emit: run_scan(src, narration, emit=emit, scan_id=scan_id),
                  config.SCANS_DIR / scan_id)


def start_verify(scan_id, verify_id, src, hazard_id=None):
    root = config.SCANS_DIR / scan_id
    return _start(verify_id, scan_id, lambda emit: run_verify(root, src, verify_id, emit, hazard_id),
                  root / 'verify' / verify_id)


async def cancel_scan(scan_id):
    tasks = []
    for job in JOBS.values():
        if (job.parent_id or job.scan_id) == scan_id and job.task and not job.task.done():
            job.task.cancel()
            tasks.append(job.task)
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    for key in [k for k, j in JOBS.items() if (j.parent_id or j.scan_id) == scan_id]:
        JOBS.pop(key, None)


async def shutdown():
    for scan_id in {j.parent_id or j.scan_id for j in list(JOBS.values())}:
        await cancel_scan(scan_id)


async def follow(job):
    sent = 0
    while True:
        waiter = job.changed
        while sent < len(job.events):
            yield job.events[sent]
            sent += 1
        if job.status not in ('running', 'queued'):
            return
        try:
            await asyncio.wait_for(waiter.wait(), 15)
        except TimeoutError:
            yield {'step': 'heartbeat', 't': round(time.perf_counter()-job.started, 1)}


def state(job_id, folder, result_file, result_key):
    result = folder / result_file
    if result.exists():
        return {'status': 'done', result_key: json.loads(result.read_text())}
    error = folder / 'error.json'
    if error.exists():
        return {'status': 'error', 'message': json.loads(error.read_text())['message']}
    job = JOBS.get(job_id)
    if job is not None and job.status in ('queued', 'running'):
        return {'status': job.status}
    return {'status': 'interrupted', 'message': 'This job was interrupted. Please submit a new attempt.'}
