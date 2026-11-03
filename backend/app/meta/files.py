"""Track remote uploads for best-effort deletion; provider expiry remains the fallback."""
import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from app import config
from app.meta.clients import upload_video
from app.storage import write_json

PROCESS = uuid.uuid4().hex


def pending_path(file_id: str) -> Path:
    import hashlib
    return config.SCANS_DIR / "_remote_cleanup" / (hashlib.sha256(file_id.encode()).hexdigest() + ".json")


async def remove(api, file_id: str) -> bool:
    try:
        await asyncio.wait_for(api.files.delete(file_id), timeout=10)
    except Exception as exc:
        if getattr(exc, 'status_code', None) == 404:
            pending_path(file_id).unlink(missing_ok=True)
            return True
        # File IDs only: never persist the video, narration or credentials in cleanup records.
        write_json(pending_path(file_id), {"file_id": file_id})
        return False
    pending_path(file_id).unlink(missing_ok=True)
    return True


@asynccontextmanager
async def uploaded_video(api, proxy: Path, root: Path):
    file_id = await upload_video(api, proxy)
    write_json(pending_path(file_id), {"file_id": file_id, "active_process": PROCESS})
    write_json(root / "remote_file.json", {"file_id": file_id, "expiry_requested_seconds": 86400})
    try:
        yield file_id
    finally:
        cleanup = asyncio.create_task(remove(api, file_id))
        try:
            await asyncio.shield(cleanup)
        except asyncio.CancelledError:
            await cleanup
            raise


async def retry_pending(api):
    for path in (config.SCANS_DIR / "_remote_cleanup").glob("*.json"):
        try:
            record = json.loads(path.read_text())
            if record.get('active_process') == PROCESS:
                continue
            file_id = record["file_id"]
            await remove(api, file_id)
        except (OSError, ValueError, KeyError):
            continue
