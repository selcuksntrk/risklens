"""Private browser-owned room screening, bounded jobs and explicitly licensed public examples."""
from __future__ import annotations
import asyncio
import hashlib
import json
import shutil
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile, WebSocket
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app import access, config, examples, guard, jobs, media, retention
from app.runtime import blocking
from app.ingress import UploadLimits
from app.storage import write_json, durable
from app.meta import image, voice
from app.meta.clients import meta_client
from app.meta.files import retry_pending
from app.report.contracts import adapt_report, counts, sourced_fix

MAX_UPLOAD_BYTES = 300 * 1024 * 1024
VIDEO_TYPES = {'video/mp4': '.mp4', 'video/quicktime': '.mov', 'video/webm': '.webm'}
FRONTEND = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
SERVED_DIRS = {'evidence', 'marked', 'fixcards'}
MUTATION_LOCK = asyncio.Lock()
ILLUSTRATION_LOCK = asyncio.Lock()
AUX_TASKS = jobs.AUX_TASKS
UPLOAD_ACTIVE = 0


async def maintenance():
    while True:
        guard.purge_old_media()
        jobs.clean_finished()
        if (config.SCANS_DIR / '_remote_cleanup').exists():
            try:
                async with meta_client() as api:
                    await retry_pending(api)
            except (Exception, SystemExit):
                pass
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app):
    global MUTATION_LOCK, ILLUSTRATION_LOCK, UPLOAD_ACTIVE
    config.SCANS_DIR.mkdir(parents=True, exist_ok=True)
    MUTATION_LOCK, ILLUSTRATION_LOCK = asyncio.Lock(), asyncio.Lock()
    UPLOAD_ACTIVE = 0
    jobs.reset_runtime()
    guard.recover_reservations()
    task = asyncio.create_task(maintenance())
    yield
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    await jobs.shutdown()
    aux = [t for group in AUX_TASKS.values() for t in group]
    for t in aux:
        t.cancel()
    await asyncio.gather(*aux, return_exceptions=True)
    AUX_TASKS.clear()


app = FastAPI(title='RiskLens', version=config.APP_VERSION, lifespan=lifespan)
app.add_middleware(UploadLimits, max_bytes=MAX_UPLOAD_BYTES + 1024*1024)
config.SCANS_DIR.mkdir(parents=True, exist_ok=True)


@app.middleware('http')
async def protect_requests(request, call_next):
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        try:
            access.same_origin(request)
            if request.url.path.startswith('/api/scans'):
                access.require_owner(request)
        except HTTPException as exc:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': exc.detail}, status_code=exc.status_code)
    size = request.headers.get('content-length', '')
    if size.isdigit() and int(size) > MAX_UPLOAD_BYTES + 1024*1024:
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail': 'Video is too large.'}, status_code=413)
    response = await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    elif request.url.path.startswith('/assets/') and response.status_code == 200:
        # Content-hashed build output: safe to cache forever.
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    else:
        # index.html / manifest / favicon: always revalidate (ETag → 304). Without this, Safari's
        # heuristic caching kept an old index.html pointing at deleted asset hashes → blank page.
        response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    return response


@app.post('/api/session')
def create_session(request: Request, response: Response):
    return access.session(request, response)


@app.get('/api/health')
def health():
    return {'status': 'ok', 'version': config.APP_VERSION, 'report_schema_version': config.SCHEMA_VERSION}


def _scan_dir(scan_id: str, request: Request, write=False) -> Path:
    if not scan_id.isalnum() or len(scan_id) > 80:
        raise HTTPException(400, 'Bad scan id.')
    example = examples.by_scan(scan_id)
    if example:
        if write:
            raise HTTPException(403, 'The sample report is read-only. Run the sample analysis or upload your own video to create a scan.')
        return examples.root(example)
    root = config.SCANS_DIR / scan_id
    access.check_private(root, request)
    return root


def _key(request, owner_id, operation):
    key = request.headers.get('Idempotency-Key', '')
    if not key or len(key) > 128 or not all(c.isalnum() or c in '-_' for c in key):
        raise HTTPException(400, 'A valid Idempotency-Key is required.')
    name = hashlib.sha256(f'{owner_id}:{operation}:{key}'.encode()).hexdigest()
    return config.SCANS_DIR / '_idempotency' / f'{name}.json'


