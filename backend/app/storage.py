"""Atomic JSON snapshots; readers never observe partial reports."""
import json
import os
from collections.abc import Callable
import uuid
from pathlib import Path


# Deployment sets this to Volume.commit. Local snapshots use ordinary fsync/rename.
COMMIT: Callable[[], None] = lambda: None


def durable():
    COMMIT()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    try:
        with temporary.open('w') as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        durable()
    finally:
        temporary.unlink(missing_ok=True)
