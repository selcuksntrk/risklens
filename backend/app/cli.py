"""Offline screening, verification and explicit administrative recovery. Never log room text."""
import argparse
import asyncio
import re
import time
from pathlib import Path
from app import access, config, guard, jobs
from app.pipeline import run_scan
from app.storage import write_json


def main():
    parser = argparse.ArgumentParser(prog='risklens')
    sub = parser.add_subparsers(dest='command', required=True)
    scan = sub.add_parser('scan')
    scan.add_argument('video', type=Path); scan.add_argument('--narration', default=None)
    scan.add_argument('--id'); scan.add_argument('--spark-only', action='store_true')
    verify = sub.add_parser('verify')
    verify.add_argument('scan_id'); verify.add_argument('video', type=Path); verify.add_argument('--hazard-id')
    claim = sub.add_parser('claim-legacy', help='Administrator only: copy ownership from an existing browser-owned scan')
    claim.add_argument('scan_id'); claim.add_argument('--owner-from-scan', required=True)
    sub.add_parser('cleanup')
    args = parser.parse_args()
    if args.command == 'cleanup':
        print(f'Cleaned {len(guard.purge_old_media())} scan folders'); return
    if args.command == 'claim-legacy':
        if not args.scan_id.isalnum() or not args.owner_from_scan.isalnum(): parser.error('Invalid ID')
        root = config.SCANS_DIR / args.scan_id
        owner = access.metadata(config.SCANS_DIR/args.owner_from_scan).get('owner_sha256', '')
        if not root.is_dir() or not re.fullmatch('[a-f0-9]{64}', owner): parser.error('Valid existing owner required')
        meta = access.metadata(root)
        if meta.get('owner_sha256'): parser.error('Existing ownership is not overwritten')
        write_json(root/'meta.json', {**meta, 'owner_sha256': owner, 'created_at_unix': time.time(), 'admin_claimed': True})
        print('Legacy report assigned. Original report and evidence were not changed.'); return
    if args.command == 'verify':
        from app.verify import run_verify
        if not args.scan_id.isalnum(): parser.error('Invalid ID')
        verify_id = 'cli' + jobs.new_scan_id()
        folder = config.SCANS_DIR/args.scan_id/'verify'/verify_id
        folder.mkdir(parents=True)
        access.new_metadata(folder, '', hazard_id=args.hazard_id)
        value = asyncio.run(run_verify(config.SCANS_DIR/args.scan_id, args.video, verify_id, lambda s,d: print(f'[{s}]'), args.hazard_id))
        print(f"{value['fixed']} visible changes confirmed / {len(value['results'])} findings checked · ${value['cost_usd']:.3f}")
        return
    scan_id = args.id or jobs.new_scan_id()
    if not scan_id.isalnum(): parser.error('Invalid ID')
    root = config.SCANS_DIR/scan_id
    if root.exists(): parser.error('Scan ID already exists; no report was overwritten')
    root.mkdir(parents=True)
    access.new_metadata(root, '', origin='offline')
    report = asyncio.run(run_scan(args.video, args.narration, scan_id=scan_id, tracking=not args.spark_only))
    print(f"{scan_id} · {report['assessment']['status']} · {len(report['hazards'])} findings · ${report['cost_usd']['total']:.3f} · {report['seconds']} s")

if __name__ == '__main__':
    main()
