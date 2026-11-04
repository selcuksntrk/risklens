"""Compose the final demo: real phone-viewport footage flush left, the run's real data as type on the right, captions from the voice take.
Everything shown comes from recordings or saved model output; recording-log.json and run-assets/report.json hold the run's numbers.
The look follows earthquake assembly-point signage: signal yellow, ink, paper, condensed Archivo (OFL), IBM Plex Mono (OFL) for data.
The line above the captions is the narration's own waveform, drawn as a seismograph trace.
Usage: uv run --no-project --with httpx --with websockets --with numpy --with pillow python scripts/compose_demo.py <out dir> [--until SECONDS]
"""
import asyncio
import base64
import html
import io
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from align_voice import chunks, place, speech_spans  # noqa: E402
from cdp import Browser  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'docs/submission/private'
F = P / 'footage-v5'; A = F / 'run-assets'; HERO = P / 'hero'; EX = ROOT / 'examples/generated'
W, H, FPS = 1920, 1080, 30
YELLOW, INK, PAPER = (255, 214, 10), (17, 17, 17), (243, 241, 234)
SLOT = (0, 0, 540, 1080)
ROOM_X = (0, 640, 1280); ROOM_W, ROOM_H = 640, 750
COL_X, COL_W = 620, 1220; FULL_X, FULL_W = 80, 1760
TRACE_Y, TRACE_AMP = 892, 24
SECTION_GAP = .7; END_CARD = 6.5

FONTS = 'https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&family=IBM+Plex+Mono:wght@500;600&display=block'
CSS = f'''*{{box-sizing:border-box;margin:0;padding:0}}html,body{{width:1920px;height:1080px;background:transparent;overflow:hidden}}
body{{font-family:Archivo,sans-serif;color:#111;-webkit-font-smoothing:antialiased}}
.col{{position:absolute;left:{COL_X}px;top:58px;width:{COL_W}px}}.full{{position:absolute;left:{FULL_X}px;top:58px;width:{FULL_W}px}}
.H{{font-stretch:62%;font-weight:800;text-transform:uppercase;font-size:128px;line-height:.96;letter-spacing:-.006em}}
.H.xl{{font-size:158px}}.H.m{{font-size:104px}}.H.s{{font-size:84px;line-height:1}}
.b{{font-size:46px;line-height:1.2;font-weight:500;margin-top:26px}}
.tape{{display:inline-block;font-family:"IBM Plex Mono",monospace;font-weight:600;font-size:31px;line-height:1;padding:11px 16px 12px;background:#111;color:#ffd60a;margin-bottom:24px}}
.tape.y{{background:#ffd60a;color:#111}}.tape.r{{background:#e5231b;color:#fff}}.tape.w{{background:#f3f1ea;color:#111}}
.mono{{font-family:"IBM Plex Mono",monospace;font-weight:500;font-size:29px;line-height:1.3}}
.white{{color:#f3f1ea}}.yellow{{color:#ffd60a}}.red{{color:#e5231b}}
.rows{{margin-top:34px}}.rw{{display:grid;grid-template-columns:330px 1fr;column-gap:30px;border-top:4px solid currentColor;padding:20px 0 26px}}
.rw>.k{{font-family:"IBM Plex Mono",monospace;font-weight:600;font-size:31px;line-height:1.22}}.rw>.v{{font-size:48px;line-height:1.14;font-weight:550}}
.strip{{display:grid;grid-template-columns:repeat(10,1fr);gap:0;margin-top:30px}}.strip img{{width:100%;height:216px;object-fit:cover;display:block}}
.tags{{display:flex;flex-wrap:wrap;gap:12px;margin-top:28px}}.tags .tape{{margin:0;font-size:36px}}
.bars{{margin-top:30px;width:100%}}.bar{{display:grid;grid-template-columns:260px 1fr;align-items:center;margin:0 0 7px;font-family:"IBM Plex Mono",monospace;font-weight:500;font-size:28px}}
.track{{position:relative;height:30px;border-bottom:2px solid #555}}.track u{{position:absolute;top:0;bottom:0;display:block}}
.cap{{position:absolute;font-size:42px;line-height:1.16;font-weight:600}}.cap.right{{left:{COL_X}px;width:{COL_W}px;top:938px}}.cap.bottom{{left:{FULL_X}px;width:{FULL_W}px;top:938px}}
.stat{{font-stretch:62%;font-weight:800;font-size:430px;line-height:.86;letter-spacing:-.012em;color:#ffd60a;white-space:nowrap;margin-top:14px}}'''


