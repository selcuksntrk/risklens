"""API clients. Keys come from the environment only and never leave the server."""
from __future__ import annotations

import os

from openai import AsyncOpenAI

from app.config import META_BASE_URL


def meta_client() -> AsyncOpenAI:
    key = os.environ.get("MODEL_API_KEY")
    if not key:
        raise SystemExit("MODEL_API_KEY is not set. Run with: uv run --env-file ../../.env ...")
    return AsyncOpenAI(base_url=META_BASE_URL, api_key=key, timeout=600)


async def upload_video(api: AsyncOpenAI, path) -> str:
    # Meta deletes the home video after a day; SAM only needs it during the scan (allowed range 1 h - 30 days)
    uploaded = await api.files.create(file=(path.name, path.read_bytes(), "video/mp4"), purpose="user_data",
                                      expires_after={"anchor": "created_at", "seconds": 86400})
    return uploaded.id
