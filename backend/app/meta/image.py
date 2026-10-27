"""Muse Image fix cards: edit the user's own evidence frame to show the hazard after the recommended fix."""
from __future__ import annotations

import base64
import time
from pathlib import Path

from openai import AsyncOpenAI
from PIL import Image

IMAGE_MODEL = "muse-image-1.0"
USD_PER_IMAGE = 0.01


def fix_prompt(room_type: str, hazard: dict) -> str:
    action = hazard["fix"]["actions"][0] if hazard.get("fix") and hazard["fix"]["actions"] else "secure it safely"
    return (
        f"Edit this photo of a {room_type.replace('_', ' ')}. Show the {hazard['object']} after this earthquake-safety "
        f"fix: {action} Make the fix clearly visible and prominent (metal brackets, straps, safety cables or the new position). Keep the camera angle, "
        "lighting, walls and every other object exactly as they are. Photorealistic, no text, no arrows."
    )


def crop_around(frame: Path, box: list[float] | None, out: Path, pad: float = 0.5, min_side: int = 320) -> Path:
    """Crop the frame around the hazard's SAM box (padded) so the fix is big enough to see on a phone."""
    image = Image.open(frame).convert("RGB")
    if box:
        x1, y1, x2, y2 = box
        w, h = max(x2 - x1, min_side), max(y2 - y1, min_side)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        half_w, half_h = w * (1 + pad) / 2, h * (1 + pad) / 2
        image = image.crop((max(0, cx - half_w), max(0, cy - half_h),
                            min(image.width, cx + half_w), min(image.height, cy + half_h)))
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, quality=92)
    return out


async def fix_card(api: AsyncOpenAI, frame: Path, prompt: str, out: Path) -> dict:
    started = time.perf_counter()
    response = await api.images.edit(
        model=IMAGE_MODEL, prompt=prompt, n=1,
        image=(frame.name, frame.read_bytes(), "image/jpeg"),
        extra_body={"output_format": "jpeg", "reasoning_strength": "low",
                    "tool_enablement": {"enable_web_search": False, "enable_shell": False}},
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(response.data[0].b64_json))
    return {"model": IMAGE_MODEL, "seconds": round(time.perf_counter() - started, 1), "cost_usd": USD_PER_IMAGE,
            "prompt": prompt}