def replay(path, fingerprint):
    if not path.exists():
        return None
    previous = json.loads(path.read_text())
    if previous['fingerprint'] != fingerprint:
        raise HTTPException(409, 'This upload key was already used for different content.')
    root = config.SCANS_DIR / previous['scan_id']
    if not root.exists() or (root / '.deleted').exists() or retention.report_expired(root):
        raise HTTPException(410, 'The original attempt was deleted or expired. Start a new upload.')
    return previous['response']


async def _temporary_upload(video):
    global UPLOAD_ACTIVE
    if UPLOAD_ACTIVE >= 3:
        raise HTTPException(429, 'Uploads are busy. Keep your video and retry shortly.')
    content_type = (video.content_type or '').split(';')[0]
    suffix = Path(video.filename or '').suffix.lower()
    if content_type not in VIDEO_TYPES:
        content_type = next((t for t, s in VIDEO_TYPES.items() if s == suffix), content_type)
    if content_type not in VIDEO_TYPES:
        raise HTTPException(415, 'Please upload MP4, MOV or WebM video.')
    UPLOAD_ACTIVE += 1
    folder = config.SCANS_DIR / '_uploads' / uuid.uuid4().hex
    folder.mkdir(parents=True)
    src = folder / f'source{VIDEO_TYPES[content_type]}'
    size, digest = 0, hashlib.sha256()
    try:
        with src.open('wb') as stream:
            while chunk := await video.read(1024*1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, 'Video is too large.')
                digest.update(chunk)
                stream.write(chunk)
        try:
            await blocking(media.validate, src)
        except Exception as exc:
            raise HTTPException(422, 'The file is empty, damaged or has no supported video stream.') from exc
        return src, digest.hexdigest()
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    finally:
        UPLOAD_ACTIVE -= 1
        await video.close()


@app.post('/api/scans')
async def create_scan(request: Request, video: UploadFile = File(...), narration: str = Form('')):
    owner_id = access.require_owner(request)
    if len(narration) > 4000:
        raise HTTPException(422, 'Room context must be at most 4000 characters.')
    key_path = _key(request, owner_id, 'scan')
    filename = Path(video.filename or 'room.mp4').name
    src, digest = await _temporary_upload(video)
    fingerprint = hashlib.sha256(f'{digest}:{narration.strip()}'.encode()).hexdigest()
    try:
        async with MUTATION_LOCK:
            previous = replay(key_path, fingerprint)
            if previous:
                return previous
            jobs.ensure_capacity()
            guard.charge_scan(guard.client_ip(request))
            scan_id = jobs.new_scan_id()
            root = config.SCANS_DIR / scan_id
            root.mkdir()
            target = root / src.name
            src.replace(target)
            access.new_metadata(root, owner_id, narration=narration.strip(), filename=filename, mime_type=video.content_type)
            result = {'scan_id': scan_id}
            write_json(key_path, {'fingerprint': fingerprint, 'scan_id': scan_id, 'response': result})
            jobs.start_scan(scan_id, target, narration.strip() or None)
            return result
    finally:
        shutil.rmtree(src.parent, ignore_errors=True)


@app.get('/api/scans')
def list_scans(request: Request, ids: str = ''):
    rows = []
    # The browser's supplied IDs are only a convenience. Ownership is always checked server-side.
    wanted = [s for s in ids.split(',') if s.isalnum()][:50]
    for scan_id in wanted:
        root = config.SCANS_DIR / scan_id
        if not root.is_dir() or not access.authorized(root, request) or retention.report_expired(root):
            continue
        if (root / 'report.json').exists():
            report = adapt_report(json.loads((root / 'report.json').read_text()))
            rows.append({'scan_id': scan_id, 'created_at': report['created_at'], 'room': report['room']['type'],
                         'hazards': len(report['hazards']), 'counts': counts(report['hazards']),
                         'assessment_status': report['assessment']['status']})
    return sorted(rows, key=lambda r: r['created_at'], reverse=True)


