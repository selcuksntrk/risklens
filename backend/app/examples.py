"""Explicitly packaged, licensed examples. Never infer publication from personal scans."""
import json
import re
from app import config


def catalog() -> list[dict]:
    path = config.EXAMPLES_DIR / 'catalog.json'
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [row for row in data if re.fullmatch(r'[a-zA-Z0-9_-]+', row.get('id', '')) and
            row.get('scan_id', '').isalnum() and (config.EXAMPLES_DIR / row['scan_id'] / 'report.json').is_file()]


def find(example_id: str) -> dict | None:
    return next((r for r in catalog() if r['id'] == example_id), None)


def by_scan(scan_id: str):
    return next((r for r in catalog() if r['scan_id'] == scan_id), None)


def root(row):
    return config.EXAMPLES_DIR / row['scan_id']
