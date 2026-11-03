"""Run frozen room-split inputs through full and Spark-only pipelines; never include private media in exports.
Usage from backend: python ../eval/run.py ../eval/private/manifest.json --output ../eval/results/run1
Model calls spend the normal persisted daily budget. No contributor model is accepted.
"""
import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1]/'.env')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'backend'))
from app import access, config, jobs
from app.pipeline import run_scan
from app.verify import run_verify
from app.storage import write_json


def validate_manifest(manifest):
    rooms = {}
    ids = set()
    for row in manifest['clips']:
        if row['split'] not in ('development', 'evaluation'): raise ValueError('Unknown split')
        if row['clip_id'] in ids: raise ValueError('Duplicate clip id')
        ids.add(row['clip_id'])
        if rooms.setdefault(row['room_id'], row['split']) != row['split']:
            raise ValueError('Room leakage: a room cannot appear in development and evaluation')
        if row['case'] not in ('A0', 'B0', 'B1', 'B2', 'B3', 'B4'): raise ValueError('Unknown case')
        if not row.get('pre_model_observations_recorded'): raise ValueError('Freeze observations before inference')
        if row['case'] != 'A0' and not row.get('baseline_clip_id'): raise ValueError('Verification needs a baseline clip')
        if not set(row.get('variants', ['spark_only', 'full'])) <= {'spark_only', 'full'}:
            raise ValueError('Unknown variant')
        repetitions = row.get('repetitions', {})
        if any(type(n) is not int or not 1 <= n <= 3 for n in repetitions.values()):
            raise ValueError('Repetitions must be between 1 and 3')
        if manifest.get('data_type') == 'synthetic' and row['case'] == 'B2':
            raise ValueError('Synthetic regression cannot demonstrate a physical fix')
    return rooms


async def run(manifest_path, output):
    manifest = json.loads(manifest_path.read_text()); validate_manifest(manifest)
    if output.exists(): raise ValueError('Use a new output directory; evaluation runs are immutable')
    # Validate ALL files before creating output or making any paid request.
    for row in manifest['clips']:
        if hashlib.sha256((manifest_path.parent/row['video']).resolve().read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Video changed since observations were frozen')
    if manifest.get('observations_file'):
        observation = (manifest_path.parent/manifest['observations_file']).read_bytes()
        if hashlib.sha256(observation).hexdigest() != manifest['observations_sha256']:
            raise ValueError('Observations changed after freezing')
    output.mkdir(parents=True)
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    summary = {'manifest_sha256': digest, 'version': config.APP_VERSION,
               'data_type': manifest.get('data_type', 'unspecified'),
               'evaluation_kind': manifest.get('evaluation_kind', 'unspecified'),
               'review_status': 'pending_human_adjudication', 'runs': []}
    write_json(output/'runs.private.json', summary)
    for variant in ('spark_only', 'full'):
        baselines = {}
        for row in sorted(manifest['clips'], key=lambda r: r['case'] != 'A0'):
            if variant not in row.get('variants', ['spark_only', 'full']): continue
            for repetition in range(1, row.get('repetitions', {}).get(variant, 1) + 1):
                stop = await attempt(manifest_path, output, summary, baselines, row, variant, repetition)
                if stop:
                    summary['stopped_reason'] = stop
                    write_json(output/'runs.private.json', summary)
                    print('Evaluation stopped: '+stop, flush=True)
                    return
    print('Run saved privately. Human matching is required before computing finding metrics.')


async def attempt(manifest_path, output, summary, baselines, row, variant, repetition):
    src = (manifest_path.parent/row['video']).resolve()
    source_hash = hashlib.sha256(src.read_bytes()).hexdigest()
    if source_hash != row['sha256']: raise ValueError('Video changed since observations were frozen')
    entry = {k: row[k] for k in ('clip_id', 'room_id', 'split', 'case')}
    entry.update(variant=variant, repetition=repetition, source_sha256=source_hash, status='running',
                 control_description=row.get('control_description'))
    summary['runs'].append(entry)
    write_json(output/'runs.private.json', summary)
    print(f"Starting {row['clip_id']} {variant} #{repetition}", flush=True)
    started = time.perf_counter()
    attempt_root = None
    stop = None
    try:
        if row['case'] == 'A0':
            scan_id = 'eval' + jobs.new_scan_id()
            root = config.SCANS_DIR/scan_id; root.mkdir(parents=True)
            access.new_metadata(root, '', origin='offline_evaluation')
            attempt_root = root
            entry['scan_id'] = scan_id
            report = await run_scan(src, row.get('context'), scan_id=scan_id, tracking=variant == 'full')
            if repetition == 1: baselines[row['clip_id']] = root
            entry.update(status='done', assessment=report['assessment']['status'], seconds=report['seconds'],
                         cost_usd=report['cost_usd']['total'], report=report)
        else:
            # Baseline automatic verification intentionally abstains without tracking.
            root = baselines[row['baseline_clip_id']]
            verify_id = 'eval' + jobs.new_scan_id()
            folder = root/'verify'/verify_id; folder.mkdir(parents=True)
            attempt_root = folder
            entry.update(scan_id=root.name, verify_id=verify_id)
            access.new_metadata(folder, '', origin='offline_evaluation')
            result = await run_verify(root, src, verify_id, lambda *_: None, row.get('hazard_id'))
            entry.update(status='done', seconds=result['seconds'], cost_usd=result['cost_usd'], verification=result)
    except Exception as exc:
        entry['status'] = 'error'
        entry['error_type'] = type(exc).__name__  # no private exception text or paths
        code = getattr(exc, 'status_code', None)
        if code: entry['http_status'] = code
        if code in (401,403,429) or type(exc).__name__ in ('APIConnectionError','APITimeoutError'):
            stop = 'model_service_or_budget_unavailable'
    entry.setdefault('seconds', round(time.perf_counter()-started, 1))
    calls = attempt_root/'model_calls.json' if attempt_root else None
    if calls and calls.exists():
        billing = json.loads(calls.read_text())
        entry['recorded_call_cost_usd'] = round(sum(c['cost_usd'] for c in billing), 6)
        entry['unknown_usage_usd'] = round(sum(c['cost_usd'] for c in billing if c.get('usage_unknown')), 6)
    # An exception never implies zero cost. Preserve reservations/unknown charges.
    write_json(output/'runs.private.json', summary)
    print(f"Finished {row['clip_id']} {variant}: {entry['status']}", flush=True)
    return stop

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1]/'.env')
    parser = argparse.ArgumentParser(); parser.add_argument('manifest', type=Path); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); asyncio.run(run(args.manifest, args.output))
