"""SAM 3.1 video tracking.

Request shape follows meta-models/meta-model-cookbook 07_sam/01_api_basics (MIT, (c) Meta Platforms, Inc.).
Boxes are read straight from the documented output grammar (docs: sam/reading-segmentation): decoding every
mask with meta_sam_parser saturated the CPU on long videos during our Oct 26 spikes, and boxes are all the
pipeline needs except on evidence frames, so the raw text is kept for decoding those masks later.
"""
from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from app.config import PRICES, SAM_MODEL

TOKEN = re.compile(r"<(\d+)f>|(\d+)<\|box;([^|]*)\|>")


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


def parse_boxes(text: str) -> tuple[dict[str, dict[int, list[float]]], dict]:
    """Per-object, per-frame boxes from `<Nf>id<|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..|><|mask;...|>,id<|box...`."""
    tracks: dict[str, dict[int, list[float]]] = defaultdict(dict)
    frame, media = 0, {}
    for match in TOKEN.finditer(text):
        if match.group(1) is not None:
            frame = int(match.group(1))
            continue
        fields = dict(kv.split("=", 1) for kv in match.group(3).split(";") if "=" in kv)
        tracks[match.group(2)][frame] = [float(fields[k]) for k in ("x1", "y1", "x2", "y2")]
        media = {"width": int(fields["w"]), "height": int(fields["h"])}
    return dict(tracks), media


def sam_cost(frames: int) -> float:
    return max(frames, PRICES["sam-3.1-min-frames"]) * PRICES["sam-3.1-frame"]


async def track_concept(api: AsyncOpenAI, file_id: str, concept: str, retries: int = 1) -> SamResult:
    """Segment and track one noun-phrase concept through an uploaded video (one concept per request)."""
    for attempt in range(retries + 1):
        started = time.perf_counter()
        chunks: list[str] = []
        status, error = "incomplete", None
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
        except Exception as exc:  # stream drop / server error: retry once, then report
            status, error = "error", repr(exc)
        if status == "completed" or attempt == retries:
            break
    text = "".join(chunks)
    boxes, media = parse_boxes(text)
    tracks = [Track(concept, oid, b) for oid, b in boxes.items() if len(b) >= 2]  # drop 1-frame flickers
    return SamResult(concept, status, round(time.perf_counter() - started, 1), media, tracks, text,
                     None if status == "completed" else str(error))
