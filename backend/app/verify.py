"""Immutable, optionally targeted verification attempts with candidate-separated evidence."""
from __future__ import annotations
import time
import json
from pathlib import Path

from app import config, media, guard
from app.runtime import blocking, together
from app.storage import write_json
from app.agents import verifier
from app.meta.clients import meta_client
from app.meta.files import uploaded_video
from app.meta.sam import Track, result_cost, track_concept
from app.report import marks as som
from app.report.contracts import adapt_report, sourced_fix
from app.report.provenance import now_iso, sha256_file, sha256_text

AFTER_FRAMES = 3
MAX_CANDIDATES = 4


def best_frames(tracks: list[Track], k: int = AFTER_FRAMES) -> list[tuple[int, Track]]:
    scored = sorted((((b[2]-b[0])*(b[3]-b[1]), f, t) for t in tracks for f, b in t.boxes.items()),
                    key=lambda item: (item[0], item[1], item[2].key))
    picked = []
    for _, frame, track in reversed(scored):
        if all(abs(frame-f) >= 5 for f, _ in picked):
            picked.append((frame, track))
        if len(picked) == k:
            break
    return sorted(picked, key=lambda p: p[0])


def apply_guard(verdict: dict, object_found: bool) -> dict:
    reason = None
    if verdict.get('original_finding_reconsidered') == 'yes':
        reason = 'The original finding needs manual review; reinterpretation is not a new fix.'
    elif verdict['verdict'] == 'fixed':
        if not object_found:
            reason = 'Object not re-found. Removal and out-of-frame objects require manual review.'
        elif verdict.get('boxed_is_same_object') != 'yes':
            reason = 'The candidate is not confirmed as the same physical object.'
        elif verdict.get('before_condition_visible') != 'yes' or verdict.get('change_kind') != 'physical_change':
            reason = 'The original condition or a new physical change is not visible; a new angle is not a fix.'
        elif verdict.get('confidence') != 'high' or verdict.get('visible_change') != 'yes':
            reason = 'Insufficient evidence of a relevant visible change.'
    if reason:
        return {**verdict, 'verdict': 'cannot_verify', 'confidence': 'low', 'guard': reason,
                'what_changed': reason,
                'next_view_request': verdict.get('next_view_request') or
                    'Show this item and its attachment or new location, including the surrounding room.'}
    return {**verdict, 'guard': None}


def unresolved(reason: str, view: dict) -> dict:
    return {'verdict': 'cannot_verify', 'confidence': 'low', 'boxed_is_same_object': 'no_box',
        'visible_change': 'unclear', 'candidate_id': 'none', 'best_after_view': view['id'],
        'before_condition_visible': 'unclear', 'change_kind': 'unclear',
        'original_finding_reconsidered': 'no', 'what_changed': reason, 'rationale': reason,
        'next_view_request': 'Show the original object, its surroundings and the relevant attachment or new location.',
        'guard': reason}


async def run_verify(scan_root: Path, src: Path, verify_id: str, emit, hazard_id: str | None = None) -> dict:
    if 'contributor' in config.SPARK_MODEL:
        raise ValueError('Private verification requires a standard model.')
    with guard.accounting(scan_root / 'verify' / verify_id):
        async with meta_client() as api:
            return await _run(api, scan_root, src, verify_id, emit, hazard_id)