def col(body, style=''):
    return f'<div class=col style="{style}">{body}</div>'


def full(body, style=''):
    return f'<div class=full style="{style}">{body}</div>'


def row(key, value):
    return f'<div class=rw><div class=k>{key}</div><div class=v>{value}</div></div>'


def build_layers(report):
    h1 = next(h for h in report['hazards'] if h['id'] == 'h1')
    thumbs = ''.join(f'<img src="file://{A}/frames/{k:05d}.jpg">' for k in report['provenance']['keyframes'])
    tags = ''.join(f'<span class="tape y">{html.escape(c["concept"].upper())}</span>' for c in report['plan']['concepts'])
    colors = {'bed': '#f3f1ea', 'wardrobe': '#ffd60a', 'suitcase': '#ff3b30', 'door': '#8f8f8f', 'pedestal fan': '#8f8f8f', 'drying rack': '#8f8f8f'}
    frames_total = report['provenance']['proxy']['frames']
    objects = sorted(report['objects'].values(), key=lambda o: o['frames'][1] - o['frames'][0], reverse=True)[:9]
    objects.sort(key=lambda o: o['frames'][0])
    bars = ''.join(f'<div class="bar white"><span>{html.escape(o["concept"].upper())}</span><div class=track><u style="left:{o["frames"][0] / frames_total * 100:.1f}%;'
                   f'width:{max((o["frames"][1] - o["frames"][0]) / frames_total * 100, 1.2):.1f}%;background:{colors.get(o["concept"], "#8f8f8f")}"></u></div></div>' for o in objects)
    examples = ''.join(f'<div><img src="file://{EX}/{d}/poster.jpg" style="width:100%;height:258px;object-fit:cover;display:block"><div class=mono style="margin-top:8px;font-weight:600">{t}</div></div>'
                       for d, t in (('realhomeistanbul', 'REAL HOME'), ('designedliving', 'LIVING ROOM'), ('designedkids', 'CHILD\'S ROOM'), ('designedkitchen', 'KITCHEN')))
    pair_h = 860
    layers = {
        'hook0': col('<div class="H xl">What could fall when the ground shakes?</div><div class=mono style="margin-top:30px;font-weight:600">REAL VIDEO / MY BEDROOM, ISTANBUL</div>'),
        'hook1': col('<div class="H xl">Wardrobe with suitcases on top</div><div class=b>It could tip over. They could fall.</div>'),
        'hook2': col('<div class=rows style="margin:0">' + row('NEEDS<br>CHECKING', "Is it fixed to the wall? That can't be seen in this video, so RiskLens asks you to check.") + '</div>'
                     '<div class=mono style="margin-top:2px;font-size:26px">OUTLINES: SAM 3.1 MASKS ON MY VIDEO. PERSONAL PHOTOS BLURRED.</div>', 'top:572px'),
        'why': full('<div class="H s white">Earthquake safety includes what is inside the room</div><div class=stat>556 OF 947</div>'
                    '<div class="b white" style="font-size:58px;margin-top:22px;font-weight:600">injuries attributed to non-structural damage</div>'
                    '<div class="mono white" style="margin-top:12px">COMMERCIAL BUILDINGS, NEW ZEALAND EARTHQUAKES 2010–2014, NOT HOMES (YEOW ET AL., 2020)</div>'),
        'theme': full('<span class="tape y" style="font-size:36px;margin:0">BUILD FOR YOUR WORLD / ISTANBUL</span>', 'top:auto;bottom:0'),
        'prod': col('<div class="H" style="font-size:132px">One phone.<br>One room.<br>About a minute.</div><div class=b style="margin-top:20px">Record a room or upload a video. No account.</div>'),
        'prod2': col(f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px">{examples}</div>', 'top:540px'),
        'run': col('<span class="tape y">LIVE RUN ON MY HOME VIDEO</span><div class="H xl yellow">Real models.<br>Waiting shortened.</div><div class=rows style="color:#f3f1ea">'
                   + row('ACTUAL TIME', '1 min 54 s') + row('MODEL CALLS', f'${report["cost_usd"]["total"]:.2f}') + '</div>'),
        'plan': col(f'<span class="tape y">MUSE SPARK 1.3 / PLANNER</span><div class="H yellow">Decides what matters in this room</div><div class=strip>{thumbs}</div><div class=tags>{tags}</div>'),
        'sam': col(f'<span class="tape y">SAM 3.1 / TRACKER</span><div class="H m yellow">Follows each object through the whole video</div><div class=bars>{bars}</div>'
                   f'<div class="mono white" style="margin-top:8px;font-size:25px">EACH BAR: ONE OBJECT FROM THIS RUN, ACROSS THE {report["provenance"]["original_duration_s"]:.0f}-SECOND VIDEO</div>'),
        'evid': col(f'<div style="display:grid;grid-template-columns:450px 1fr;column-gap:44px"><img src="file://{A}/evidence/h1.jpg" style="width:450px;height:800px;object-fit:cover;display:block">'
                    f'<div><span class="tape y">FRAME {h1["evidence_frame"]} / BOX BY SAM 3.1</span><div class="H xl yellow">A real frame and a real box</div></div></div>'),
        'survey': col('<span class="tape y">MUSE SPARK 1.3 / SURVEYOR</span><div class="H yellow">What it can see. What needs checking.</div><div class="rows white">'
                      + row('CAN SEE', 'Two large suitcases on top of the wardrobe. No rail, lip or strap visible.') + row('NEEDS<br>CHECKING', 'Tall white wardrobe: wall fixing not visible.') + '</div>'),
        'fema': col('<span class="tape y">MUSE SPARK 1.3 / FIX PLANNER</span><div class="H yellow">Reads FEMA E-74, then writes the next steps</div><div class="rows white">'
                    + row('§6.5.6.1', 'Shelf-mounted items<br><span class=mono>P. 6-566–6-571</span>') + row('§6.5.2.1', 'Bookshelves<br><span class=mono>P. 6-501–6-507</span>')
                    + row('§6.5.5.3', 'Miscellaneous furniture and fixtures<br><span class=mono>P. 6-561–6-565</span>') + '</div>'),
        'find': col('<span class=tape>ONE FINDING</span><div class="H xl">Blue suitcase on top of the wardrobe</div><div class=b>What the video shows, and what is still unknown.</div>'),
        'todo': col('<span class=tape>WHAT TO DO</span><div class="H m">Move both large suitcases off the wardrobe</div><div class=rows>'
                    + row('FEMA E-74<br>§6.5.6.1', 'Linked to the section the model read.<br><span class=mono>P. 6-566–6-571</span>') + row('ESTIMATE', 'Under $20, about 15 minutes.') + '</div>'),
        'nosrc': col('<div class=rows style="margin:0">' + row('NO SOURCE', '<span class=red style="font-weight:700">No steps.</span> Enforced in the interface and the endpoint.') + '</div>', 'top:640px'),
        'img': f'<div style="position:absolute;left:540px;top:0;height:{pair_h}px;width:1380px;display:flex;justify-content:flex-end;gap:0">'
               f'<div style="position:relative;height:100%"><img src="file://{A}/evidence/h1.jpg" style="height:100%;display:block"><span class=tape style="position:absolute;left:0;top:0;margin:0">MY VIDEO</span></div>'
               f'<div style="position:relative;height:100%"><img src="file://{A}/fixcards/h1.jpg" style="height:100%;display:block"><span class="tape y" style="position:absolute;left:0;top:0;margin:0">MUSE IMAGE 1.0 / AI-MADE PICTURE</span></div></div>',
        'noproof': '<div style="position:absolute;right:0;top:796px"><span class="tape r" style="margin:0;font-size:38px">NOT PROOF ANYTHING WAS FIXED</span></div>',
        'film': col('<span class=tape>AFTER A FIX</span><div class="H xl">Film the item again</div>'),
        'same': col('<div class=rows style="margin:0">' + row('THE SAME<br>VIDEO AGAIN?', 'A SHA-256 check catches it before any model runs.') + '</div>', 'top:310px'),
        'change': col('<div class=rows style="margin:0">' + row('TO SHOW<br>A CHANGE', 'A new video needs the same object, and a visible difference.') + '</div>', 'top:530px'),
        'rooms': full('<div class="H s yellow" style="font-size:96px">Three test rooms, hazards placed on purpose</div>', 'top:768px')
                 + ''.join(f'<span class="tape y" style="position:absolute;left:{x}px;top:0;margin:0">{t}</span>' for x, t in zip(ROOM_X, ('LIVING ROOM / MUSE IMAGE', "CHILDREN'S BEDROOM / MUSE IMAGE", 'KITCHEN + ENTRANCE / MUSE IMAGE'))),
        'qa': '<div style="position:absolute;right:0;top:690px"><span class="tape y" style="margin:0;font-size:36px">MUSE SPARK CHECKED EVERY VIEW: 18 OF 18 PASSED</span></div>',
        'score': ''.join(f'<div style="position:absolute;left:{x}px;top:505px;background:{bg};color:#111;font-stretch:62%;font-weight:800;font-size:170px;line-height:1;padding:2px 26px 8px">{n}</div>'
                         for x, n, bg in zip(ROOM_X, ('5/5', '4/4', '4/5'), ('#ffd60a', '#ffd60a', '#e5231b'))),
        'miss': '<div style="position:absolute;right:0;top:690px"><span class="tape r" style="margin:0;font-size:36px">MISSED: BOXES AND SHOE CABINET NARROWING THE PATH TO THE FRONT DOOR</span></div>',
        'not': '<div class="mono white" style="position:absolute;left:80px;top:996px;font-size:27px">ONE RUN PER ROOM, MATCHED BY HAND. TEST SCENES, NOT REAL HOMES.</div>',
        'close1': col('<div class="H">A visual check, not a building inspection.</div>'),
        'close2': col('<div class="H" style="font-size:92px">Shows the evidence.<br>Honest about what it can\'t see.</div>', 'top:336px'),
        'close3': col('<div class="H" style="background:#111;color:#ffd60a;display:inline-block;padding:6px 20px 10px">One room at a time.</div>', 'top:560px'),
        'end': full('<div class=H style="font-size:360px;line-height:.86">RiskLens</div><div class=b style="font-size:64px;font-weight:650;margin-top:30px">Film a room. See what could fall in an earthquake.</div>'
                    '<div class=rows style="margin-top:40px">' + row('TRY IT', 'selcuksntrk--risklens-web.us-east.modal.run') + row('CODE', 'github.com/selcuksntrk/risklens') + row('MODELS', 'Muse Spark 1.3, SAM 3.1, Muse Image 1.0') + '</div>'
                    '<div class=mono style="font-size:25px;margin-top:2px">BUILT SOLO IN ISTANBUL FOR THE META GLOBAL AI DEVELOPER HACKATHON / INDIE DEVELOPER / BUILD FOR YOUR WORLD<br>REAL HOME: MY OWN RECORDING, PERSONAL PHOTOS BLURRED. TEST ROOMS: AI-MADE WITH MUSE IMAGE.</div>', 'top:44px'),
    }
    return layers


async def render_layers(layers, out):
    out.mkdir(parents=True, exist_ok=True); result = {}
    head = f'<!doctype html><meta charset=utf-8><link rel=stylesheet href="{FONTS}"><style>{CSS}</style>'
    fonts_ready = ('document.fonts.check(\'800 100px Archivo\') && document.fonts.check(\'600 30px "IBM Plex Mono"\') && '
                   'document.fonts.status === "loaded" && [...document.images].every(i => i.complete)')
    async with Browser(width=W, height=H, scale=1, port=9336) as b:
        await b.send('Emulation.setDefaultBackgroundColorOverride', color={'r': 0, 'g': 0, 'b': 0, 'a': 0})
        warm = out / 'warm.html'; warm.write_text(f'{head}<body><div class=H>Warm</div><div class=mono style="font-weight:600">Warm</div><div class=b>Warm</div></body>')
        await b.goto(warm.as_uri(), settle=2.5); await asyncio.sleep(2); warm.unlink()
        for name, body in layers.items():
            page = out / f'{name}.html'; page.write_text(f'{head}<body>{body}</body>')
            await b.goto(page.as_uri(), settle=.05)
            await b.js('Promise.all([document.fonts.load(\'800 100px Archivo\'), document.fonts.load(\'600 30px "IBM Plex Mono"\')])')
            await b.wait_for(fonts_ready, 30, .05)
            over = await b.js('[...document.querySelectorAll(".col,.full")].some(e => { const r = e.getBoundingClientRect(); return r.bottom > 1082 || r.right > 1922 })')
            shot = await b.send('Page.captureScreenshot', format='png')
            arr = np.asarray(Image.open(io.BytesIO(base64.b64decode(shot['data']))).convert('RGBA'), np.uint8)
            ys, xs = np.nonzero(arr[..., 3]); box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1) if len(xs) else (0, 0, 1, 1)
            crop = arr[box[1]:box[3], box[0]:box[2]].astype(np.float32)
            result[name] = (box[0], box[1], crop[..., :3], crop[..., 3:] / 255)
            if over: print('OVERFLOW', name)
            if not name.startswith('cap') and box[3] > 880 and name not in ('evid', 'end', 'rooms', 'not', 'theme'): print('below trace line', name, box)
            page.unlink()
    out.rmdir()
    return result


