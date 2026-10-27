"""Fix planner: turns surveyed hazards into practical, cited fixes. Spark looks up FEMA E-74 sections through a
tool (it sees only the catalog of titles up front), so every recommendation traces back to a section it read."""
from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path

from openai import AsyncOpenAI

from app.meta.spark import spark_agent

FEMA_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "fema_e74.json"
COSTS = ["under $20", "$20-100", "$100-500", "over $500"]


@cache
def fema() -> dict:
    data = json.loads(FEMA_PATH.read_text())
    return {"source": data["source"], "sections": {s["id"]: s for s in data["sections"]}}


SECTION_ID = re.compile(r"\d+(?:\.\d+)+")


def normalize_ids(ids: list[str]) -> list[str]:
    """'6.5.2.1 Bookshelves' / '§6.5.2.1' -> '6.5.2.1' (models sometimes echo the catalog line)."""
    return [m.group(0) for i in ids if (m := SECTION_ID.search(str(i)))]


def fema_lookup(section_ids: list[str]) -> dict:
    sections = fema()["sections"]
    section_ids = normalize_ids(section_ids)
    unknown = [s for s in section_ids if s not in sections]
    found = [{k: sections[s][k] for k in ("id", "title", "pages", "summary", "causes", "mitigation")}
             for s in section_ids[:4] if s in sections]
    return {"sections": found, "unknown_ids": unknown}


TOOLS = [{
    "type": "function", "name": "fema_lookup",
    "description": "Read FEMA E-74 guidance (typical damage + mitigation) for up to 4 sections by id.",
    "parameters": {"type": "object", "additionalProperties": False, "required": ["section_ids"],
                   "properties": {"section_ids": {"type": "array", "items": {"type": "string"}}}},
}]


def tools() -> list[dict]:
    """The lookup tool with the valid section ids as an enum, so the model can only ask for sections that exist."""
    tool = json.loads(json.dumps(TOOLS[0]))
    tool["parameters"]["properties"]["section_ids"]["items"]["enum"] = list(fema()["sections"])
    tool["strict"] = True
    return [tool]


def instructions() -> str:
    catalog = "; ".join(f"{s['id']} = {s['title']}" for s in fema()["sections"].values())
    return (
        "You write the fix plan of a non-structural earthquake hazard survey for a homeowner and their insurer. "
        "Before recommending anything, call fema_lookup for the FEMA E-74 sections that match the hazards, and base "
        f"every fix on what those sections say. Available sections: {catalog}. "
        "For each hazard give 1-3 concrete actions a homeowner can follow (what hardware, where to fix it, e.g. "
        "screw into wall studs, not drywall alone), cite the sections you used, say if it is DIY or needs a "
        "professional, and estimate cost and time. Prefer moving an object out of harm's way when that is the "
        "cheapest fix. Never give structural advice; if a fix needs wall or building assessment, say 'ask a "
        "professional'."
    )


def schema(hazard_ids: list[str]) -> dict:
    return {
        "type": "object", "additionalProperties": False, "required": ["fixes"],
        "properties": {"fixes": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["hazard_id", "actions", "fema_sections", "diy", "cost", "minutes", "priority"],
            "properties": {
                "hazard_id": {"type": "string", "enum": hazard_ids},
                "actions": {"type": "array", "items": {"type": "string"}},
                "fema_sections": {"type": "array", "items": {"type": "string"}},
                "diy": {"type": "boolean"},
                "cost": {"type": "string", "enum": COSTS},
                "minutes": {"type": "integer"},
                "priority": {"type": "integer"},
            }}}},
    }


async def plan_fixes(api: AsyncOpenAI, hazards: list[dict], room: dict) -> tuple[dict[str, dict], dict]:
    if not hazards:
        return {}, {"cost_usd": 0.0, "reasoning_summary": [], "tool_calls": [], "seconds": 0, "usage": {}}
    brief = [{k: h[k] for k in ("id", "object", "relation", "severity", "rationale")} for h in hazards]
    content = [{"type": "input_text", "text": f"Room: {room['type']}. Hazards: {json.dumps(brief, ensure_ascii=False)}"}]
    out, meta = await spark_agent(api, content, schema([h["id"] for h in hazards]), "fix_plan",
                                  instructions=instructions(), tools=tools(), handlers={"fema_lookup": fema_lookup},
                                  effort="low", max_rounds=3)
    sections = fema()["sections"]
    read = {s for c in meta["tool_calls"] for s in normalize_ids(json.loads(c["arguments"]).get("section_ids", []))}
    fixes = {}
    for fix in out["fixes"]:
        # keep only citations the agent actually read (and that exist), so the report never cites unseen guidance
        cited = [s for s in normalize_ids(fix["fema_sections"]) if s in sections and s in read]
        fixes[fix["hazard_id"]] = {**fix, "fema_sections": [
            {"id": s, "title": sections[s]["title"], "pages": sections[s]["pages"], "url": sections[s]["url"]}
            for s in cited]}
    return fixes, meta
