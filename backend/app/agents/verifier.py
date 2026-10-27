"""Verifier agent: after the homeowner re-films the room, decide per hazard whether the fix is really there.

Conservative on purpose: an insurer relies on "verified fixed", so it needs visible evidence.
"""
from __future__ import annotations

from pathlib import Path

from openai import AsyncOpenAI

from app.meta.spark import image_part, spark_json

INSTRUCTIONS = (
    "You verify earthquake-safety fixes for a home insurer. You get the BEFORE evidence photo of one hazard (the "
    "object is boxed), the recommended fix, and AFTER photos from a new video of the same room (the same kind of "
    "object is boxed where it was found). Decide: fixed = the recommended fix or an equally effective one is clearly "
    "visible (anchors, straps, brackets, safety cables, or the object was moved out of the danger zone or removed); "
    "not_fixed = the same object is still there in the same hazardous way; cannot_verify = the object or the "
    "attachment points are not visible enough to tell. Only claim fixed when you can see it; when in doubt, choose "
    "cannot_verify. Also say whether the boxed object in the AFTER photos is the same physical object as in BEFORE "
    "(a different lamp or shelf that was boxed by mistake = no). Say what changed between before and after. Do not "
    "assess the building structure."
)


def schema(after_frames: list[int]) -> dict:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["verdict", "confidence", "boxed_is_same_object", "what_changed", "rationale", "best_after_frame"],
        "properties": {
            "verdict": {"type": "string", "enum": ["fixed", "not_fixed", "cannot_verify"]},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "boxed_is_same_object": {"type": "string", "enum": ["yes", "no", "no_box"]},
            "what_changed": {"type": "string"},
            "rationale": {"type": "string"},
            "best_after_frame": {"type": "string", "enum": [str(f) for f in after_frames]},
        },
    }


async def verify_hazard(api: AsyncOpenAI, hazard: dict, before: Path, after: list[tuple[int, Path]],
                        object_found: bool) -> tuple[dict, dict]:
    fix = hazard.get("fix") or {}
    content: list[dict] = [
        {"type": "input_text", "text": (
            f"Hazard: {hazard['object']}, {hazard['relation']} ({hazard['severity']}). {hazard['rationale']} "
            f"Recommended fix: {' '.join(fix.get('actions', [])) or 'secure or relocate it'}. "
            + ("The segmentation model found this kind of object in the new video (boxed)." if object_found else
               "The segmentation model did NOT find this kind of object in the new video; the photos are overview "
               "frames, so check whether it was removed or moved.")
            + " BEFORE:")},
        image_part(before),
    ]
    for frame, path in after:
        content += [{"type": "input_text", "text": f"AFTER, frame {frame}:"}, image_part(path)]
    return await spark_json(api, content, schema([f for f, _ in after]), "fix_verification",
                            instructions=INSTRUCTIONS, effort="medium", max_tokens=4000)
