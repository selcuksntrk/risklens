"""Planner agent: Spark looks at the room and decides what SAM should track (SAM 3 Agent pattern).

The Oct 26 spikes showed concept wording drives SAM precision ("television" also matched monitors), so the
concepts are chosen per room instead of from a fixed list.
"""
from __future__ import annotations

from pathlib import Path

from openai import AsyncOpenAI

from app.config import MAX_CONCEPTS
from app.hazards import ROOM_TYPES
from app.meta.spark import image_part, spark_json

INSTRUCTIONS = (
    "You plan an earthquake non-structural hazard survey of one room filmed on a phone. Look at the frames and "
    "decide which objects a segmentation model should track. Output short, concrete noun phrases, one object "
    "type each, with no spatial words, verbs, lists or negation (good: 'bookshelf', 'wardrobe', 'wall mirror', "
    "'framed picture', 'flat screen tv', 'pendant lamp', 'bed', 'door'). Prefer objects that can fall, tip, slide "
    "or shatter, plus the anchors the survey needs to reason about: always include 'bed' or 'sofa' if someone may "
    "sleep there and 'door' if an exit is visible. At most "
    f"{MAX_CONCEPTS} concepts, most important first. For each, give up to 2 alternate wordings the segmentation "
    "model can try if the first finds nothing (e.g. 'bookshelf' -> 'shelving unit', 'shelves'). "
    "Never assess the building structure."
)

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["room_type", "sleeping_area", "exit_visible", "concepts"],
    "properties": {
        "room_type": {"type": "string", "enum": ROOM_TYPES},
        "sleeping_area": {"type": "boolean"},
        "exit_visible": {"type": "boolean"},
        "concepts": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["concept", "alternates", "reason"],
            "properties": {"concept": {"type": "string"}, "reason": {"type": "string"},
                           "alternates": {"type": "array", "items": {"type": "string"}}}}},
    },
}


def clean_concept(text: str) -> str:
    return " ".join(text.lower().replace(",", " ").split())[:40]


async def plan(api: AsyncOpenAI, keyframes: list[Path], narration: str | None = None) -> tuple[dict, dict]:
    note = f"Occupant narration: {narration}" if narration else "No narration."
    out, meta = await spark_json(api, [{"type": "input_text", "text": f"Plan the survey. {note}"},
                                       *(image_part(p) for p in keyframes)],
                                 SCHEMA, "survey_plan", instructions=INSTRUCTIONS, effort="low", max_tokens=4000)
    seen, concepts = set(), []
    for item in out["concepts"]:
        concept = clean_concept(item["concept"])
        if concept and concept not in seen:
            seen.add(concept)
            alternates = [a for a in map(clean_concept, item["alternates"]) if a and a != concept][:2]
            concepts.append({"concept": concept, "alternates": alternates, "reason": item["reason"]})
    out["concepts"] = concepts[:MAX_CONCEPTS]
    return out, meta