@app.get('/api/scans/{scan_id}')
def get_scan(scan_id: str, request: Request):
    root = _scan_dir(scan_id, request)
    state = jobs.state(scan_id, root, 'report.json', 'report')
    if state['status'] == 'done':
        state['report'] = adapt_report(state['report'])
        state['fixcards'] = [p.stem for p in (root / 'fixcards').glob('h*.jpg') if not p.stem.endswith('_before')]
        latest = root / 'verification.json'
        state['verification'] = json.loads(latest.read_text()) if latest.exists() else None
        state['read_only'] = examples.by_scan(scan_id) is not None
    elif (root / 'partial.json').exists():
        state['partial'] = json.loads((root / 'partial.json').read_text())
    return state


@app.post('/api/scans/{scan_id}/verify')
async def verify_scan(scan_id: str, request: Request, video: UploadFile = File(...), hazard_id: str = Form('')):
    root = _scan_dir(scan_id, request, write=True)
    owner_id = access.require_owner(request)
    if not (root / 'report.json').exists():
        raise HTTPException(409, 'The original report is not ready.')
    report = json.loads((root / 'report.json').read_text())
    if not report['hazards'] or (hazard_id and hazard_id not in {h['id'] for h in report['hazards']}):
        raise HTTPException(422, 'Select an existing finding for verification.')
    key_path = _key(request, owner_id, f'verify:{scan_id}')
    src, digest = await _temporary_upload(video)
    fingerprint = hashlib.sha256(f'{digest}:{hazard_id}'.encode()).hexdigest()
    try:
        async with MUTATION_LOCK:
            _scan_dir(scan_id, request, write=True)
            previous = replay(key_path, fingerprint)
            if previous:
                return previous
            jobs.ensure_capacity(scan_id)
            guard.charge_scan(guard.client_ip(request))
            verify_id = f'{scan_id}v{jobs.new_scan_id()[:6]}'
            folder = root / 'verify' / verify_id
            folder.mkdir(parents=True)
            target = folder / src.name
            src.replace(target)
            access.new_metadata(folder, owner_id, hazard_id=hazard_id or None, filename=Path(video.filename or 'room.mp4').name, mime_type=video.content_type)
            result = {'verify_id': verify_id}
            write_json(key_path, {'fingerprint': fingerprint, 'scan_id': scan_id, 'response': result})
            jobs.start_verify(scan_id, verify_id, target, hazard_id or None)
            return result
    finally:
        shutil.rmtree(src.parent, ignore_errors=True)


@app.get('/api/scans/{scan_id}/verifications')
def list_verifications(scan_id: str, request: Request):
    root = _scan_dir(scan_id, request)
    rows = []
    for folder in (root / 'verify').glob('*'):
        if not folder.is_dir():
            continue
        state = jobs.state(folder.name, folder, 'verification.json', 'verification')
        value = state.get('verification', {})
        rows.append({'verify_id': folder.name, 'status': state['status'], 'created_at': value.get('created_at'),
                     'fixed': value.get('fixed', 0), 'hazard_id': value.get('hazard_id')})
    return sorted(rows, key=lambda r: r.get('created_at') or '', reverse=True)


@app.get('/api/scans/{scan_id}/verify/{verify_id}')
def get_verification(scan_id: str, verify_id: str, request: Request):
    root = _scan_dir(scan_id, request)
    if not verify_id.isalnum():
        raise HTTPException(400, 'Bad verification id.')
    folder = root / 'verify' / verify_id
    if not folder.is_dir():
        raise HTTPException(404, 'Verification not found.')
    return jobs.state(verify_id, folder, 'verification.json', 'verification')


@app.delete('/api/scans/{scan_id}')
async def delete_scan(scan_id: str, request: Request):
    async with MUTATION_LOCK:
        root = _scan_dir(scan_id, request, write=True)
        write_json(root / '.deleted', {'deleted': True})
        await jobs.cancel_scan(scan_id)
        tasks = list(AUX_TASKS.get(scan_id, set()))
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        shutil.rmtree(root)
        durable()
    return {'status': 'deleted'}


