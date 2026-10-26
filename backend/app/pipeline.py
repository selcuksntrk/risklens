"""Scan pipeline: video -> planner (Spark) -> tracking (SAM 3.1) -> set-of-marks -> surveyor (Spark) -> report.

Every step calls `emit(step, data)`; the web app streams these as the live agent timeline.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from app import config, media
from app.agents import planner, surveyor
from app.hazards import DISCLAIMER, risk_score
from app.meta.clients import meta_client, upload_video
from app.meta.sam import sam_cost, track_concept
from app.report import marks as som
from app.report.provenance import now_iso, sha256_file, sha256_text

Emit = Callable[[str, dict], None]


def _print_emit(step: str, data: dict) -> None:
    print(f"[{step}] " + json.dumps(data, ensure_ascii=False)[:300])


async def run_scan(src: Path, narration: str | None = None, emit: Emit = _print_emit,
                   scan_id: str | None = None) -> dict:
    started = time.perf_counter()
    scan_id = scan_id or uuid.uuid4().hex[:12]
    root = config.SCANS_DIR / scan_id
    api = meta_client()
    costs: dict[str, float] = {}
    timings: dict[str, float] = {}
    mark_t = time.perf_counter()

    def lap(name: str) -> None:
        nonlocal mark_t
        now = time.perf_counter()
        timings[name] = round(now - mark_t, 1)
        mark_t = now

    emit("ingest", {"scan_id": scan_id, "source": src.name})
    proxy = media.make_proxy(src, root / "proxy.mp4")
    frames = media.extract_frames(proxy, root / "frames")
    info = media.probe(proxy)
    keyframes = media.pick_keyframes(len(frames), config.KEYFRAMES)
    lap("ingest")
    emit("ingest.done", {"frames": len(frames), "duration_s": round(info["duration_s"], 1), "keyframes": keyframes})

    # Upload while the planner looks at the room.
    file_task = asyncio.create_task(upload_video(api, proxy))
    plan, plan_meta = await planner.plan(api, [frames[i] for i in keyframes], narration)
    costs["planner"] = plan_meta["cost_usd"]
    lap("planner")
    emit("planner.done", {"room_type": plan["room_type"], "concepts": [c["concept"] for c in plan["concepts"]],
                          "reasoning_summary": plan_meta["reasoning_summary"]})
    file_id = await file_task
    lap("upload_wait")

    sem = asyncio.Semaphore(config.SAM_CONCURRENCY)

    async def track(item: dict):
        """Try the planner's wording first, then its alternates while SAM finds nothing."""
        attempts = []
        for concept in [item["concept"], *item["alternates"]]:
            async with sem:
                emit("sam.start", {"concept": concept})
                result = await track_concept(api, file_id, concept)
            emit("sam.done", {"concept": concept, "objects": len(result.tracks), "seconds": result.seconds,
                              "status": result.status})
            attempts.append(result)
            if result.tracks:
                break
        return attempts

    sam_results = [r for attempts in await asyncio.gather(*(track(c) for c in plan["concepts"])) for r in attempts]
    costs["sam"] = sum(sam_cost(len(frames)) for _ in sam_results)
    tracks = [t for r in sam_results for t in r.tracks]
    lap("sam")
    marks = som.assign_marks(tracks)

    marked = []
    for frame in keyframes:
        out = root / "marked" / f"{frame:05d}.jpg"
        som.draw_marks(frames[frame], frame, marks, out)
        marked.append((frame, out))
    emit("marks.done", {"objects": {m: t.concept for m, t in marks.items()},
                        "images": [str(p.relative_to(root)) for _, p in marked]})

    survey, survey_meta = await surveyor.survey(api, marked, list(marks), plan, narration)
    costs["surveyor"] = survey_meta["cost_usd"]
    lap("surveyor")

    hazards = []
    for i, h in enumerate(survey["hazards"]):
        frame = int(h["evidence_frame"])
        track = marks.get(h["mark"])
        if track and som.box_near(track, frame) is None:     # surveyor cited a frame where SAM never saw it
            frame = min(track.frames, key=lambda f: abs(f - frame))
            h = {**h, "evidence_frame": str(frame)}
        evidence = root / "evidence" / f"h{i + 1}.jpg"
        if track:
            som.draw_marks(frames[frame], frame, {h["mark"]: track}, evidence, only={h["mark"]})
        else:
            evidence.parent.mkdir(parents=True, exist_ok=True)
            evidence.write_bytes(frames[frame].read_bytes())
        hazards.append({
            "id": f"h{i + 1}", **h,
            "track": track.key if track else None,
            "box": som.box_near(track, frame) if track else None,
            "track_frames": [track.frames[0], track.frames[-1]] if track else None,
            "evidence_image": str(evidence.relative_to(root)),
        })
    emit("surveyor.done", {"hazards": len(hazards), "reasoning_summary": survey_meta["reasoning_summary"]})

    report = {
        "scan_id": scan_id,
        "created_at": now_iso(),
        "room": {"type": plan["room_type"], "sleeping_area": plan["sleeping_area"],
                 "exit_visible": plan["exit_visible"], "summary": survey["room_summary"],
                 "risk_score": risk_score(hazards)},
        "hazards": hazards,
        "plan": plan,
        "objects": {m: {"concept": t.concept, "track": t.key, "frames": [t.frames[0], t.frames[-1]]}
                    for m, t in marks.items()},
        "disclaimer": DISCLAIMER,
        "cost_usd": {k: round(v, 4) for k, v in costs.items()} | {"total": round(sum(costs.values()), 4)},
        "seconds": round(time.perf_counter() - started, 1),
        "timings_s": timings,
        "provenance": {
            "source_sha256": sha256_file(src),
            "proxy": {"fps": config.PROXY_FPS, **info},
            "models": {"planner": plan_meta["model"], "surveyor": survey_meta["model"], "tracking": config.SAM_MODEL},
            "prompts_sha256": {"planner": sha256_text(planner.INSTRUCTIONS),
                               "surveyor": sha256_text(surveyor.INSTRUCTIONS)},
            "sam": [{"concept": r.concept, "status": r.status, "objects": len(r.tracks), "seconds": r.seconds,
                     "error": r.error} for r in sam_results],
            "reasoning_summaries": {"planner": plan_meta["reasoning_summary"],
                                    "surveyor": survey_meta["reasoning_summary"]},
            "usage": {"planner": plan_meta["usage"], "surveyor": survey_meta["usage"]},
        },
    }
    (root / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    emit("done", {"scan_id": scan_id, "hazards": len(hazards), "risk_score": report["room"]["risk_score"],
                  "cost_usd": report["cost_usd"]["total"], "seconds": report["seconds"]})
    return report
