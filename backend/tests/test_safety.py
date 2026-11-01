"""Failure and boundary tests: assertions target user-visible contract, not implementation shape."""
import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from PIL import Image

from app import config, guard, jobs, media, pipeline, verify
from app.meta.sam import SamResult, Track
from app.report.contracts import adapt_report, sourced_fix
from app.storage import write_json
from test_api import client, owned_root


def result(status='completed', tracks=None):
    return SamResult('cabinet', status, 1, {}, tracks or [])


@pytest.mark.parametrize('groups,expected', [
    ([[result('error')], [result('error')]], 'incomplete'),
    ([[result()], [result('error')]], 'partial'),
    ([[result()]], 'complete'),
    ([[result(), result('error')]], 'incomplete'),
])
def test_tracking_errors_are_distinct_from_successful_empty(groups, expected):
    assessment = pipeline.assessment_for(groups, {'view_adequacy': 'adequate'}, True, True)
    assert assessment['status'] == expected
    if expected != 'complete':
        assert assessment['warnings']


def test_fixer_failure_and_poor_views_are_persistent():
    assert pipeline.assessment_for([], {'view_adequacy': 'adequate'}, False, False)['status'] == 'partial'
    assert pipeline.assessment_for([], {'view_adequacy': 'insufficient', 'view_guidance': 'Show attachment'}, True, True)['warnings'] == ['Show attachment']


def test_legacy_adapter_is_read_only_and_does_not_invent_evidence():
    original = {'hazards': [{'id': 'h1', 'fix': {'actions': ['x']}}]}
    adapted = adapt_report(original)
    assert adapted['schema_version'] == 1
    assert adapted['hazards'][0]['evidence_status'] == 'legacy_unknown'
    assert adapted['hazards'][0]['fix']['source_status'] == 'legacy_unknown'
    assert 'schema_version' not in original
    assert 'evidence_status' not in original['hazards'][0]


def test_neighbouring_tracking_box_is_not_drawn(tmp_path):
    from app.report.marks import draw_marks
    frame = tmp_path / 'frame.jpg'
    Image.new('RGB', (80, 80), 'white').save(frame)
    output = tmp_path / 'out.jpg'
    draw_marks(frame, 2, {'1': Track('shelf', '0', {1: [10, 10, 50, 50]})}, output)
    assert Image.open(output).getpixel((10, 10)) == (255, 255, 255)


def sourced():
    return {'actions': ['Move the object'], 'source_status': 'verified', 'action_sources': [['6.5']],
            'fema_sections': [{'id': '6.5'}]}


def test_every_action_requires_a_read_section():
    assert sourced_fix({'fix': sourced()})
    for refs in ([], [[]], [['unknown']], [['6.5'], ['6.5']]):
        assert not sourced_fix({'fix': {**sourced(), 'action_sources': refs}})


@pytest.mark.parametrize('change', [
    {'boxed_is_same_object': 'no'}, {'visible_change': 'no'}, {'visible_change': 'unclear'},
    {'confidence': 'medium'}, {'original_finding_reconsidered': 'yes'}, {'before_condition_visible': 'no'}, {'change_kind': 'viewpoint_only'},
])
def test_fix_requires_identity_relevant_visible_change_and_confidence(change):
    base = {'verdict': 'fixed', 'before_condition_visible': 'yes', 'change_kind': 'physical_change', 'boxed_is_same_object': 'yes', 'visible_change': 'yes', 'confidence': 'high',
            'original_finding_reconsidered': 'no'}
    assert verify.apply_guard({**base, **change}, True)['verdict'] == 'cannot_verify'