@app.post('/api/scans/{scan_id}/hazards/{hazard_id}/fixcard')
async def make_fix_card(scan_id: str, hazard_id: str, request: Request):
    root = _scan_dir(scan_id, request, write=True)
    if not (root / 'report.json').exists():
        raise HTTPException(409, 'The report is not ready.')
    report = adapt_report(json.loads((root / 'report.json').read_text()))
    hazard = next((h for h in report['hazards'] if h['id'] == hazard_id), None)
    if not hazard:
        raise HTTPException(404, 'Finding not found.')
    if not sourced_fix(hazard):
        raise HTTPException(409, 'A source-linked recommendation is required for an AI illustration.')
    async def generate():
        async with ILLUSTRATION_LOCK:
            _scan_dir(scan_id, request, write=True)
            out = root / 'fixcards' / f'{hazard_id}.jpg'
            if not out.exists():
                frame = root / 'frames' / f"{int(hazard['evidence_frame']):05d}.jpg"
                if retention.raw_expired(root) or not frame.exists():
                    raise HTTPException(410, 'The source frames have expired. Please scan again.')
                guard.charge_fixcard()
                before = await blocking(image.crop_around, frame, hazard.get('box'), root / 'fixcards' / f'{hazard_id}_before.jpg')
                async with meta_client() as api:
                    try:
                        meta = await image.fix_card(api, before, image.fix_prompt(report['room']['type'], hazard), out)
                    except image.ImageRefused as exc:
                        raise HTTPException(422, str(exc)) from exc
                write_json(out.with_suffix('.json'), meta)
            return {'image': f'fixcards/{hazard_id}.jpg', 'before': f'fixcards/{hazard_id}_before.jpg'}
    task = asyncio.create_task(generate())
    AUX_TASKS.setdefault(scan_id, set()).add(task)
    try:
        return await task
    except asyncio.CancelledError:
        raise HTTPException(409, 'Illustration cancelled.') from None
    finally:
        AUX_TASKS[scan_id].discard(task)
        if not AUX_TASKS[scan_id]:
            del AUX_TASKS[scan_id]


@app.get('/api/scans/{scan_id}/events')
async def scan_events(scan_id: str, request: Request):
    job = jobs.JOBS.get(scan_id)
    # A verification event URL uses its job id. Resolve ownership through the recorded parent.
    parent = (job.parent_id or scan_id) if job else scan_id
    _scan_dir(parent, request)
    if not job:
        raise HTTPException(404, 'No live events. Fetch the persistent job status instead.')
    async def stream():
        async for event in jobs.follow(job):
            yield f'data: {json.dumps(event)}\n\n'
        yield 'event: end\ndata: {}\n\n'
    return StreamingResponse(stream(), media_type='text/event-stream', headers={'X-Accel-Buffering': 'no'})


def _servable(parts):
    return (len(parts) == 2 and parts[0] in SERVED_DIRS) or (len(parts) == 4 and parts[0] == 'verify' and parts[2] == 'after')


@app.get('/api/scans/{scan_id}/files/{path:path}')
def scan_file(scan_id: str, path: str, request: Request):
    root = _scan_dir(scan_id, request).resolve()
    target = (root / path).resolve()
    if root not in target.parents or not target.is_file() or not _servable(target.relative_to(root).parts):
        raise HTTPException(404)
    return FileResponse(target)


@app.get('/api/examples')
def list_examples():
    return examples.catalog()


@app.post('/api/examples/{example_id}/runs')
async def run_example(example_id: str, request: Request):
    owner_id = access.require_owner(request)
    row = examples.find(example_id)
    if not row:
        raise HTTPException(404, 'Example not found.')
    key_path = _key(request, owner_id, f'example:{example_id}')
    source = examples.root(row) / 'source.mp4'
    if not source.exists():
        raise HTTPException(503, 'Live sample is not installed.')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    async with MUTATION_LOCK:
        previous = replay(key_path, digest)
        if previous:
            return previous
        jobs.ensure_capacity()
        guard.charge_scan(guard.client_ip(request))
        scan_id = jobs.new_scan_id()
        root = config.SCANS_DIR / scan_id
        root.mkdir()
        target = root / 'source.mp4'
        shutil.copyfile(source, target)
        access.new_metadata(root, owner_id, example_id=example_id, narration=row.get('context', ''))
        result = {'scan_id': scan_id}
        write_json(key_path, {'fingerprint': digest, 'scan_id': scan_id, 'response': result})
        jobs.start_scan(scan_id, target, row.get('context'))
        return result


@app.websocket('/api/voice')
async def voice_ws(ws: WebSocket):
    if access.owner(ws) is None:
        await ws.close(code=1008)
        return
    await voice.proxy(ws)


if FRONTEND.is_dir():
    app.mount('/', StaticFiles(directory=FRONTEND, html=True), name='frontend')
