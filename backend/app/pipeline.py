"""Evidence-preserving room screening. Job completion and assessment completeness are separate."""
from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from app import config, media, guard
from app.runtime import blocking, together
from app.storage import write_json
from app.agents import fixer, planner, surveyor
from app.hazards import DISCLAIMER, risk_score
from app.meta.clients import meta_client
from app.meta.files import uploaded_video
from app.meta.sam import result_cost, track_concept
from app.report import marks as som
from app.report.contracts import counts
from app.report.provenance import now_iso, sha256_file, sha256_text

Emit = Callable[[str, dict], None]


def _print_emit(step: str, data: dict) -> None:
    print(f'[{step}]')  # no room descriptions, narration, paths or model text in server logs


def hash_json(value) -> str:
    return sha256_text(json.dumps(value, sort_keys=True, ensure_ascii=False))


def assessment_for(groups, survey: dict, fixes_ok: bool, sources_ok: bool) -> dict:
    statuses = []
    for group in groups:
        completed = [r for r in group if r.status == 'completed']
        statuses.append('ok' if any(r.tracks for r in completed) else
                        'not_found' if completed and all(r.status == 'completed' for r in group) else 'error')
    warnings = []
    all_failed = bool(statuses) and all(s == 'error' for s in statuses)
    partial = any(s == 'error' for s in statuses)
    inadequate = survey.get('view_adequacy') != 'adequate'
    if all_failed:
        warnings.append('Object tracking failed. This is an incomplete assessment, not an absence of hazards.')
    elif partial:
        warnings.append('Some tracking targets could not be assessed due to a technical error.')
    if inadequate:
        warnings.append(survey.get('view_guidance') or 'Sampled views are insufficient. Please film the room again.')
    if not fixes_ok:
        warnings.append('Findings are available, but recommendations could not be prepared.')
    elif not sources_ok:
        warnings.append('Some recommendations lack a confirmed source and have been withheld.')
    return {'status': 'incomplete' if all_failed or inadequate else
            'partial' if partial or not fixes_ok or not sources_ok else 'complete',
            'stages': {'tracking': statuses, 'surveyor': survey.get('view_adequacy', 'insufficient'),
                       'fixer': 'ok' if fixes_ok else 'error'}, 'warnings': warnings}


async def run_scan(src: Path, narration: str | None = None, emit: Emit = _print_emit,
                   scan_id: str | None = None, *, tracking: bool = True) -> dict:
    if 'contributor' in config.SPARK_MODEL:
        raise ValueError('Public/private room screening requires a standard model, not a contributor model.')
    scan_id = scan_id or uuid.uuid4().hex[:12]
    with guard.accounting(config.SCANS_DIR / scan_id):
        async with meta_client() as api:
            return await _run(api, src, narration, emit, scan_id, tracking)


