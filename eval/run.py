"""Run frozen room-split inputs through full and Spark-only pipelines; never include private media in exports.
Usage from backend: python ../eval/run.py ../eval/private/manifest.json --output ../eval/results/run1
Model calls spend the normal persisted daily budget. No contributor model is accepted.
"""
import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path
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
    return rooms


async def run(manifest_path, output):
    manifest = json.loads(manifest_path.read_text()); validate_manifest(manifest)
    if output.exists(): raise ValueError('Use a new output directory; evaluation runs are immutable')
    output.mkdir(parents=True)
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    summary = {'manifest_sha256': digest, 'version': config.APP_VERSION, 'runs': []}
    for variant in ('spark_only', 'full'):
        baselines = {}
        for row in sorted(manifest['clips'], key=lambda r: r['case'] != 'A0'):
            src = (manifest_path.parent/row['video']).resolve()
            source_hash = hashlib.sha256(src.read_bytes()).hexdigest()
            if source_hash != row['sha256']: raise ValueError('Video changed since observations were frozen')
            entry = {k: row[k] for k in ('clip_id', 'room_id', 'split', 'case')}
            entry.update(variant=variant, source_sha256=source_hash, status='error')
            try:
                if row['case'] == 'A0':
                    scan_id = 'eval' + jobs.new_scan_id()
                    root = config.SCANS_DIR/scan_id; root.mkdir(parents=True)
                    access.new_metadata(root, '', origin='offline_evaluation')
                    report = await run_scan(src, row.get('context'), scan_id=scan_id, tracking=variant == 'full')
                    baselines[row['clip_id']] = root
                    entry.update(status='done', assessment=report['assessment']['status'], seconds=report['seconds'],
                                 cost_usd=report['cost_usd']['total'], report=report)
                else:
                    # Baseline automatic verification intentionally abstains without tracking.
                    root = baselines[row['baseline_clip_id']]
                    verify_id = 'eval' + jobs.new_scan_id()
                    folder = root/'verify'/verify_id; folder.mkdir(parents=True)
                    access.new_metadata(folder, '', origin='offline_evaluation')
                    result = await run_verify(root, src, verify_id, lambda *_: None, row.get('hazard_id'))
                    entry.update(status='done', seconds=result['seconds'], cost_usd=result['cost_usd'], verification=result)
            except Exception as exc:
                entry['error_type'] = type(exc).__name__  # no private exception text or paths
            summary['runs'].append(entry)
            write_json(output/'runs.private.json', summary)
    print('Run saved privately. Human matching is required before computing finding metrics.')

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1]/'.env')
    parser = argparse.ArgumentParser(); parser.add_argument('manifest', type=Path); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); asyncio.run(run(args.manifest, args.output))
