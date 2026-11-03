"""Design synthetic sample rooms with Muse Image, gated by a Muse Spark consistency check.

Each scene bible (scripts/scenes/*.json) fixes the room, every object's exact description and the designed
hazards (answer key). Shot 0 is generated from text; later shots are generated against shot 0 as a visual anchor,
then Muse Spark compares candidate and anchor and lists which designed hazards are clearly visible. A shot is
accepted at consistency >= 7 with every expected hazard visible and no people or readable text; otherwise it is
regenerated (max 3 attempts, best kept). Output: examples/build/<scene>/shots/NN.png + qa.json (gitignored).

Run: uv run --with httpx --with pillow --env-file ../.env python scripts/generate_scenes.py [scene ...]
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCENES = ROOT / 'scripts' / 'scenes'
BUILD = ROOT / 'examples' / 'build'
BASE = 'https://api.meta.ai/v1'
IMAGE_MODEL, QA_MODEL = 'muse-image-1.0', 'muse-spark-1.3'
MAX_ATTEMPTS, PASS_SCORE = 3, 7
IMAGE_TOOL = {'type': 'image_generation', 'size': '1536x1024', 'reasoning_strength': 'high',
              'enable_image_search': False, 'enable_web_search': False, 'enable_shell': False, 'output_format': 'png'}

STYLE = ('Photograph taken on a smartphone main camera (26 mm equivalent lens, held at eye level about 150 cm, '
         'auto-HDR, mild sensor noise, slightly imperfect handheld framing) inside a real, lived-in apartment in '
         'Istanbul, Turkey. Natural late-afternoon daylight from the window, warm ceiling light on. Everyday clutter '
         'consistent with a family home. Photorealistic, true-to-scale furniture, correct perspective and lens '
         'geometry. No people, no pets, no readable text or numbers, no logos or brand names, no religious or '
         'political objects, no captions or watermarks.')

QA_SCHEMA = {'type': 'object', 'additionalProperties': False,
             'required': ['consistency_score', 'designed_visible', 'inconsistencies', 'artifacts', 'people_or_text'],
             'properties': {'consistency_score': {'type': 'integer'},
                            'designed_visible': {'type': 'array', 'items': {'type': 'string'}},
                            'inconsistencies': {'type': 'array', 'items': {'type': 'string'}},
                            'artifacts': {'type': 'array', 'items': {'type': 'string'}},
                            'people_or_text': {'type': 'boolean'}}}


def key() -> str:
    k = os.environ.get('MODEL_API_KEY')
    if not k:
        sys.exit('MODEL_API_KEY missing (pass --env-file).')
    return k


def http() -> httpx.Client:
    return httpx.Client(base_url=BASE, headers={'Authorization': f'Bearer {key()}'}, timeout=300)


def data_url(path: Path, max_side: int = 1024) -> str:
    image = Image.open(path).convert('RGB')
    image.thumbnail((max_side, max_side))
    buf = io.BytesIO(); image.save(buf, 'JPEG', quality=88)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


def describe(bible: dict, ids: list[str]) -> str:
    objects = bible['objects']
    return '; '.join(objects.get(i, i) for i in ids)


def shot_prompt(bible: dict, shot: dict) -> str:
    if shot['id'] == 0:
        return (f"{STYLE}\n\nRoom: {bible['description']}\n\nCamera: {shot['camera']}. Clearly visible in this "
                f"view: {describe(bible, shot['visible'])}.")
    return (f"{STYLE}\n\nThe reference image is the establishing shot of this exact room. Same room, identical "
            f"furniture, materials, colours, wall finish, floor and positions; nothing added, removed or restyled. "
            f"Room: {bible['description']}\n\nNew camera: {shot['camera']}. Clearly visible in this view: "
            f"{describe(bible, shot['visible'])}. Keep every object's exact description from the reference.")


def generate(client: httpx.Client, bible: dict, shot: dict, anchor: Path | None) -> tuple[bytes, dict]:
    prompt = shot_prompt(bible, shot)
    if anchor is None:
        body = {'model': IMAGE_MODEL, 'input': prompt, 'tools': [IMAGE_TOOL], 'store': False}
    else:
        body = {'model': IMAGE_MODEL, 'tools': [IMAGE_TOOL], 'store': False, 'input': [{'role': 'user', 'content': [
            {'type': 'input_text', 'text': 'Reference (establishing shot of the same room):'},
            {'type': 'input_image', 'image_url': data_url(anchor)},
            {'type': 'input_text', 'text': prompt}]}]}
    for attempt in range(4):
        r = client.post('/responses', json=body)
        if r.status_code in (429, 500, 502, 503) and attempt < 3:
            time.sleep(5 * (attempt + 1)); continue
        if r.status_code >= 400:
            raise RuntimeError(f'image {r.status_code}: {r.text[:300]}')
        break
    out = r.json()
    image = next(o['result'] for o in out['output'] if o['type'] == 'image_generation_call' and o.get('result'))
    summary = [s.get('text', '') for o in out['output'] if o['type'] == 'reasoning' for s in (o.get('summary') or [])]
    return base64.b64decode(image), {'prompt': prompt, 'reasoning_summary': summary}


def qa(client: httpx.Client, bible: dict, shot: dict, candidate: Path, anchor: Path | None) -> dict:
    expected = {h['id']: f"{h['label']} ({bible['objects'][h['object']]})" for h in bible['answer_key']
                if h['id'] in shot['expected']}
    images = [{'type': 'input_text', 'text': 'Image 1 (establishing shot):'}, {'type': 'input_image', 'image_url': data_url(anchor)}] if anchor else []
    images += [{'type': 'input_text', 'text': f"Image {2 if anchor else 1} (candidate):"}, {'type': 'input_image', 'image_url': data_url(candidate)}]
    instruction = (
        f"<scene_bible>{json.dumps({'description': bible['description'], 'objects': bible['objects']})}</scene_bible>\n"
        f"<expected_in_shot>{json.dumps(expected)}</expected_in_shot>\n"
        + ("Score 0-10 how consistently the candidate shows the SAME room as image 1 (furniture identity, colours, "
           "materials, relative positions; a different viewpoint is expected and is not an inconsistency). "
           if anchor else "There is no anchor: score 0-10 how faithfully the candidate matches the scene bible. ")
        + "List the ids of expected items that are clearly visible AND match their description (designed_visible). "
          "List concrete inconsistencies and generation artifacts (warped geometry, melted or duplicated objects, "
          "impossible furniture). Set people_or_text true if any person, body part, readable text, number or logo appears. "
          "Judge only what is visible.")
    body = {'model': QA_MODEL, 'reasoning': {'effort': 'low'}, 'store': False, 'max_output_tokens': 3000,
            'input': [{'role': 'user', 'content': images + [{'type': 'input_text', 'text': instruction}]}],
            'text': {'format': {'type': 'json_schema', 'name': 'shot_qa', 'schema': QA_SCHEMA, 'strict': True}}}
    for attempt in range(3):
        r = client.post('/responses', json=body)
        if r.status_code < 400: break
        time.sleep(4 * (attempt + 1))
    r.raise_for_status()
    out = r.json()
    text = ''.join(c.get('text', '') for o in out['output'] if o['type'] == 'message' for c in o.get('content', []))
    result = json.loads(text)
    result['usage'] = out.get('usage', {})
    return result


def passed(result: dict, shot: dict) -> bool:
    return (result['consistency_score'] >= PASS_SCORE and not result['people_or_text']
            and set(shot['expected']) <= set(result['designed_visible']))


def rank(result: dict, shot: dict) -> tuple:
    return (passed(result, shot), not result['people_or_text'],
            len(set(shot['expected']) & set(result['designed_visible'])), result['consistency_score'])


def build_scene(name: str, only: list[int] | None = None) -> dict:
    bible = json.loads((SCENES / f'{name}.json').read_text())
    out = BUILD / bible['id']; shots_dir = out / 'shots'; tries = out / 'attempts'
    shots_dir.mkdir(parents=True, exist_ok=True); tries.mkdir(exist_ok=True)
    log_path = out / 'qa.json'
    log = json.loads(log_path.read_text()) if log_path.exists() else {'scene': bible['id'], 'shots': {}}
    client = http()
    anchor = shots_dir / '00.png'
    for shot in bible['shots']:
        sid = shot['id']
        if only is not None and sid not in only:
            continue
        best = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            path = tries / f'{sid:02d}-{attempt}.png'
            started = time.time()
            try:
                image, meta = generate(client, bible, shot, None if sid == 0 else anchor)
            except Exception as e:  # content filter or transient failure: record and retry
                print(f'[{bible["id"]}] shot {sid} attempt {attempt} failed: {e}', flush=True); continue
            path.write_bytes(image)
            result = qa(client, bible, shot, path, None if sid == 0 else anchor)
            print(f'[{bible["id"]}] shot {sid} attempt {attempt}: score {result["consistency_score"]} visible '
                  f'{result["designed_visible"]}/{shot["expected"]} people_or_text={result["people_or_text"]} '
                  f'({time.time() - started:.0f}s)', flush=True)
            entry = {'attempt': attempt, 'file': path.name, **result, 'prompt': meta['prompt'],
                     'image_reasoning_summary': meta['reasoning_summary']}
            if best is None or rank(result, shot) > rank(best, shot):
                best = entry
            if passed(result, shot):
                break
        if best is None:
            raise SystemExit(f'{bible["id"]} shot {sid}: no image generated')
        (shots_dir / f'{sid:02d}.png').write_bytes((tries / best['file']).read_bytes())
        log['shots'][str(sid)] = {**best, 'passed': passed(best, shot), 'expected': shot['expected']}
        log_path.write_text(json.dumps(log, indent=2) + '\n')
    return log


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('scenes', nargs='*', default=[p.stem for p in sorted(SCENES.glob('*.json'))])
    parser.add_argument('--shots', type=int, nargs='*', help='regenerate only these shot ids')
    args = parser.parse_args()
    with ThreadPoolExecutor(len(args.scenes)) as pool:
        for log in pool.map(lambda s: build_scene(s, args.shots), args.scenes):
            ok = sum(v['passed'] for v in log['shots'].values())
            print(f"{log['scene']}: {ok}/{len(log['shots'])} shots passed QA")