async def _run(api, src: Path, narration: str | None, emit: Emit, scan_id: str, tracking: bool) -> dict:
    started = time.perf_counter()
    root = config.SCANS_DIR / scan_id
    root.mkdir(parents=True, exist_ok=True)
    costs, timings = {}, {}
    mark_t = started

    def lap(name):
        nonlocal mark_t
        now = time.perf_counter()
        timings[name], mark_t = round(now - mark_t, 1), now

    emit('ingest', {'scan_id': scan_id})
    original = await blocking(media.validate, src)
    proxy = await blocking(media.make_proxy, src, root / 'proxy.mp4')
    frames = await blocking(media.extract_frames, proxy, root / 'frames')
    if not frames:
        raise ValueError('No decodable video frames.')
    info = await blocking(media.probe, proxy)
    keyframes = media.pick_keyframes(len(frames), config.KEYFRAMES)
    lap('ingest')
    emit('ingest.done', {'frames': len(frames), 'duration_s': round(info['duration_s'], 1),
                        'keyframes': keyframes, 'trimmed': original['duration_s'] > info['duration_s'] + .5})
    plan, plan_meta = await planner.plan(api, [frames[i] for i in keyframes], narration)
    costs['planner'] = plan_meta['cost_usd']
    lap('planner')
    emit('planner.done', {'room_type': plan['room_type'], 'concepts': [c['concept'] for c in plan['concepts']],
                          'reasoning_summary': plan_meta['reasoning_summary']})
    groups = []
    if tracking and plan['concepts']:
        async with uploaded_video(api, proxy, root) as file_id:
            async def track(item):
                attempts = []
                for concept in [item['concept'], *item['alternates']]:
                    emit('sam.start', {'concept': concept})
                    result = await track_concept(api, file_id, concept, n_frames=len(frames))
                    attempts.append(result)
                    emit('sam.done', {'concept': concept, 'objects': len(result.tracks),
                                      'seconds': result.seconds, 'status': result.status})
                    if result.status == 'completed' and result.tracks:
                        break
                return attempts
            groups = await together(*(track(c) for c in plan['concepts']))
    results = [r for group in groups for r in group]
    costs['sam'] = sum(result_cost(r, len(frames)) for r in results)
    tracks = [t for r in results if r.status == 'completed' for t in r.tracks]
    lap('sam')
    marks = som.assign_marks(tracks)
    marked = []
    for frame in keyframes:
        out = root / 'marked' / f'{frame:05d}.jpg'
        await blocking(som.draw_marks, frames[frame], frame, marks, out)
        marked.append((frame, out))
    emit('marks.done', {'objects': {m: t.concept for m, t in marks.items()},
                        'images': [str(p.relative_to(root)) for _, p in marked]})
    survey, survey_meta = await surveyor.survey(api, marked, list(marks), plan, narration)
    costs['surveyor'] = survey_meta['cost_usd']
    lap('surveyor')
    hazards, seen = [], set()
    for h in survey['hazards']:
        frame = int(h['evidence_frame'])
        if frame not in keyframes:
            raise ValueError('Evidence frame was not evaluated by the surveyor.')
        track = marks.get(h['mark'])
        key = (track.key, h['relation']) if track else None
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        hid = f'h{len(hazards) + 1}'
        box = track.boxes.get(frame) if track else None
        evidence = root / 'evidence' / f'{hid}.jpg'
        await blocking(som.draw_marks, frames[frame], frame, {h['mark']: track} if box else {}, evidence)
        hazards.append({'id': hid, **h, 'track': track.key if track else None, 'box': box,
            'tracking_supported': box is not None,
            'tracking_note': '' if box else 'No tracking box at this exact evidence frame.',
            'track_frames': [track.frames[0], track.frames[-1]] if track else None,
            'evidence_image': str(evidence.relative_to(root))})
    room = {'type': plan['room_type'], 'sleeping_area': plan['sleeping_area'], 'exit_visible': plan['exit_visible'],
            'summary': survey['room_summary'], 'risk_score': risk_score(hazards)}
    emit('surveyor.done', {'hazards': len(hazards), 'reasoning_summary': survey_meta['reasoning_summary']})
    provisional = {'schema_version': 2, 'scan_id': scan_id, 'room': room, 'hazards': hazards,
                   'assessment': {'status': 'partial', 'warnings': ['Recommendations are still being prepared.']}}
    write_json(root / 'partial.json', provisional)
    emit('findings.ready', {'findings': provisional})
    fixes_ok = True
    try:
        fixes, fix_meta = await fixer.plan_fixes(api, hazards, room)
    except Exception:
        fixes_ok = False
        fixes, fix_meta = {}, {'cost_usd': 0, 'reasoning_summary': [], 'tool_calls': [], 'usage': {}}
        emit('fixer.error', {'message': 'Recommendations could not be prepared.'})
    costs['fixer'] = fix_meta['cost_usd']
    for h in hazards:
        h['fix'] = fixes.get(h['id'])
    sources_ok = all((h.get('fix') or {}).get('source_status') == 'verified' for h in hazards)
    assessment = assessment_for(groups, survey, fixes_ok, sources_ok)
    if not tracking:
        assessment['stages']['tracking'] = ['skipped_baseline']
    lap('fixer')
    emit('fixer.done', {'fixes': len(fixes), 'fema_lookups': [c.get('returned_section_ids', [])
                        for c in fix_meta['tool_calls']], 'reasoning_summary': fix_meta['reasoning_summary']})
    report = {'schema_version': config.SCHEMA_VERSION, 'scan_id': scan_id, 'created_at': now_iso(),
        'assessment': assessment, 'counts': counts(hazards), 'context': {
            'occupant_narration': narration or '', 'source': 'occupant_statement_not_visual_evidence'},
        'room': room, 'hazards': hazards, 'plan': plan,
        'objects': {m: {'concept': t.concept, 'track': t.key, 'frames': [t.frames[0], t.frames[-1]]}
                    for m, t in marks.items()}, 'disclaimer': DISCLAIMER,
        'cost_usd': {k: round(v, 4) for k, v in costs.items()} | {'total': round(sum(costs.values()), 4)},
        'seconds': round(time.perf_counter() - started, 1), 'timings_s': timings,
        'provenance': {'source_sha256': sha256_file(src), 'app_version': config.APP_VERSION,
            'keyframes': keyframes, 'proxy': {'fps': config.PROXY_FPS, **info},
            'original_duration_s': original['duration_s'], 'tracking_enabled': tracking,
            'settings': {'keyframes': config.KEYFRAMES, 'max_concepts': config.MAX_CONCEPTS,
                         'max_video_seconds': config.MAX_VIDEO_SECONDS, 'proxy_height': config.PROXY_HEIGHT,
                         'planner_effort': 'low', 'surveyor_effort': 'medium', 'fixer_effort': 'low'},
            'models': {'planner': plan_meta['model'], 'surveyor': survey_meta['model'],
                       'fixer': fix_meta.get('model'), 'tracking': config.SAM_MODEL if tracking else None},
            'prompts_sha256': {'planner': sha256_text(planner.INSTRUCTIONS),
                'surveyor': sha256_text(surveyor.INSTRUCTIONS), 'fixer': sha256_text(fixer.instructions())},
            'schemas_sha256': {'planner': hash_json(planner.SCHEMA),
                'surveyor': hash_json(surveyor.schema(list(marks), keyframes)),
                'fixer': hash_json(fixer.schema([h['id'] for h in hazards]))},
            'grounding': {'source': fixer.fema()['source'], 'tool_calls': fix_meta['tool_calls']},
            'sam': [{'concept': r.concept, 'status': r.status, 'objects': len(r.tracks),
                     'seconds': r.seconds, 'error': 'Tracking service error' if r.error else None} for r in results],
            'reasoning_summaries': {'planner': plan_meta['reasoning_summary'],
                'surveyor': survey_meta['reasoning_summary'], 'fixer': fix_meta['reasoning_summary']},
            'usage': {'planner': plan_meta['usage'], 'surveyor': survey_meta['usage'], 'fixer': fix_meta['usage']}}}
    recorded = guard.recorded_costs()
    if recorded:
        report['cost_usd']['total'] = recorded['total']
        report['provenance']['billing'] = recorded
    write_json(root / 'report.json', report)
    (root / 'partial.json').unlink(missing_ok=True)
    emit('done', {'scan_id': scan_id, 'hazards': len(hazards), 'assessment': assessment['status'],
                  'cost_usd': report['cost_usd']['total'], 'seconds': report['seconds']})
    return report
