"""Publish ONLY registered sample videos into the public example allowlist.

`examples/sources.json` is the committed registry: one row per sample with its rights statement and the SHA-256
of the exact source video. A personal scan can never be published by passing its ID: the video handed to this
script must hash to a registered row, and the report must have been produced from that same file.

Usage:
  python scripts/package_example.py <example_id> <scan_dir> <video> --events <events.json>
  python scripts/package_example.py --catalog          # rebuild catalog.json from packaged examples
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'examples' / 'sources.json'
OUT = ROOT / 'examples' / 'generated'
SCENES = ROOT / 'scripts' / 'scenes'
MATCHES = ROOT / 'examples' / 'matches'
PUBLIC_FIELDS = ('id', 'scan_id', 'kind', 'title', 'description', 'license', 'license_url', 'source_url',
                 'synthetic', 'modifications', 'context')


def registry() -> list[dict]:
    return json.loads(REGISTRY.read_text())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def answer_key(row: dict, report: dict) -> dict | None:
    """Designed hazards from the scene bible, plus the author's finding-to-hazard match (committed, reviewable)."""
    if not row.get('scene'):
        return None
    bible = json.loads((SCENES / f"{row['scene']}.json").read_text())
    match_path = MATCHES / f"{row['id']}.json"
    match = json.loads(match_path.read_text()) if match_path.exists() else {'matches': {}, 'note': 'Not yet matched.'}
    if match.get('source_sha256') not in (None, report['provenance']['source_sha256']):
        raise SystemExit(f'{match_path} was written for a different run.')
    found: dict[str, list[str]] = {}
    for finding, hazard in match['matches'].items():
        if hazard:
            found.setdefault(hazard, []).append(finding)
    hazards = [{**h, 'matched_finding': (found.get(h['id']) or [None])[0], 'matched_findings': found.get(h['id'], [])}
               for h in bible['answer_key']]
    finding_ids = {h['id'] for h in report['hazards']}
    extras = sorted(finding_ids - set(match['matches']))
    unmatched_listed = sorted(f for f, h in match['matches'].items() if not h)
    return {'designed': len(hazards), 'matched': sum(1 for h in hazards if h['matched_finding']),
            'hazards': hazards, 'controls': [{**c, 'flagged': match.get('controls_flagged', {}).get(c['object'])} for c in bible.get('controls', [])],
            'other_findings': extras + unmatched_listed, 'method': match.get('method', 'author-matched'),
            'note': match.get('note', '')}


def package(example_id: str, scan: Path, video: Path, events: Path | None):
    row = next((r for r in registry() if r['id'] == example_id), None)
    if not row:
        raise SystemExit(f'{example_id} is not in {REGISTRY}. Nothing published.')
    digest = sha256(video)
    report = json.loads((scan / 'report.json').read_text())
    if digest != row['sha256'] or report['provenance']['source_sha256'] != digest:
        raise SystemExit('Video or report does not match the registered source hash. Nothing published.')
    if report.get('schema_version') != 2:
        raise SystemExit('Run the current pipeline first; legacy results are not upgraded or presented as current.')
    out = OUT / row['scan_id']
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    run_id = report['scan_id']
    report['scan_id'] = row['scan_id']   # only the locator changes; provenance and observations stay intact
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    for folder in ('evidence', 'marked'):
        if (scan / folder).exists():
            shutil.copytree(scan / folder, out / folder)
    shutil.copyfile(video, out / 'source.mp4')
    if events:
        (out / 'events.json').write_text(events.read_text().replace(f'"{run_id}"', f'"{row["scan_id"]}"'))
    order = {'high': 0, 'medium': 1, 'low': 2}
    first = min(report['hazards'], key=lambda h: (order[h['severity']], h['evidence_status'] != 'observed'), default=None)
    poster = out / (first['evidence_image'] if first else 'evidence/h1.jpg')
    if poster.exists():
        shutil.copyfile(poster, out / 'poster.jpg')
    key = answer_key(row, report)
    if key:
        (out / 'answer_key.json').write_text(json.dumps(key, indent=2) + '\n')
    (out / 'ATTRIBUTION.json').write_text(json.dumps({k: row.get(k) for k in PUBLIC_FIELDS} | {'source_sha256': digest}, indent=2) + '\n')
    print(out)


def counts(report: dict) -> dict:
    hz = report['hazards']
    return {'high': sum(h['severity'] == 'high' for h in hz), 'medium': sum(h['severity'] == 'medium' for h in hz),
            'low': sum(h['severity'] == 'low' for h in hz), 'needs_check': sum(h['evidence_status'] != 'observed' for h in hz)}


def build_catalog():
    rows = []
    for row in registry():
        folder = OUT / row['scan_id']
        if not (folder / 'report.json').is_file():
            continue
        report = json.loads((folder / 'report.json').read_text())
        key_path = folder / 'answer_key.json'
        key = json.loads(key_path.read_text()) if key_path.exists() else None
        order = {'high': 0, 'medium': 1, 'low': 2}
        top = min(report['hazards'], key=lambda h: (order[h['severity']], h['evidence_status'] != 'observed'), default=None)
        rows.append({k: row.get(k) for k in PUBLIC_FIELDS} | {
            'top_finding': {k: top[k] for k in ('id', 'object', 'severity', 'relation', 'evidence_status')} if top else None,
            'room': report['room']['type'], 'findings': len(report['hazards']), 'counts': counts(report),
            'duration_s': row.get('duration_s'), 'seconds': report.get('seconds'),
            'cost_usd': round(report.get('cost_usd', {}).get('total', 0), 3),
            'has_video': (folder / 'source.mp4').is_file(), 'has_poster': (folder / 'poster.jpg').is_file(),
            'has_replay': (folder / 'events.json').is_file(), 'answer_key': key,
            'source_sha256': row['sha256']})
    (OUT / 'catalog.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(f'catalog: {[r["id"] for r in rows]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('example_id', nargs='?'); parser.add_argument('scan', type=Path, nargs='?')
    parser.add_argument('video', type=Path, nargs='?'); parser.add_argument('--events', type=Path)
    parser.add_argument('--catalog', action='store_true')
    args = parser.parse_args()
    if not args.catalog:
        if not (args.example_id and args.scan and args.video):
            parser.error('example_id, scan and video are required')
        package(args.example_id, args.scan, args.video, args.events)
    build_catalog()
