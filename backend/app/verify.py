"""Verify-after-fix pipeline: re-filmed video -> SAM re-finds each hazard's object -> verifier agent per hazard ->
`verification.json` next to the original report, with before/after evidence pairs and the risk score after fixes."""
from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from pathlib import Path

from app import config, media
from app.agents import verifier
from app.hazards import risk_score
from app.meta.clients import meta_client, upload_video
from app.meta.sam import Track, result_cost, track_concept
from app.report import marks as som
from app.report.provenance import now_iso, sha256_file, sha256_text

Emit = Callable[[str, dict], None]
AFTER_FRAMES = 3


def best_frames(tracks: list[Track], k: int = AFTER_FRAMES) -> list[tuple[int, Track]]:
    """Frames where the object is biggest (closest / most visible), spread out so they are not near-duplicates."""
    scored = sorted(((b[2] - b[0]) * (b[3] - b[1]), f, t) for t in tracks for f, b in t.boxes.items())
    picked: list[tuple[int, Track]] = []
    for _, frame, track in reversed(scored):
        if all(abs(frame - f) >= 5 for f, _ in picked):
            picked.append((frame, track))
        if len(picked) == k:
            break
    return sorted(picked, key=lambda p: p[0])


def apply_guard(verdict: dict, object_found: bool) -> dict:
    """Deterministic evidence rule on top of the model: "fixed" needs the object re-found by SAM in the new video
    AND confirmed as the same physical object. Otherwise "removed", "out of frame" and "SAM boxed a different lamp"
    look alike, so the claim is downgraded and the guard is recorded for the audit trail."""
    if verdict["verdict"] != "fixed":
        return {**verdict, "guard": None}
    if not object_found:
        reason = "object not re-found by SAM 3.1; removal cannot be told apart from out-of-frame"
        hint = "If you removed or moved it, film the empty spot where it stood."
    elif verdict.get("boxed_is_same_object") != "yes":
        reason = "SAM 3.1 re-found a different object, so the fix is not tied to this hazard"
        hint = "Film this object up close, including where it is attached."
    else:
        return {**verdict, "guard": None}
    return {**verdict, "verdict": "cannot_verify", "confidence": "low", "guard": reason,
            "what_changed": f"{hint} (Model's reading: {verdict['what_changed']})"}


async def run_verify(scan_root: Path, src: Path, verify_id: str, emit: Emit) -> dict:
    started = time.perf_counter()
    report = json.loads((scan_root / "report.json").read_text())
    root = scan_root / "verify" / verify_id
    api = meta_client()
    emit("ingest", {"verify_id": verify_id})
    proxy = await asyncio.to_thread(media.make_proxy, src, root / "proxy.mp4")   # off the event loop
    frames = await asyncio.to_thread(media.extract_frames, proxy, root / "frames")
    file_id = await upload_video(api, proxy)
    emit("ingest.done", {"frames": len(frames)})

    hazards = [h for h in report["hazards"]]
    concepts = sorted({h["track"].split("#")[0] for h in hazards if h.get("track")})
    sem = asyncio.Semaphore(config.SAM_CONCURRENCY)

    alternates = {}
    for item in report["plan"]["concepts"]:
        for name in [item["concept"], *item.get("alternates", [])]:
            alternates[name] = [w for w in [item["concept"], *item.get("alternates", [])] if w != name]

    sam_cost_usd: list[float] = []

    async def track(concept: str):
        """Same wording as the scan first, then the planner's alternates while SAM finds nothing."""
        for wording in [concept, *alternates.get(concept, [])]:
            async with sem:
                emit("sam.start", {"concept": wording})
                result = await track_concept(api, file_id, wording)
            sam_cost_usd.append(result_cost(result, len(frames)))
            emit("sam.done", {"concept": wording, "objects": len(result.tracks)})
            if result.tracks:
                break
        return concept, result

    found = dict(await asyncio.gather(*(track(c) for c in concepts)))
    overview = []                           # copied under after/ because raw frames are never served
    for f in media.pick_keyframes(len(frames), 4):
        out = root / "after" / f"overview_{f:05d}.jpg"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(frames[f].read_bytes())
        overview.append((f, out))

    async def check(h: dict):
        result = found.get(h["track"].split("#")[0]) if h.get("track") else None
        tracks = result.tracks if result else []
        if tracks:
            after = []
            for frame, t in best_frames(tracks):
                out = root / "after" / f"{h['id']}_{frame:05d}.jpg"
                await asyncio.to_thread(som.draw_marks, frames[frame], frame, {"1": t}, out, only={"1"})
                after.append((frame, out))
        else:
            after = overview
        verdict, meta = await verifier.verify_hazard(api, h, scan_root / h["evidence_image"], after, bool(tracks))
        verdict = apply_guard(verdict, object_found=bool(tracks))
        best = int(verdict["best_after_frame"])
        after_image = next((p for f, p in after if f == best), after[0][1])
        emit("verify.hazard", {"hazard_id": h["id"], "object": h["object"], "verdict": verdict["verdict"]})
        return h["id"], {**verdict, "object_found": bool(tracks),
                         "after_image": str(after_image.relative_to(scan_root))}, meta

    checked = await asyncio.gather(*(check(h) for h in hazards))
    results = {hid: r for hid, r, _ in checked}
    remaining = [h for h in hazards if results[h["id"]]["verdict"] != "fixed"]
    cost = sum(sam_cost_usd) + sum(m["cost_usd"] for _, _, m in checked)
    verification = {
        "verify_id": verify_id, "created_at": now_iso(),
        "results": results,
        "fixed": sum(r["verdict"] == "fixed" for r in results.values()),
        "risk_score_before": report["room"]["risk_score"], "risk_score_after": risk_score(remaining),
        "cost_usd": round(cost, 4), "seconds": round(time.perf_counter() - started, 1),
        "provenance": {"source_sha256": sha256_file(src), "model": checked[0][2]["model"] if checked else None,
                       "prompt_sha256": sha256_text(verifier.INSTRUCTIONS),
                       "reasoning_summaries": {hid: m["reasoning_summary"] for hid, _, m in checked}},
    }
    (scan_root / "verification.json").write_text(json.dumps(verification, indent=2, ensure_ascii=False) + "\n")
    emit("done", {"fixed": verification["fixed"], "of": len(hazards),
                  "risk_score_after": verification["risk_score_after"], "cost_usd": verification["cost_usd"]})
    return verification