class Clip:
    """Sequential 30 fps reader for one time-remapped piece of a recording; holds the last frame when it runs out."""
    def __init__(self, path, a, b, seconds, size, top=False):
        self.w, self.h = size; self.last = None
        rate = seconds / max(b - a, .001); y = '0' if top else f'(ih-{self.h})/2'
        vf = (f'trim={a:.3f}:{b:.3f},setpts=(PTS-STARTPTS)*{rate:.4f},fps={FPS},'
              f'scale={self.w}:{self.h}:force_original_aspect_ratio=increase:flags=lanczos,crop={self.w}:{self.h}:(iw-{self.w})/2:{y}')
        self.proc = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'quiet', '-i', str(path), '-vf', vf, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)

    def read(self):
        raw = self.proc.stdout.read(self.w * self.h * 3)
        if len(raw) == self.w * self.h * 3:
            self.last = np.frombuffer(raw, np.uint8).reshape(self.h, self.w, 3).astype(np.float32)
        return self.last

    def close(self):
        self.proc.stdout.close(); self.proc.terminate(); self.proc.wait()


def timeline(plan):
    """Absolute time of every voice piece and caption; every section starts just after the previous one ends."""
    t, sections = .3, []
    for s in plan['sections']:
        start, spans, pieces = t, [], []
        for piece in s['pieces']:
            src = P / piece['src']; a, b = piece['start'], piece['end']
            pieces.append((src, a, b, t, piece.get('gain_db', 0)))
            spans += [(t + x, t + y) for x, y in speech_spans(src, a, b)]
            t += b - a + piece.get('gap_after', 0)
        parts = chunks(s['text'], 100); weights = [len(p) for p in parts]; total = sum(weights); spoken = sum(y - x for x, y in spans); done = 0; cues = []
        for p, w in zip(parts, weights):
            cues.append((place(done, total, spans, spoken, 0), place(done + w, total, spans, spoken, 0), p)); done += w
        sections.append({'start': start, 'end': t, 'pieces': pieces, 'cues': cues}); t += SECTION_GAP
    return sections, t - SECTION_GAP


