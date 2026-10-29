"""SAM 3.1 video tracking.

Request shape follows meta-models/meta-model-cookbook 07_sam/01_api_basics (MIT, (c) Meta Platforms, Inc.).
Boxes are read straight from the documented output grammar (docs: sam/reading-segmentation): decoding every
mask with meta_sam_parser saturated the CPU on long videos during our Oct 26 spikes, and boxes are all the
pipeline needs except on evidence frames, so the raw text is kept for decoding those masks later.
"""
from __future__ import annotations

import asyncio
import random
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field

from openai import APIStatusError, AsyncOpenAI

from app.config import PRICES, SAM_MODEL

# Frame markers start a line; an object id follows a line start, a comma or a frame marker. Anchoring matters:
# mask payloads are base85 and may contain text that looks like "<12f>" (docs: sam/reading-segmentation).
TOKEN = re.compile(r"(?m)^<(\d+)f>|(?:^|(?<=,)|(?<=f>))(\d+)<\|box;([^|]*)\|>")
NO_RETRY = {400, 401, 402, 403, 404, 413}       # the request itself is wrong: resending it fails the same way


@dataclass
class Track:
    concept: str
    local_id: str
    boxes: dict[int, list[float]]          # frame -> [x1, y1, x2, y2] in media pixels

    @property
    def key(self) -> str:                   # namespaced: object ordinals restart per SAM request
        return f"{self.concept}#{self.local_id}"

    @property
    def frames(self) -> list[int]:
        return sorted(self.boxes)


@dataclass
class SamResult:
    concept: str
    status: str
    seconds: float
    media: dict
    tracks: list[Track] = field(default_factory=list)
    raw_text: str = ""
    error: str | None = None
    frames_billed: int = 0                  # usage.video_frames_processed, summed over every attempt


def parse_boxes(text: str) -> tuple[dict[str, dict[int, list[float]]], dict]:
    """Per-object, per-frame boxes from `<Nf>id<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..|><|mask;...|>,id<|box...`."""
    tracks: dict[str, dict[int, list[float]]] = defaultdict(dict)
    frame, media = 0, {}
    for match in TOKEN.finditer(text):
        if match.group(1) is not None:
            frame = int(match.group(1))
            continue
        fields = dict(kv.split("=", 1) for kv in match.group(3).split(";") if "=" in kv)
        if not all(k in fields for k in ("x1", "y1", "x2", "y2", "w", "h")):
            continue
        tracks[match.group(2)][frame] = [float(fields[k]) for k in ("x1", "y1", "x2", "y2")]
        media = {"width": int(fields["w"]), "height": int(fields["h"])}
    return dict(tracks), media


def sam_cost(frames: int) -> float:
    return max(frames, PRICES["sam-3.1-min-frames"]) * PRICES["sam-3.1-frame"]


def result_cost(result: SamResult, n_frames: int) -> float:
    """What SAM billed (usage.video_frames_processed), or the per-frame estimate when usage is missing."""
    return result.frames_billed * PRICES["sam-3.1-frame"] if result.frames_billed else sam_cost(n_frames)


def backoff(attempt: int, retry_after: str | None) -> float:
    """Retry-After when the server sends one, else 0.5 s doubling with jitter; never more than 10 s."""
    try:
        wait = float(retry_after) if retry_after else 0.5 * 2 ** attempt + random.random() * 0.5
    except ValueError:
        wait = 1.0
    return min(wait, 10.0)


async def track_concept(api: AsyncOpenAI, file_id: str, concept: str, retries: int = 2) -> SamResult:
    """Segment and track one noun-phrase concept through an uploaded video (one concept per request)."""
    billed = 0
    for attempt in range(retries + 1):
        started = time.perf_counter()
        chunks: list[str] = []
        status, error, retry_after = "incomplete", None, None
        try:
            stream = await api.responses.create(
                model=SAM_MODEL,
                stream=True,
                input=[{"type": "message", "role": "user", "content": [
                    {"type": "input_text", "text": concept},
                    {"type": "input_video", "file_id": file_id}]}],
                metadata={"mask_encoding": "one_bit"},
            )
            async with stream:
                async for event in stream:
                    if event.type == "response.output_text.delta":
                        chunks.append(event.delta)
                    elif event.type in ("response.completed", "response.failed", "response.incomplete"):
                        status = event.response.status
                        error = getattr(event.response, "error", None)
                        billed += getattr(event.response.usage, "video_frames_processed", 0) or 0
                    elif event.type == "error":     # the stream itself failed (e.g. server_shutting_down)
                        status, error = "error", f"{getattr(event, 'code', None)}: {getattr(event, 'message', '')}"
        except APIStatusError as exc:
            status, error = "error", f"{exc.status_code}: {exc.message}"
            if exc.status_code in NO_RETRY:
                break
            retry_after = exc.response.headers.get("retry-after")
        except Exception as exc:  # stream drop / timeout
            status, error = "error", repr(exc)
        if status == "completed" or attempt == retries:
            break
        await asyncio.sleep(backoff(attempt, retry_after))
    text = "".join(chunks)
    boxes, media = parse_boxes(text)
    tracks = [Track(concept, oid, b) for oid, b in boxes.items() if len(b) >= 2]  # drop 1-frame flickers
    return SamResult(concept, status, round(time.perf_counter() - started, 1), media, tracks, text,
                     None if status == "completed" else str(error), billed)
