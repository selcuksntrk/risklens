"""Read-only compatibility: absence of evidence is never upgraded on old reports."""
from copy import deepcopy


def adapt_report(value: dict) -> dict:
    report = deepcopy(value)
    report.setdefault("schema_version", 1)
    report.setdefault("assessment", {"status": "legacy_unknown", "stages": {},
        "warnings": ["Historical report: evidence completeness was not recorded. Re-scan for the current assessment."]})
    report.setdefault("context", {"occupant_narration": "", "source": "unknown"})
    for hazard in report.get("hazards", []):
        hazard.setdefault("evidence_status", "legacy_unknown")
        hazard.setdefault("evidence_observation", "Not recorded in this historical report.")
        hazard.setdefault("next_view_request", "Show this item and its attachment or location clearly.")
        hazard.setdefault("tracking_supported", False)
        fix = hazard.get("fix")
        if fix:
            fix.setdefault("source_status", "legacy_unknown")
            fix.setdefault("action_sources", [])
    return report


def counts(hazards: list[dict]) -> dict:
    return {**{s: sum(h.get("severity") == s for h in hazards) for s in ("high", "medium", "low")},
            "needs_check": sum(h.get("evidence_status") != "observed" for h in hazards)}


def sourced_fix(hazard: dict) -> bool:
    fix = hazard.get("fix") or {}
    actions = fix.get("actions") or []
    refs = fix.get("action_sources") or []
    sections = {s["id"] for s in fix.get("fema_sections", []) if "id" in s}
    return (fix.get("source_status") == "verified" and bool(actions) and len(refs) == len(actions)
            and all(ids and all(i in sections for i in ids) for ids in refs))
