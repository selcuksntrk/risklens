"""HTTP release acceptance. --live explicitly spends model budget using ONLY the packaged synthetic video.
Checks version, public example, browser ownership, duplicate uploads, queued deletion and targeted verification.
No credentials, room text or private media are printed or saved to the result file.
"""
import argparse
import hashlib
import json
import time
import uuid
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]

def check(base_url, live=False):
    results = {'version': (ROOT/'VERSION').read_text().strip(), 'checks': [], 'live': live}
    started = time.monotonic()
    def record(name):
        results['checks'].append(name); print(name, flush=True)
    with httpx.Client(base_url=base_url.rstrip('/'), timeout=90, follow_redirects=True) as a, httpx.Client(base_url=base_url.rstrip('/'), timeout=90) as b:
        health = a.get('/api/health'); health.raise_for_status()
        assert health.json()['version'] == results['version'] and health.json()['report_schema_version'] == 2
        page = a.get('/'); page.raise_for_status()
        manifest = json.loads((ROOT/'release.json').read_text())
        for asset, digest in manifest['assets'].items():
            response = a.get('/'+asset); response.raise_for_status()
            assert hashlib.sha256(response.content).hexdigest() == digest, asset
        record('health_and_frontend_release_match')
        rows = a.get('/api/examples').json(); assert rows
        row = rows[0]; public = a.get('/api/scans/'+row['scan_id']); public.raise_for_status()
        assert public.json()['read_only'] and public.json()['report']['schema_version'] == 2
        for hazard in public.json()['report']['hazards']:
            assert a.get(f"/api/scans/{row['scan_id']}/files/{hazard['evidence_image']}").status_code == 200
        record('completed_licensed_example_readable_without_session')
        if not live: return results
        session = a.post('/api/session'); session.raise_for_status()
        cookie = session.headers.get('set-cookie','').lower()
        assert 'httponly' in cookie and 'samesite=lax' in cookie and 'secure' in cookie
        b.post('/api/session').raise_for_status()
        assert b.post(f"/api/scans/{row['scan_id']}/hazards/h1/fixcard").status_code == 403
        record('secure_session_and_readonly_example')
        key = uuid.uuid4().hex
        response = a.post(f"/api/examples/{row['id']}/runs", headers={'Idempotency-Key':key}); response.raise_for_status()
        scan_id = response.json()['scan_id']
        owned = {scan_id}
        video = (ROOT/'examples/generated'/row['scan_id']/'source.mp4').read_bytes()
        try:
            assert a.post(f"/api/examples/{row['id']}/runs", headers={'Idempotency-Key':key}).json()['scan_id'] == scan_id
            upload_key = uuid.uuid4().hex
            def upload(context='Synthetic upload test'):
                return a.post('/api/scans', headers={'Idempotency-Key':upload_key},
                    data={'narration':context}, files={'video':('synthetic-original.mp4',video,'video/mp4')})
            first, retry = upload(), upload(); first.raise_for_status(); retry.raise_for_status()
            queued_id = first.json()['scan_id']; owned.add(queued_id)
            assert first.json() == retry.json() and upload('Changed context').status_code == 409
            assert b.get('/api/scans/'+queued_id).status_code == 404
            results['deleted_upload_status'] = a.get('/api/scans/'+queued_id).json()['status']
            assert a.delete('/api/scans/'+queued_id).status_code == 200
            assert upload().status_code == 410
            record('own_upload_idempotency_conflict_and_deletion')
            deadline = time.monotonic()+600
            while time.monotonic() < deadline:
                response = a.get('/api/scans/'+scan_id); response.raise_for_status(); state = response.json()
                if state['status'] == 'done': break
                if state['status'] in ('error','interrupted'): raise RuntimeError('Live sample ended: '+state['status'])
                time.sleep(3)
            else: raise TimeoutError('Live sample did not finish')
            report = state['report']
            results['sample'] = {'assessment': report['assessment']['status'], 'findings': len(report['hazards']),
                'seconds':report['seconds'], 'cost_usd':report['cost_usd']['total']}
            record('live_sample_returned_persistent_assessment')
            for route in ('', '/events', '/verifications'):
                assert b.get('/api/scans/'+scan_id+route).status_code == 404
            assert b.get('/api/scans', params={'ids':scan_id}).json() == []
            assert b.delete('/api/scans/'+scan_id).status_code == 404
            if report['hazards']:
                h = report['hazards'][0]
                assert b.get(f"/api/scans/{scan_id}/files/{h['evidence_image']}").status_code == 404
                assert b.post(f"/api/scans/{scan_id}/hazards/{h['id']}/fixcard").status_code == 404
                verify_key = uuid.uuid4().hex
                response = a.post(f'/api/scans/{scan_id}/verify', headers={'Idempotency-Key':verify_key},
                    data={'hazard_id':h['id']}, files={'video':('same.mp4',video,'video/mp4')}); response.raise_for_status()
                verify_id = response.json()['verify_id']
                assert b.get(f'/api/scans/{scan_id}/verify/{verify_id}').status_code == 404
                deadline = time.monotonic()+120
                while time.monotonic() < deadline:
                    state = a.get(f'/api/scans/{scan_id}/verify/{verify_id}').json()
                    if state['status'] == 'done': break
                    if state['status'] in ('error','interrupted'): raise RuntimeError('Verification ended: '+state['status'])
                    time.sleep(2)
                else: raise TimeoutError('Verification did not finish')
                verification = state['verification']
                assert verification['fixed'] == 0 and verification['checked_hazard_ids'] == [h['id']]
                assert set(verification['unchecked_hazard_ids']) == {x['id'] for x in report['hazards'] if x['id'] != h['id']}
                assert a.get(f'/api/scans/{scan_id}/verifications').json()[0]['verify_id'] == verify_id
                record('targeted_identical_video_zero_confirmations_and_history')
            record('cross_browser_private_routes_denied')
        finally:
            for scan in owned:
                response = a.delete('/api/scans/'+scan)
                assert response.status_code in (200,404), response.status_code
                assert a.get('/api/scans/'+scan).status_code == 404
        assert a.post(f"/api/examples/{row['id']}/runs", headers={'Idempotency-Key':key}).status_code == 410
        record('deleted_scans_unavailable_and_not_replayed')
    results['elapsed_seconds'] = round(time.monotonic()-started,1)
    return results

if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('url'); parser.add_argument('--live', action='store_true')
    parser.add_argument('--output', type=Path, required=True); args=parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = check(args.url,args.live); args.output.write_text(json.dumps(result,indent=2)+'\n')