def mix_voice(S, limit, path):
    inputs, filters = [], []
    for s in S:
        for src, a, b, start, gain in s['pieces']:
            i = len(inputs) // 6; inputs += ['-ss', str(a), '-to', str(b), '-i', str(src)]
            filters.append(f'[{i}:a]aformat=channel_layouts=mono,volume={gain}dB,afade=in:d=0.03,afade=out:st={b - a - .05:.3f}:d=0.05,adelay={int(start * 1000)}:all=1[a{i}]')
    count = len(inputs) // 6
    filters.append(''.join(f'[a{i}]' for i in range(count)) + f'amix=inputs={count}:duration=longest:normalize=0,apad=whole_dur={limit},atrim=0:{limit}[out]')
    subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', *inputs, '-filter_complex', ';'.join(filters), '-map', '[out]', '-ar', '48000', '-c:a', 'pcm_s16le', str(path)], check=True)


def waveform(path, step):
    raw = subprocess.check_output(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(path), '-ac', '1', '-ar', '8000', '-f', 's16le', '-'])
    samples = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    n = max(int(8000 * step), 1); count = len(samples) // n; blocks = samples[:count * n].reshape(count, n)
    low, high = blocks.min(1), blocks.max(1); scale = max(np.percentile(high, 99.5), .01)
    return np.clip(low / scale, -1, 1), np.clip(high / scale, -1, 1)