def test_private_ownership_all_routes_and_legacy_quarantine(client, tmp_path):
    root = owned_root(client, tmp_path, 'owned')
    write_json(root / 'report.json', {'scan_id': 'owned', 'created_at': 'now', 'room': {'type': 'office'}, 'hazards': [{'id': 'h1'}]})
    (root / 'evidence').mkdir(); (root / 'evidence/h1.jpg').write_bytes(b'jpg')
    (root / 'verify/v1').mkdir(parents=True)
    owner_cookie = client.cookies.get('risklens_session')
    client.cookies.clear(); client.post('/api/session')
    for route in ('', '/files/evidence/h1.jpg', '/events', '/verify/v1', '/verifications'):
        assert client.get(f'/api/scans/owned{route}').status_code == 404
    assert client.get('/api/scans?ids=owned').json() == []
    assert client.delete('/api/scans/owned').status_code == 404
    assert client.post('/api/scans/owned/hazards/h1/fixcard').status_code == 404
    assert client.post('/api/scans/owned/verify', files={'video': ('v.mp4', b'x', 'video/mp4')}).status_code == 404
    (tmp_path / 'legacy').mkdir()
    assert client.get('/api/scans/legacy').status_code == 404
    client.cookies.clear(); client.cookies.set('risklens_session', owner_cookie)
    assert client.get('/api/scans/owned').status_code == 200


def test_idempotent_upload_reuses_job_and_rejects_changed_content(client):
    from app import guard
    headers = {'Idempotency-Key': 'same'}
    def post(content=b'x'):
        return client.post('/api/scans', files={'video': ('original.MOV', content, 'video/quicktime')}, headers=headers)
    first, second = post(), post()
    assert first.status_code == second.status_code == 200 and first.json() == second.json()
    assert guard._load()['scans'] == 1
    assert post(b'other').status_code == 409
    scan_id = first.json()['scan_id']
    assert client.delete(f'/api/scans/{scan_id}').status_code == 200
    assert post().status_code == 410
    assert not (config.SCANS_DIR / scan_id).exists()


def test_empty_and_broken_video_rejected_before_model_or_quota(client, monkeypatch):
    def reject(_):
        raise ValueError('decode')
    monkeypatch.setattr(media, 'validate', reject)
    assert client.post('/api/scans', files={'video': ('r.mp4', b'broken', 'video/mp4')}).status_code == 422
    assert guard._load()['scans'] == 0
    assert not jobs.JOBS


def test_source_unverified_fixcard_blocked_server_side(client, tmp_path):
    root = owned_root(client, tmp_path, 'abc123')
    write_json(root / 'report.json', {'hazards': [{'id': 'h1', 'fix': {'actions': ['unsafe'], 'source_status': 'source_unverified'}}]})
    assert client.post('/api/scans/abc123/hazards/h1/fixcard').status_code == 409
    assert guard._load()['fixcards'] == 0


def test_expired_content_denied_before_physical_cleanup(client, tmp_path):
    root = owned_root(client, tmp_path, 'expired')
    meta = json.loads((root / 'meta.json').read_text()); meta['created_at_unix'] = time.time()-31*86400
    write_json(root / 'meta.json', meta)
    assert client.get('/api/scans/expired').status_code == 410
    assert root.exists()
    guard.purge_old_media()
    assert not root.exists()


def test_verification_raw_retention_uses_its_own_time(tmp_path):
    from app import access
    root = tmp_path / 'room'; after = root / 'verify/new'
    after.mkdir(parents=True)
    access.new_metadata(root, 'owner'); access.new_metadata(after, 'owner')
    meta = json.loads((root / 'meta.json').read_text()); meta['created_at_unix'] -= 8*86400
    write_json(root / 'meta.json', meta)
    for folder in (root, after): (folder / 'source.mp4').write_bytes(b'x')
    guard.purge_old_media()
    assert not (root / 'source.mp4').exists() and (after / 'source.mp4').exists()


