"""Model IDs, prices and pipeline limits in one place."""
from __future__ import annotations

import os
from pathlib import Path

META_BASE_URL = "https://api.meta.ai/v1"
SAM_MODEL = "sam-3.1"
SPARK_MODEL = os.environ.get("SPARK_MODEL", "muse-spark-1.3")

# USD, from knowledge/meta-platform/pricing-and-budget.md (verified 2026-10-26)
PRICES = {
    "muse-spark-1.3": {"input": 1.25e-6, "cached": 0.15e-6, "output": 4.25e-6},
    "muse-spark-1.3-contributor": {"input": 0.10e-6, "cached": 0.002e-6, "output": 0.20e-6},
    "sam-3.1-frame": 0.20 / 1000,
    "sam-3.1-min-frames": 50,
}

PROXY_FPS = 5           # SAM bills per frame: 60 s clip = 300 frames per concept
PROXY_HEIGHT = 720
MAX_CONCEPTS = 8
KEYFRAMES = 6           # frames the planner/surveyor see
SAM_CONCURRENCY = 4

SCANS_DIR = Path(os.environ.get("RISKLENS_SCANS", Path(__file__).resolve().parents[2] / "scans"))