async def _run(api, scan_root, src, verify_id, emit, hazard_id):
    started = time.perf_counter()
    report = adapt_report(json.loads((scan_root / 'report.json').read_text()))
    hazards = [h for h in report['hazards'] if hazard_id is None or h['id'] == hazard_id]
    if not hazards:
        raise ValueError('No findings selected for verification.')
    root = scan_root / 'verify' / verify_id
    root.mkdir(parents=True, exist_ok=True)
    emit('ingest', {'verify_id': verify_id})
    await blocking(media.validate, src)
    proxy = await blocking(media.make_proxy, src, root / 'proxy.mp4')
    frames = await blocking(media.extract_frames, proxy, root / 'frames')
    if not frames:
        raise ValueError('No decodable video frames.')
    processed = await blocking(media.probe, proxy)
    emit('ingest.done', {'frames': len(frames), 'duration_s': processed['duration_s']})
    identical = sha256_file(src) == report.get('provenance', {}).get('source_sha256')
    concepts = [] if identical else sorted({h['track'].split('#')[0] for h in hazards if h.get('track')})
    alternates = {}
    for item in report.get('plan', {}).get('concepts', []):
        names = [item['concept'], *item.get('alternates', [])]
        for name in names:
            alternates[name] = [w for w in names if w != name]
    sam_costs, found = [], {}
    if concepts:
        async with uploaded_video(api, proxy, root) as file_id:
            async def track(concept):
                for wording in [concept, *alternates.get(concept, [])]:
                    emit('sam.start', {'concept': wording})
                    result = await track_concept(api, file_id, wording, n_frames=len(frames))
                    sam_costs.append(result_cost(result, len(frames)))
                    emit('sam.done', {'concept': wording, 'objects': len(result.tracks), 'status': result.status})
                    if result.status == 'completed' and result.tracks:
                        break
                return concept, result
            found = dict(await together(*(track(c) for c in concepts)))
    overview = []
    for f in media.pick_keyframes(len(frames), 3):
        out = root / 'after' / f'overview_{f:05d}.jpg'
        await blocking(som.draw_marks, frames[f], f, {}, out)
        overview.append({'id': f'overview_{f}', 'candidate_id': 'none', 'frame': f, 'path': out})

    async def check(h):
        result = found.get(h['track'].split('#')[0]) if h.get('track') else None
        tracks = result.tracks if result and result.status == 'completed' else []
        views = list(overview[:1])
        too_many = len(tracks) > MAX_CANDIDATES
        for ci, candidate in enumerate(tracks[:MAX_CANDIDATES]):
            for frame, t in best_frames([candidate], 2):
                out = root / 'after' / f"{h['id']}_c{ci}_{frame:05d}.jpg"
                await blocking(som.draw_marks, frames[frame], frame, {'1': t}, out)
                views.append({'id': f'c{ci}f{frame}', 'candidate_id': t.key, 'frame': frame, 'path': out})
        meta = {'cost_usd': 0, 'model': None, 'reasoning_summary': []}
        if identical:
            raw = unresolved('This is the original video. It cannot demonstrate a new physical change.', views[0])
        elif not h.get('track'):
            raw = unresolved('This original finding was not tracked; it requires manual review.', views[0])
        elif not tracks:
            raw = unresolved('Object not re-found or tracking unavailable; removal cannot be confirmed.', views[0])
        elif too_many:
            raw = unresolved('Too many similar candidates. Film only the target and its immediate surroundings.', views[0])
        elif not sourced_fix(h):
            raw = unresolved('No source-linked recommendation is available for automatic change confirmation.', views[0])
        else:
            raw, meta = await verifier.verify_hazard(api, h, scan_root / h['evidence_image'], views)
        verdict = apply_guard(raw, bool(tracks))
        selected = next((v for v in views if v['id'] == verdict.get('best_after_view')), views[0])
        if verdict['verdict'] == 'fixed' and (verdict.get('candidate_id') == 'none' or
                selected['candidate_id'] != verdict.get('candidate_id')):
            verdict = unresolved('Selected evidence does not belong to the identified object.', selected)
        emit('verify.hazard', {'hazard_id': h['id'], 'object': h['object'], 'verdict': verdict['verdict']})
        return h['id'], {**verdict, 'model_verdict': raw['verdict'] if meta.get('model') else None,
            'model_called': bool(meta.get('model')), 'object_found': bool(tracks),
            'after_image': str(selected['path'].relative_to(scan_root)),
            'candidates': [{'id': v['id'], 'candidate_id': v['candidate_id'], 'frame': v['frame'],
                            'image': str(v['path'].relative_to(scan_root))} for v in views]}, meta
    checked = await together(*(check(h) for h in hazards))
    results = {hid: verdict for hid, verdict, _ in checked}
    cost = sum(sam_costs) + sum(m['cost_usd'] for _, _, m in checked)
    verification = {'schema_version': 2, 'verify_id': verify_id, 'created_at': now_iso(),
        'hazard_id': hazard_id, 'checked_hazard_ids': list(results),
        'unchecked_hazard_ids': [h['id'] for h in report['hazards'] if h['id'] not in results],
        'results': results, 'fixed': sum(v['verdict'] == 'fixed' for v in results.values()),
        'counts': {s: sum(v['verdict'] == s for v in results.values()) for s in ['fixed','not_fixed','cannot_verify']},
        'cost_usd': round(cost, 4), 'seconds': round(time.perf_counter()-started, 1),
        'provenance': {'source_sha256': sha256_file(src), 'app_version': config.APP_VERSION,
            'prompt_sha256': sha256_text(verifier.INSTRUCTIONS), 'model': config.SPARK_MODEL,
            'schema_sha256': sha256_text(json.dumps(verifier.schema(['VIEW_ID'], ['CANDIDATE_ID']), sort_keys=True)),
            'media': {'fps': config.PROXY_FPS, 'max_seconds': config.MAX_VIDEO_SECONDS, **processed},
            'original_source_sha256': report.get('provenance', {}).get('source_sha256'),
            'settings': {'effort': 'medium', 'max_candidates': MAX_CANDIDATES, 'frames_per_candidate': 2},
            'reasoning_summaries': {hid: m['reasoning_summary'] for hid, _, m in checked}}}
    recorded = guard.recorded_costs()
    if recorded:
        verification['cost_usd'] = recorded['total']
        verification['provenance']['billing'] = recorded
    write_json(root / 'verification.json', verification)
    write_json(scan_root / 'verification.json', verification)
    emit('done', {'fixed': verification['fixed'], 'of': len(hazards), 'cost_usd': verification['cost_usd']})
    return verification