def test_budget_reservations_are_atomic_and_errors_are_charged(monkeypatch):
    monkeypatch.setattr(guard, 'MAX_USD_PER_DAY', 1)
    def reserve(_):
        try: return guard.Reservation('spark', .6)
        except HTTPException: return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        reservations = [r for r in pool.map(reserve, range(8)) if r is not None]
    assert len(reservations) == 1
    reservations[0].settle(None)
    assert guard._load()['usd'] == guard._load()['unknown_usd'] == .6
    with pytest.raises(HTTPException): guard.Reservation('image', .5)
    with pytest.raises(RuntimeError):
        with guard.meter('image', .1): raise RuntimeError('provider failed')
    assert guard._load()['usd'] == .7
    pending = guard.Reservation('voice', .1)
    guard.recover_reservations()
    assert guard._load()['usd'] == pytest.approx(.8)
    assert not guard._load()['reservations']
    pending.settle(0)  # a recovered reservation cannot refund unknown spend
    assert guard._load()['usd'] == pytest.approx(.8)


def test_queue_one_active_two_pending_and_cancellation_joins_writers(tmp_path):
    async def scenario():
        from app.runtime import blocking
        jobs.reset_runtime()
        active, peak = 0, 0
        def write_late(path):
            time.sleep(.03); path.write_text('finished')
        async def work(emit):
            nonlocal active, peak
            active += 1; peak = max(peak, active)
            try: await blocking(write_late, tmp_path / 'late.txt'); await asyncio.sleep(10)
            finally: active -= 1
        for i in range(3):
            folder = tmp_path / str(i); folder.mkdir()
            jobs._start(str(i), str(i), work, folder)
        with pytest.raises(HTTPException) as exc: jobs.ensure_capacity()
        assert exc.value.status_code == 429
        await asyncio.sleep(.01)
        assert sum(j.status == 'running' for j in jobs.JOBS.values()) == 1
        await jobs.cancel_scan('0')
        assert (tmp_path / 'late.txt').exists()
        await jobs.shutdown()
        assert peak == 1 and not jobs.JOBS
    asyncio.run(scenario())


def test_targeted_verification_and_identical_video_never_close_other_findings(tmp_path, monkeypatch):
    from app.report.provenance import sha256_file
    root = tmp_path / 'scan'; root.mkdir()
    src = root / 'source.mp4'; src.write_bytes(b'original')
    frame = root / 'frame.jpg'; Image.new('RGB', (80, 80)).save(frame)
    hazards = [{'id': 'h1', 'object': 'shelf', 'track': 'shelf#0'}, {'id': 'h2', 'object': 'shelf', 'track': 'shelf#1'}]
    write_json(root / 'report.json', {'hazards': hazards, 'provenance': {'source_sha256': sha256_file(src)}})
    monkeypatch.setattr(media, 'validate', lambda _: {})
    monkeypatch.setattr(media, 'probe', lambda _: {'duration_s': 1})
    monkeypatch.setattr(media, 'make_proxy', lambda *_: src)
    monkeypatch.setattr(media, 'extract_frames', lambda *_: [frame])
    async def forbidden(*a, **k): raise AssertionError('Identical video must not call the model')
    monkeypatch.setattr(verify, 'track_concept', forbidden)
    monkeypatch.setattr(verify.verifier, 'verify_hazard', forbidden)
    out = asyncio.run(verify._run(None, root, src, 'new', lambda *_: None, 'h1'))
    assert out['checked_hazard_ids'] == ['h1'] and out['unchecked_hazard_ids'] == ['h2']
    assert out['fixed'] == 0 and out['results']['h1']['verdict'] == 'cannot_verify'
    assert json.loads((root / 'verify/new/verification.json').read_text()) == out

