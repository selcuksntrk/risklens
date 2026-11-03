"""Muse Image fix cards: edit the user's own evidence frame to show the hazard after the recommended fix."""
from __future__ import annotations

import base64
import time
from pathlib import Path

import httpx
from openai import AsyncOpenAI
from PIL import Image, ImageDraw, ImageFont

from app.report.contracts import sourced_fix
from app import guard

IMAGE_MODEL = "muse-image-1.0"
USD_PER_IMAGE = 0.01


def fix_prompt(room_type: str, hazard: dict) -> str:
    if not sourced_fix(hazard):
        raise ValueError("A source-linked recommendation is required before generating an illustration.")
    action = hazard["fix"]["actions"][0]
    return (
        f"Edit this photo of a {room_type.replace('_', ' ')}. Show the {hazard['object']} after this earthquake-safety "
        f"precaution: {action} Illustrate only this recommendation. Do not invent attachment hardware, hardware counts, hidden anchors or a completed fix when the recommendation requests an inspection. Keep the camera angle, "
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


def label_illustration(path: Path) -> None:
    image = Image.open(path).convert("RGB")
    draw = ImageDraw.Draw(image)
    size = max(12, image.width // 40)
    font = ImageFont.load_default(size=size)
    label = "AI-generated illustration - not verification"
    while draw.textlength(label, font=font) > image.width - 12 and size > 7:
        size -= 1
        font = ImageFont.load_default(size=size)
    height = size + 20
    draw.rectangle((0, image.height - height, image.width, image.height), fill="#17212c")
    draw.text((6, image.height - height + 8), label, font=font, fill="white")
    image.save(path, quality=92)


async def fix_card(api: AsyncOpenAI, frame: Path, prompt: str, out: Path) -> dict:
    """JSON body, not the SDK's multipart upload: multipart silently ignores output_format and the nested
    tool_enablement object (docs: image-generation), so the image could come back as webp with tools on."""
    started = time.perf_counter()
    image_url = "data:image/jpeg;base64," + base64.b64encode(frame.read_bytes()).decode("ascii")
    with guard.meter('image', USD_PER_IMAGE) as charge:
      async with httpx.AsyncClient(timeout=180) as http:
          response = await http.post(f"{str(api.base_url).rstrip('/')}/images/edits",
                                     headers={"Authorization": f"Bearer {api.api_key}"},
                                     json={"model": IMAGE_MODEL, "prompt": prompt, "n": 1,
                                           "images": [{"image_url": image_url}],
                                           "output_format": "jpeg", "reasoning_strength": "low",
                                           "tool_enablement": {"enable_image_search": False,
                                                               "enable_web_search": False, "enable_shell": False}})
          if response.is_success:
              charge.settle(USD_PER_IMAGE)
    if response.status_code == 400 and "content_policy_violation" in response.text:
        raise ImageRefused("Muse Image declined to edit this photo.")
    response.raise_for_status()
    body = response.json()
    if body.get("output_format", "jpeg") != "jpeg":
        raise RuntimeError(f"expected jpeg, got {body.get('output_format')}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(body["data"][0]["b64_json"]))
    label_illustration(out)
    return {"model": IMAGE_MODEL, "seconds": round(time.perf_counter() - started, 1), "cost_usd": USD_PER_IMAGE,
            "prompt": prompt}
