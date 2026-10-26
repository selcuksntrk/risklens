"""Command line entry point.

    uv run --env-file ../../.env python -m app.cli scan path/to/room.mp4 [--narration "bedroom, kids sleep here"]
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.pipeline import run_scan


def main() -> None:
    parser = argparse.ArgumentParser(prog="risklens")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="survey one room video")
    scan.add_argument("video", type=Path)
    scan.add_argument("--narration", default=None)
    args = parser.parse_args()

    report = asyncio.run(run_scan(args.video, args.narration))
    print(f"\nRisk score {report['room']['risk_score']} · {len(report['hazards'])} hazards · "
          f"${report['cost_usd']['total']:.3f} · {report['seconds']} s")
    for h in report["hazards"]:
        print(f"  [{h['severity']:>6}] {h['relation']:<20} {h['object']} (mark {h['mark']}): {h['rationale']}")


if __name__ == "__main__":
    main()
