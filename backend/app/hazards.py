"""Hazard taxonomy (earthquake non-structural first). RiskLens never assesses the building structure."""
from __future__ import annotations

RELATIONS = {
    "above_sleeping_area": "Mounted or standing so it can fall onto a bed or sofa where someone sleeps",
    "blocks_exit": "Can fall or slide into a door or escape path",
    "tall_tip_over": "Tall, top-heavy furniture that can tip over if not anchored to the wall",
    "glass_breakage": "Mirror, glass door or large glass surface that can shatter",
    "heavy_falling_object": "Heavy item (TV, appliance, objects on high shelves) that can slide or fall",
    "other": "Another non-structural earthquake hazard (explain in the rationale)",
}
SEVERITIES = {"high": 0.45, "medium": 0.25, "low": 0.10}  # chance-like weights for the room score
ROOM_TYPES = ["bedroom", "kids_room", "living_room", "kitchen", "hallway", "office", "bathroom", "other"]

DISCLAIMER = ("RiskLens surveys non-structural hazards (furniture, fixtures, contents) only. It does not assess the "
              "structural safety of the building.")


def risk_score(hazards: list[dict]) -> int:
    """0-100 room score = 100 * (1 - prod(1 - w)): grows with each hazard but never saturates at a handful."""
    safe = 1.0
    for h in hazards:
        safe *= 1 - SEVERITIES[h["severity"]]
    return round(100 * (1 - safe))
