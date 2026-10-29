"""Muse Image fix cards: edit the user's own evidence frame to show the hazard after the recommended fix."""
from __future__ import annotations

import base64
import time
from pathlib import Path

import httpx
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


class ImageRefused(Exception):
    """Muse Image's content-safety filter declined the edit (400 content_policy_violation)."""


async def fix_card(api: AsyncOpenAI, frame: Path, prompt: str, out: Path) -> dict:
    """JSON body, not the SDK's multipart upload: multipart silently ignores output_format and the nested
    tool_enablement object (docs: image-generation), so the image could come back as webp with tools on."""
    started = time.perf_counter()
    image_url = "data:image/jpeg;base64," + base64.b64encode(frame.read_bytes()).decode("ascii")
    async with httpx.AsyncClient(timeout=180) as http:
        response = await http.post(f"{str(api.base_url).rstrip('/')}/images/edits",
                                   headers={"Authorization": f"Bearer {api.api_key}"},
                                   json={"model": IMAGE_MODEL, "prompt": prompt, "n": 1,
                                         "images": [{"image_url": image_url}],
                                         "output_format": "jpeg", "reasoning_strength": "low",
                                         "tool_enablement": {"enable_image_search": False,
                                                             "enable_web_search": False, "enable_shell": False}})
    if response.status_code == 400 and "content_policy_violation" in response.text:
        raise ImageRefused("Muse Image declined to edit this photo.")
    response.raise_for_status()
    body = response.json()
    if body.get("output_format", "jpeg") != "jpeg":
        raise RuntimeError(f"expected jpeg, got {body.get('output_format')}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(body["data"][0]["b64_json"]))
    return {"model": IMAGE_MODEL, "seconds": round(time.perf_counter() - started, 1), "cost_usd": USD_PER_IMAGE,
            "prompt": prompt}
