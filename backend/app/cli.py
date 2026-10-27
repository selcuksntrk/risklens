"""Command line entry point.

    uv run --env-file ../../.env python -m app.cli scan path/to/room.mp4 [--narration "bedroom, kids sleep here"]
"""
from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from app.pipeline import run_scan


def main() -> None:
    parser = argparse.ArgumentParser(prog="risklens")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="survey one room video")
    scan.add_argument("video", type=Path)
    scan.add_argument("--narration", default=None)
    verify = sub.add_parser("verify", help="re-filmed video after fixes -> per-hazard verdicts")
    verify.add_argument("scan_id")
    verify.add_argument("video", type=Path)
    args = parser.parse_args()

    if args.command == "verify":
        from app.config import SCANS_DIR
        from app.verify import run_verify
        v = asyncio.run(run_verify(SCANS_DIR / args.scan_id, args.video, f"cli{int(time.time())}", lambda s, d: print(f"[{s}] {d}")))
        print(f"\nFixed {v['fixed']}/{len(v['results'])} · risk {v['risk_score_before']} -> {v['risk_score_after']} "
              f"· ${v['cost_usd']:.3f} · {v['seconds']} s")
        for hid, r in v["results"].items():
            print(f"  {hid}: {r['verdict']:<13} ({r['confidence']}) {r['what_changed']}")
        return
    report = asyncio.run(run_scan(args.video, args.narration))
    print(f"\nRisk score {report['room']['risk_score']} · {len(report['hazards'])} hazards · "
          f"${report['cost_usd']['total']:.3f} · {report['seconds']} s")
    for h in report["hazards"]:
        print(f"  [{h['severity']:>6}] {h['relation']:<20} {h['object']} (mark {h['mark']}): {h['rationale']}")


if __name__ == "__main__":
    main()