@pytest.mark.parametrize('failure', ['all_tracking', 'partial_tracking', 'fixer', 'empty_success'])
def test_complete_pipeline_persists_failure_and_original_evidence(tmp_path, monkeypatch, failure):
    root = tmp_path/'room'; root.mkdir()
    src = root/'source.mp4'; src.write_bytes(b'original')
    frames = []
    for i in range(6):
        path = root/f'{i}.jpg'; Image.new('RGB', (80, 80), (i*30, 0, 0)).save(path); frames.append(path)
    monkeypatch.setattr(media, 'validate', lambda _: {'duration_s': 6})
    monkeypatch.setattr(media, 'make_proxy', lambda *_: src)
    monkeypatch.setattr(media, 'extract_frames', lambda *_: frames)
    monkeypatch.setattr(media, 'probe', lambda _: {'duration_s': 6})
    meta = {'model': 'fake', 'cost_usd': 0, 'reasoning_summary': [], 'usage': {}, 'tool_calls': []}
    async def plan(*_):
        return {'room_type': 'office', 'sleeping_area': False, 'exit_visible': False,
                'concepts': [{'concept': c, 'alternates': []} for c in ('shelf', 'lamp')]}, meta
    @asynccontextmanager
    async def uploaded(*_): yield 'fakefile'
    async def track(api, fid, concept, **kwargs):
        failed = failure == 'all_tracking' or failure == 'partial_tracking' and concept == 'lamp'
        tracks = [] if failed or failure == 'empty_success' else [Track(concept, '0', {0:[1,1,40,40], 2:[1,1,40,40]})]
        return SamResult(concept, 'error' if failed else 'completed', 0, {}, tracks)
    async def survey(*_):
        return {'room_summary': 'Test room', 'view_adequacy': 'adequate', 'view_guidance': '', 'hazards': [] if failure == 'empty_success' else [
            {'mark': '1', 'object': 'Shelf', 'relation': 'tall_tip_over', 'severity': 'medium', 'evidence_frame': '1',
             'rationale': 'Unknown attachment', 'evidence_status': 'needs_check', 'evidence_observation': 'Shelf', 'next_view_request': 'Show attachment'}]}, meta
    async def fixes(*_):
        if failure == 'fixer': raise RuntimeError('provider failure')
        return {'h1': sourced()}, meta
    monkeypatch.setattr(pipeline.planner, 'plan', plan); monkeypatch.setattr(pipeline.surveyor, 'survey', survey)
    monkeypatch.setattr(pipeline.fixer, 'plan_fixes', fixes); monkeypatch.setattr(pipeline, 'uploaded_video', uploaded)
    monkeypatch.setattr(pipeline, 'track_concept', track)
    out = asyncio.run(pipeline._run(None, src, 'Untrusted context', lambda *_: None, 'room', True))
    expected = {'all_tracking': 'incomplete', 'partial_tracking': 'partial', 'fixer': 'partial', 'empty_success': 'complete'}[failure]
    assert out['assessment']['status'] == expected
    assert out['context']['occupant_narration'] == 'Untrusted context'
    if out['hazards']:
        h = out['hazards'][0]
        assert h['evidence_frame'] == '1' and not h['tracking_supported'] and h['box'] is None
        assert Image.open(root/h['evidence_image']).getpixel((10,10))[0] == pytest.approx(30, abs=3)
    assert json.loads((root/'report.json').read_text()) == out
    assert not (root/'partial.json').exists()