def main(out, until=None):
    plan = json.loads((P / 'voice-plan.json').read_text()); report = json.loads((A / 'report.json').read_text())
    S, voice_end = timeline(plan); total = voice_end + .6 + END_CARD
    def at(i, prefix):
        return next(c[0] for c in S[i]['cues'] if c[2].lower().startswith(prefix.lower()))
    why_end = at(1, 'Film one room')
    limit = min(until or total, total); n = int(limit * FPS)

    def field_at(t):
        if t < S[1]['start']: return YELLOW
        if t < why_end: return INK
        if t < S[2]['start']: return YELLOW
        if t < S[3]['start']: return INK
        if t < S[5]['start']: return PAPER
        if t < S[6]['start']: return INK
        return YELLOW

    layers = build_layers(report)
    for i, s in enumerate(S):
        for j, c in enumerate(s['cues']):
            wide = i == 5 or (i == 1 and c[0] < why_end - .01)
            tint = '#f3f1ea' if field_at(c[0] + .01) == INK else '#111'
            layers[f'cap{i}_{j}'] = f'<div class="cap {"bottom" if wide else "right"}" style="color:{tint}">{html.escape(c[2])}</div>'
    rendered = asyncio.run(render_layers(layers, out / 'layers-tmp'))

    video = lambda name: F / f'{name}.mp4'
    focus, allh = HERO / 'hero-focus.mp4', HERO / 'hero-all.mp4'
    t2, t3, t4, t5, t6, t7 = S[1], S[2], S[3], S[4], S[5], S[6]
    gap = lambda s: s['end'] + SECTION_GAP
    shots = [  # start, end, file, source from, source to
        (0, at(0, 'RiskLens found'), focus, 25.4, 29.2), (at(0, 'RiskLens found'), at(0, "It can't"), focus, 29.2, 31.0), (at(0, "It can't"), t2['start'], focus, 31.0, 31.4),
        (why_end, gap(t2), video('home'), .8, 8.0),
        (t3['start'], at(2, 'First'), video('run'), 3.0, 10.0), (at(2, 'First'), at(2, 'Then SAM'), video('run'), 10.0, 19.0),
        (at(2, 'Then SAM'), at(2, 'So every'), allh, 24.0, 29.6),
        (at(2, 'So every'), at(2, 'Then Spark'), video('run'), 38.0, 56.0), (at(2, 'Then Spark'), at(2, 'Last'), video('run'), 56.0, 96.0), (at(2, 'Last'), gap(t3), video('run'), 96.0, 126.0),
        (t4['start'], at(3, 'Each next'), video('finding'), 7.5, 15.0), (at(3, 'Each next'), at(3, 'Muse Image'), video('finding'), 15.5, 22.0), (at(3, 'Muse Image'), gap(t4), video('finding'), 33.0, 44.0),
        (t5['start'], at(4, 'The same'), video('verify'), 5.5, 9.0), (at(4, 'The same'), at(4, 'A real change'), video('verify'), 9.0, 9.4),
        (at(4, 'A real change'), gap(t5), video('verify'), 10.12, 10.15),   # holds on "Comparing…", before the result screen
        (t7['start'], at(6, 'and it helps'), video('finding'), .5, 6.5), (at(6, 'and it helps'), t7['end'] + .6, focus, 29.2, 31.4),
    ]
    texts = [
        ('hook0', 0, at(0, 'RiskLens found')), ('hook1', at(0, 'RiskLens found'), t2['start']), ('hook2', at(0, "It can't"), t2['start']),
        ('why', t2['start'], why_end), ('theme', t2['start'], why_end), ('prod', why_end, gap(t2)), ('prod2', at(1, 'Or open'), gap(t2)),
        ('run', t3['start'], at(2, 'First')), ('plan', at(2, 'First'), at(2, 'Then SAM')), ('sam', at(2, 'Then SAM'), at(2, 'So every')), ('evid', at(2, 'So every'), at(2, 'Then Spark')),
        ('survey', at(2, 'Then Spark'), at(2, 'Last')), ('fema', at(2, 'Last'), gap(t3)),
        ('find', t4['start'], at(3, 'Each next')), ('todo', at(3, 'Each next'), at(3, 'Muse Image')), ('nosrc', at(3, 'If that'), at(3, 'Muse Image')), ('img', at(3, 'Muse Image'), gap(t4)), ('noproof', t4['pieces'][1][3], gap(t4)),
        ('film', t5['start'], gap(t5)), ('same', at(4, 'The same'), gap(t5)), ('change', at(4, 'A real change'), gap(t5)),
        ('rooms', t6['start'], gap(t6)), ('qa', at(5, 'Spark checked'), at(5, 'It missed')), ('score', at(5, 'RiskLens found'), gap(t6)), ('miss', at(5, 'It missed'), gap(t6)), ('not', at(5, 'This is a test'), gap(t6)),
        ('close1', t7['start'], t7['end'] + .6), ('close2', at(6, 'It shows'), t7['end'] + .6), ('close3', at(6, 'One room'), t7['end'] + .6),
        ('end', t7['end'] + .6, total),
    ]
    for i, s in enumerate(S):
        for j, c in enumerate(s['cues']):
            end = s['cues'][j + 1][0] if j + 1 < len(s['cues']) else c[1] + .25
            texts.append((f'cap{i}_{j}', c[0], end))
    print({f'section {i + 1}': (round(s['start'], 1), round(s['end'], 1)) for i, s in enumerate(S)}, 'total', round(total, 1))

    voice = out / 'voice.wav'; mix_voice(S, limit, voice)
    step = 6.0 / COL_W; low, high = waveform(voice, step)
    picture = out / 'picture.mp4'
    write = subprocess.Popen(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                              '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', str(picture)], stdin=subprocess.PIPE)
    room_a, room_b = t6['start'], gap(t6); room_clips = []
    end_start = t7['end'] + .6
    current, index = None, -1
    for frame in range(n):
        t = frame / FPS; field = field_at(t)
        img = np.empty((H, W, 3), np.float32); img[:] = field
        shot = next((k for k, s in enumerate(shots) if s[0] <= t < s[1]), None)
        if shot != index:
            if current: current.close()
            current = None; index = shot
            if shot is not None:
                s = shots[shot]; current = Clip(s[2], s[3], s[4], s[1] - s[0], SLOT[2:], top=s[2].parent == F)
        if current is not None:
            pixels = current.read()
            if pixels is not None:
                img[0:SLOT[3], 0:SLOT[2]] = pixels
                if field == PAPER: img[:, SLOT[2]:SLOT[2] + 4] = INK
        if room_a <= t < room_b:
            if not room_clips:
                room_clips = [Clip(EX / d / 'source.mp4', 2.0, 2.0 + room_b - room_a, room_b - room_a, (ROOM_W, ROOM_H)) for d in ('designedliving', 'designedkids', 'designedkitchen')]
            for x, clip in zip(ROOM_X, room_clips):
                pixels = clip.read()
                if pixels is not None:
                    img[0:ROOM_H, x:x + ROOM_W] = pixels
        if t < end_start:   # seismograph trace: the narration's real waveform, scrolling
            wide = room_a <= t < room_b or S[1]['start'] <= t < why_end
            x0, width = (FULL_X, FULL_W) if wide else (COL_X, COL_W)
            line = np.array((243, 241, 234) if field == INK else INK, np.float32)
            head = int(t / step)
            for k in range(width):
                j = head - (width - k)
                lo, hi = (low[j], high[j]) if 0 <= j < len(low) else (0.0, 0.0)
                y0 = int(TRACE_Y - hi * TRACE_AMP); y1 = int(TRACE_Y - lo * TRACE_AMP) + 2
                img[y0:y1, x0 + k] = line
        for name, a, b in texts:
            if a <= t < b:
                x, y, rgb, alpha = rendered[name]; view = img[y:y + rgb.shape[0], x:x + rgb.shape[1]]
                if not name.startswith('cap') and t - a < .2:   # hard wipe in, no fades
                    edge = int(rgb.shape[1] * (1 - (1 - (t - a) / .2) ** 3)); alpha = alpha.copy(); alpha[:, edge:] = 0
                view[:] = view * (1 - alpha) + rgb * alpha
        write.stdin.write(img.astype(np.uint8).tobytes())
    write.stdin.close(); write.wait()
    if current: current.close()
    for clip in room_clips: clip.close()

    final = out / 'risklens-demo.mp4'
    subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(picture), '-i', str(voice), '-map', '0:v:0', '-map', '1:a:0', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-t', str(limit), '-movflags', '+faststart', str(final)], check=True)
    picture.unlink(); voice.unlink()
    print(final, round(limit, 1), 's')


if __name__ == '__main__':
    out_dir = Path(sys.argv[1]).resolve(); out_dir.mkdir(parents=True, exist_ok=True)
    main(out_dir, float(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[2] == '--until' else None)
