"""Single-container, lock-protected quotas and call-level reservations persisted across restarts."""
from __future__ import annotations
import json
import os
import secrets
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request
from app import config
from app.storage import write_json

MAX_SCANS_PER_DAY = int(os.environ.get('RISKLENS_MAX_SCANS_PER_DAY', '60'))
MAX_SCANS_PER_IP = int(os.environ.get('RISKLENS_MAX_SCANS_PER_IP', '10'))
MAX_FIXCARDS_PER_DAY = int(os.environ.get('RISKLENS_MAX_FIXCARDS_PER_DAY', '100'))
MAX_USD_PER_DAY = float(os.environ.get('RISKLENS_MAX_USD_PER_DAY', '15'))
RETENTION_DAYS = int(os.environ.get('RISKLENS_RETENTION_DAYS', '7'))
REPORT_RETENTION_DAYS = int(os.environ.get('RISKLENS_REPORT_RETENTION_DAYS', '30'))
TRUST_CF_HEADER = os.environ.get('RISKLENS_TRUST_CF_HEADER') == '1'
LOCK = threading.RLock()
CALLS: ContextVar[tuple[list, Path] | None] = ContextVar('model_calls', default=None)


def client_ip(request: Request) -> str:
    if TRUST_CF_HEADER and request.headers.get('cf-connecting-ip'):
        return request.headers['cf-connecting-ip']
    return request.client.host if request.client else '?'


def _path():
    return config.SCANS_DIR / '_budget.json'


def _load() -> dict:
    today = datetime.now(ZoneInfo('Europe/Istanbul')).date().isoformat()
    try:
        state = json.loads(_path().read_text())
    except FileNotFoundError:
        state = {}
    except (OSError, ValueError) as exc:
        raise HTTPException(503, 'Budget ledger unavailable; try again later.') from exc
    if state.get('day') != today:
        # Pending calls straddling midnight remain reserved; never silently refund unknown charges.
        state = {'day': today, 'scans': 0, 'per_ip': {}, 'fixcards': 0, 'usd': 0.0,
                 'reservations': state.get('reservations', {}), 'unknown_usd': 0.0}
    state.setdefault('reservations', {})
    state.setdefault('unknown_usd', 0.0)
    return state


def _save(state):
    write_json(_path(), state)


def available(state) -> float:
    return MAX_USD_PER_DAY - state['usd'] - sum(r['amount'] for r in state['reservations'].values())


def charge_scan(ip: str):
    with LOCK:
        state = _load()
        if available(state) <= 0 or state['scans'] >= MAX_SCANS_PER_DAY:
            raise HTTPException(429, 'Daily scan budget reached. Please try again tomorrow (Istanbul time).')
        if state['per_ip'].get(ip, 0) >= MAX_SCANS_PER_IP:
            raise HTTPException(429, 'Daily scan limit for this network reached.')
        state['scans'] += 1
        state['per_ip'][ip] = state['per_ip'].get(ip, 0) + 1
        _save(state)


def charge_fixcard():
    with LOCK:
        state = _load()
        if available(state) <= 0 or state['fixcards'] >= MAX_FIXCARDS_PER_DAY:
            raise HTTPException(429, 'Daily illustration limit reached.')
        state['fixcards'] += 1
        _save(state)


def add_spend(usd: float):
    with LOCK:
        state = _load()
        state['usd'] = round(state['usd'] + usd, 6)
        _save(state)


class Reservation:
    def __init__(self, kind: str, estimate: float):
        self.kind = kind
        self.id = secrets.token_hex(16)
        self.amount = max(.000001, estimate)
        self.settled = False
        with LOCK:
            state = _load()
            if available(state) < self.amount:
                raise HTTPException(429, 'Not enough daily model budget for the next step.')
            state['reservations'][self.id] = {'kind': kind, 'amount': self.amount, 'started': time.time()}
            _save(state)

    def settle(self, actual: float | None):
        if self.settled:
            return
        with LOCK:
            state = _load()
            reservation = state['reservations'].pop(self.id, None)
            if reservation is None:
                return
            self.amount = max(0.0, actual) if actual is not None else reservation['amount']
            state['usd'] = round(state['usd'] + self.amount, 6)
            if actual is None:
                state['unknown_usd'] = round(state['unknown_usd'] + self.amount, 6)
            _save(state)
            self.settled = True
            recording = CALLS.get()
            if recording is not None:
                records, path = recording
                records.append({'kind': self.kind, 'cost_usd': self.amount, 'usage_unknown': actual is None})
                write_json(path, records)


@contextmanager
def meter(kind: str, estimate: float):
    reservation = Reservation(kind, estimate)
    try:
        yield reservation
    finally:
        if not reservation.settled:
            reservation.settle(None)  # timeout/cancellation/error is unknown spend, never assumed free


def recover_reservations():
    """Only at process startup, before accepting jobs; unknown prior work is conservatively charged."""
    with LOCK:
        state = _load()
        pending = sum(r['amount'] for r in state['reservations'].values())
        state['usd'] += pending
        state['unknown_usd'] += pending
        state['reservations'] = {}
        _save(state)


def featured_ids() -> set[str]:
    # Legacy fixture support only for retention. Web access uses the packaged example catalog exclusively.
    path = config.SCANS_DIR / 'featured.txt'
    return {i for i in path.read_text().split() if i.isalnum()} if path.exists() else set()


def purge_old_media(now: float | None = None) -> list[str]:
    from app.retention import purge
    return purge(now)


@contextmanager
def accounting(root: Path):
    token = CALLS.set(([], root / 'model_calls.json'))
    try:
        yield
    finally:
        CALLS.reset(token)


def recorded_costs():
    recording = CALLS.get()
    if recording is None or not recording[0]:
        return None
    records = recording[0]
    return {'calls': list(records), 'total': round(sum(r['cost_usd'] for r in records), 6),
            'unknown_usd': round(sum(r['cost_usd'] for r in records if r['usage_unknown']), 6)}