def test_candidate_identity_must_match_selected_evidence(tmp_path, monkeypatch):
    root = tmp_path/'room'; root.mkdir()
    src = root/'after.mp4'; src.write_bytes(b'after')
    frame = root/'original.jpg'; Image.new('RGB', (80,80)).save(frame)
    h = {'id':'h1','object':'Cabinet','track':'cabinet#0','evidence_image':'original.jpg','fix':sourced()}
    write_json(root/'report.json', {'hazards':[h], 'plan':{'concepts':[]}})
    monkeypatch.setattr(media, 'validate', lambda _: {})
    monkeypatch.setattr(media, 'probe', lambda _: {'duration_s':1})
    monkeypatch.setattr(media, 'make_proxy', lambda *_: src)
    monkeypatch.setattr(media, 'extract_frames', lambda *_: [frame]*6)
    @asynccontextmanager
    async def uploaded(*_): yield 'fake'
    async def track(*a,**k): return result(tracks=[Track('cabinet','0',{0:[1,1,20,20],5:[1,1,20,20]}), Track('cabinet','1',{0:[30,30,60,60],5:[30,30,60,60]})])
    async def verdict(api, hazard, before, views):
        assert before == frame and len({v['candidate_id'] for v in views}) == 3
        return {'verdict':'fixed','candidate_id':'cabinet#0','best_after_view':'c1f0','confidence':'high',
                'boxed_is_same_object':'yes','visible_change':'yes','before_condition_visible':'yes','change_kind':'physical_change'}, {'cost_usd':0,'reasoning_summary':[], 'model':'fake'}
    monkeypatch.setattr(verify, 'uploaded_video', uploaded); monkeypatch.setattr(verify, 'track_concept', track)
    monkeypatch.setattr(verify.verifier, 'verify_hazard', verdict)
    out = asyncio.run(verify._run(None, root, src, 'attempt', lambda *_: None, None))
    assert out['fixed'] == 0
    assert out['results']['h1']['model_verdict'] == 'fixed'
    assert out['results']['h1']['verdict'] == 'cannot_verify'


def test_valid_streaming_webm_without_duration_is_accepted(tmp_path):
    import subprocess
    src = tmp_path/'browser.webm'
    with src.open('wb') as output:
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=blue:size=64x64:duration=1',
                        '-c:v','libvpx','-f','webm','pipe:1'], stdout=output, check=True)
    info = media.validate(src)
    assert info['width'] == 64
    assert media.probe(media.make_proxy(src, tmp_path/'proxy.mp4'))['duration_s'] > 0


def test_completed_example_is_public_and_readonly_but_live_run_is_private(client, tmp_path):
    root = config.EXAMPLES_DIR/'syntheticroom'; root.mkdir(parents=True)
    write_json(config.EXAMPLES_DIR/'catalog.json', [{'id':'synthetic-room','scan_id':'syntheticroom','synthetic':True}])
    write_json(root/'report.json', {'schema_version':2, 'hazards':[], 'room':{'type':'office'}, 'created_at':'now'})
    (root/'source.mp4').write_bytes(b'licensed test fixture')
    assert len(client.get('/api/examples').json()) == 1
    assert client.get('/api/scans/syntheticroom').json()['read_only']
    assert client.delete('/api/scans/syntheticroom').status_code == 403
    assert client.post('/api/scans/syntheticroom/hazards/h1/fixcard').status_code == 403
    started = client.post('/api/examples/synthetic-room/runs', headers={'Idempotency-Key':'live-once'})
    assert started.status_code == 200
    assert client.post('/api/examples/synthetic-room/runs', headers={'Idempotency-Key':'live-once'}).json() == started.json()
    own_id = started.json()['scan_id']
    client.cookies.clear()
    assert client.get('/api/scans/syntheticroom').status_code == 200
    assert client.get(f'/api/scans/{own_id}').status_code == 404


def test_persistence_finishes_before_job_start(client, monkeypatch):
    from app import storage
    persisted = []
    monkeypatch.setattr(storage, 'COMMIT', lambda: persisted.append('commit'))
    original = jobs.start_scan
    def start(*args):
        assert persisted
        records = list((config.SCANS_DIR/'_idempotency').glob('*.json'))
        assert len(records) == 1
        return original(*args)
    monkeypatch.setattr(jobs, 'start_scan', start)
    response = client.post('/api/scans', files={'video': ('r.mp4', b'video', 'video/mp4')})
    assert response.status_code == 200


def test_generated_image_has_embedded_label(tmp_path):
    from app.meta.image import label_illustration
    path = tmp_path/'illustration.jpg'; Image.new('RGB', (480,320), 'white').save(path)
    label_illustration(path)
    image = Image.open(path)
    assert sum(image.getpixel((2,318))) < 180
    assert image.getpixel((2,2)) == (255,255,255)
