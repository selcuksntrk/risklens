"""Surveyor agent: Spark reasons over set-of-marks keyframes and reports hazards tied to tracked object IDs.

Relation schema and instructions evolved from the Oct 26 spatial spike (11/15 raw, ~14/15 adjudicated vs Hypersim 3D truth).
"""
from __future__ import annotations

from pathlib import Path

from openai import AsyncOpenAI

from app.hazards import RELATIONS, SEVERITIES
from app.meta.spark import image_part, spark_json

INSTRUCTIONS = (
    "You are a non-structural earthquake hazard surveyor for a home insurer. The images are frames from one room "
    "video. Tracked objects carry a colored box and a number (the mark). For each hazard, give the mark of the object "
    "that causes it (or 'none' if it is unmarked, and then name it), the relation, a severity and the frame that "
    "shows it best. Relations: " + "; ".join(f"{k} = {v}" for k, v in RELATIONS.items()) + ". "
    "Severity: high = heavy enough to seriously injure a person in a likely spot (bed, exit, play area); medium = "
    "can injure or block but less likely; low = light objects, damage or minor risk (plants, small decor and light "
    "lamps are low unless they are heavy and directly over a bed). Report what a professional surveyor would list, "
    "not every object. Only report what is visible; one entry per object and relation; "
    "say in the rationale what you saw (position, size, anchoring if visible). If you see straps, brackets or other "
    "anchoring, do not report tip-over for that object. Do not assess the building structure."
)


def schema(marks: list[str], frames: list[int]) -> dict:
    return {
        "type": "object", "additionalProperties": False, "required": ["room_summary", "hazards"],
        "properties": {
            "room_summary": {"type": "string"},
            "hazards": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "required": ["mark", "object", "relation", "severity", "evidence_frame", "rationale"],
                "properties": {
                    "mark": {"type": "string", "enum": [*marks, "none"]},
                    "object": {"type": "string"},
                    "relation": {"type": "string", "enum": list(RELATIONS)},
                    "severity": {"type": "string", "enum": list(SEVERITIES)},
                    "evidence_frame": {"type": "string", "enum": [str(f) for f in frames]},
                    "rationale": {"type": "string"},
                }}},
        },
    }


async def survey(api: AsyncOpenAI, marked: list[tuple[int, Path]], marks: list[str], plan: dict,
                 narration: str | None = None) -> tuple[dict, dict]:
    content: list[dict] = [{"type": "input_text", "text": (
        f"Room type (from the planner): {plan['room_type']}; sleeping area: {plan['sleeping_area']}; "
        f"exit visible: {plan['exit_visible']}. " + (f"Occupant narration: {narration}. " if narration else "")
        + "Survey this room.")}]
    for frame, path in marked:
        content += [{"type": "input_text", "text": f"Frame {frame}:"}, image_part(path)]
    out, meta = await spark_json(api, content, schema(marks, [f for f, _ in marked]), "hazard_survey",
                                 instructions=INSTRUCTIONS, effort="medium")
    return out, meta
