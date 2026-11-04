"""Compose the final demo: real phone-viewport footage on the left, real run data as text on the right, captions from the voice take.
Everything shown comes from recordings or saved model output; recording-log.json and run-assets/report.json hold the run's numbers.
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
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from align_voice import chunks, place, speech_spans  # noqa: E402
from cdp import Browser  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'docs/submission/private'
F = P / 'footage-v5'; A = F / 'run-assets'; HERO = P / 'hero'; EX = ROOT / 'examples/generated'
W, H, FPS = 1920, 1080, 30
BG = (15, 16, 18)
PHONE = (180, 51, 452, 978); WIDE = (130, 50, 552, 980)     # x, y, w, h
ROOM_X = (110, 687, 1264); ROOM_Y, ROOM_W, ROOM_H = 221, 546, 440
SECTION_GAP = .7; END_CARD = 6.5

CSS = '''*{box-sizing:border-box;margin:0}html,body{width:1920px;height:1080px;background:transparent;overflow:hidden}
body{font-family:-apple-system,"SF Pro Display","Helvetica Neue",Arial,sans-serif;color:#f4f4f2;-webkit-font-smoothing:antialiased}
.panel{position:absolute;left:790px;top:88px;width:1030px}
.eye{color:#ff7a3d;font-size:27px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;margin-bottom:20px}
h1{font-size:74px;line-height:1.07;font-weight:750;letter-spacing:-.022em;margin-bottom:26px}
h2{font-size:62px;line-height:1.12;font-weight:720;letter-spacing:-.015em;margin-bottom:18px}
p{font-size:40px;line-height:1.3;color:#cfd0d2}.small{font-size:27px;color:#a7a9ac;line-height:1.35}
.chips{display:flex;flex-wrap:wrap;gap:13px;margin-top:22px}.chip{background:#26272b;border-radius:40px;padding:11px 25px;font-size:32px;font-weight:600}
.thumbs{display:grid;grid-template-columns:repeat(10,1fr);gap:7px}.thumbs img{width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:7px;display:block}
.card{background:#1c1d21;border-radius:20px;padding:26px 32px;margin-top:20px}.card b{display:block;font-size:27px;letter-spacing:.06em;margin-bottom:9px;text-transform:uppercase}
.card p{color:#f4f4f2}.ok b{color:#78e08c}.warn b{color:#ffb454}.src b{color:#40c4ff}.miss b{color:#ff7a3d}
.row{display:flex;gap:26px;align-items:flex-start}.fig img{height:600px;border-radius:16px;display:block}.fig span{display:block;font-size:27px;color:#cfd0d2;margin-top:12px}
.bars{margin-top:16px}.bar{display:flex;align-items:center;gap:18px;margin:9px 0;font-size:26px;color:#cfd0d2}.bar i{font-style:normal;width:190px;flex:none;text-align:right}
.track{position:relative;flex:1;height:24px;background:#1c1d21;border-radius:6px}.track u{position:absolute;top:0;bottom:0;border-radius:6px;display:block}
.line{font-size:58px;line-height:1.14;font-weight:700;letter-spacing:-.015em;margin-top:28px}
.full{position:absolute;left:110px;top:72px;width:1700px}
.label{position:absolute;top:673px;font-size:36px;font-weight:650}.badge{position:absolute;top:566px;background:#0f1012ee;border-radius:16px;padding:2px 26px;font-size:92px;font-weight:800}
.stat{font-size:200px;font-weight:800;letter-spacing:-.04em;color:#ff7a3d;line-height:1.02;margin:14px 0 4px}
.rooms{display:grid;grid-template-columns:repeat(3,1fr);gap:30px;margin-top:8px}.room{position:relative}.room img{width:100%;height:440px;object-fit:cover;border-radius:18px;display:block}.room span{display:block;font-size:34px;font-weight:650;margin-top:12px}
.cap{position:absolute;font-size:40px;line-height:1.26;font-weight:500;color:#fff}.cap.right{left:790px;width:1030px;bottom:44px}.cap.bottom{left:160px;width:1600px;bottom:40px;text-align:center}
.brand{font-size:120px;font-weight:800;letter-spacing:-.03em}.link{font-size:50px;font-weight:650;color:#ff7a3d;margin-top:14px}'''


def panel(eye, head, body='', big=True):
    title = f'<h1>{head}</h1>' if big else f'<h2>{head}</h2>'
    return f'<div class=panel><div class=eye>{eye}</div>{title}{body}</div>'


def build_layers(report):
    h1 = next(h for h in report['hazards'] if h['id'] == 'h1')
    keyframes = report['provenance']['keyframes']
    thumbs = ''.join(f'<img src="file://{A}/frames/{k:05d}.jpg">' for k in keyframes)
    chips = ''.join(f'<span class=chip>{html.escape(c["concept"])}</span>' for c in report['plan']['concepts'])
    colors = {'bed': '#78e08c', 'wardrobe': '#ff7a3d', 'suitcase': '#40c4ff', 'door': '#b39bff', 'pedestal fan': '#ffb454', 'drying rack': '#ff8fb1'}
    frames_total = report['provenance']['proxy']['frames']
    objects = sorted(report['objects'].values(), key=lambda o: o['frames'][1] - o['frames'][0], reverse=True)[:9]
    objects.sort(key=lambda o: o['frames'][0])
    bars = ''.join(f'<div class=bar><i>{html.escape(o["concept"])}</i><div class=track><u style="left:{o["frames"][0] / frames_total * 100:.1f}%;'
                   f'width:{max((o["frames"][1] - o["frames"][0]) / frames_total * 100, 1.2):.1f}%;background:{colors.get(o["concept"], "#ccc")}"></u></div></div>' for o in objects)
    thumb4 = ''.join(f'<div style="flex:1"><img src="file://{EX}/{d}/poster.jpg" style="width:100%;height:290px;object-fit:cover;border-radius:14px;display:block"><span class=small style="display:block;margin-top:8px;color:#f4f4f2">{t}</span></div>'
                     for d, t in (('realhomeistanbul', 'Real home'), ('designedliving', 'Living room'), ('designedkids', "Children's room"), ('designedkitchen', 'Kitchen')))
    return {
        'hook0': panel('Real video · my bedroom in Istanbul', 'What could fall when the ground shakes?'),
        'hook1': panel('Found in the video', 'Wardrobe with suitcases on top', '<p>It could tip over. They could fall.</p>'),
        'hook2': '<div class=panel style="top:470px"><div class="card warn"><b>Needs checking</b><p>Is it fixed to the wall? That can\'t be seen in this video, so RiskLens asks you to check.</p></div>'
                 '<p class=small style="margin-top:18px">Coloured outlines: SAM 3.1 masks on my video. Personal photos blurred.</p></div>',
        'why': '<div class=full style="top:120px"><div class=eye>Build for your world · Istanbul</div><h1>Earthquake safety includes what is inside the room</h1>'
               '<div class=stat>556 of 947</div><p style="font-size:44px;color:#f4f4f2">injuries attributed to non-structural damage</p>'
               '<p class=small style="margin-top:14px;font-size:30px">Commercial buildings in the 2010–2014 New Zealand earthquakes, not homes (Yeow et al., 2020).</p></div>',
        'prod': panel('RiskLens', 'One phone.<br>One room.<br>About a minute.', '<p>Record a room or upload a video. No account.</p>'),
        'prod2': f'<div class=panel style="top:530px"><div class=eye style="margin-bottom:14px">Or try an example</div><div style="display:flex;gap:16px">{thumb4}</div></div>',
        'run': panel('Live run on my home video', 'Real models.<br>Waiting shortened.', f'<p>Actual time: 1 min 54 s · ${report["cost_usd"]["total"]:.2f} in model calls.</p>'),
        'plan': panel('Muse Spark 1.3 · planner', 'Decides what matters in this room', f'<div class=thumbs>{thumbs}</div><div class=chips>{chips}</div>', big=False),
        'sam': panel('SAM 3.1 · tracker', 'Follows each object through the whole video', f'<div class=bars>{bars}</div><p class=small style="margin-top:12px">Each bar is one object from this run, across the {report["provenance"]["original_duration_s"]:.0f}-second video.</p>', big=False),
        'evid': panel('Evidence', 'A real frame and a real box', f'<div class=fig><img src="file://{A}/evidence/h1.jpg"><span>Frame {h1["evidence_frame"]} · box by SAM 3.1</span></div>', big=False),
        'survey': panel('Muse Spark 1.3 · surveyor', 'What it can see. What needs checking.',
                        '<div class="card ok"><b>Can see</b><p>Two large suitcases on top of the wardrobe. No rail, lip or strap visible.</p></div>'
                        '<div class="card warn"><b>Needs checking</b><p>Tall white wardrobe: wall fixing not visible.</p></div>', big=False),
        'fema': panel('Muse Spark 1.3 · fix planner', 'Reads FEMA E-74, then writes the next steps',
                      '<div class="card src"><b>§6.5.6.1</b><p>Shelf-mounted items · p. 6-566–6-571</p></div><div class="card src"><b>§6.5.2.1</b><p>Bookshelves · p. 6-501–6-507</p></div>'
                      '<div class="card src"><b>§6.5.5.3</b><p>Miscellaneous furniture and fixtures · p. 6-561–6-565</p></div>', big=False),
        'find': panel('One finding', 'Blue suitcase on top of the wardrobe', '<p>What the video shows, and what is still unknown.</p>', big=False),
        'todo': panel('What to do', 'Move both large suitcases off the wardrobe', '<div class="card src"><b>FEMA E-74 §6.5.6.1 · p. 6-566–6-571</b><p>Linked to the section the model read.</p></div><p class=small style="margin-top:16px">Rough estimate: under $20, about 15 minutes.</p>', big=False),
        'nosrc': '<div class=panel style="top:610px"><div class="card warn"><b>No source, no steps</b><p>Enforced in the interface and the endpoint.</p></div></div>',
        'img': f'<div class=panel><div class=eye>Muse Image 1.0</div><div class=row><div class=fig><img src="file://{A}/evidence/h1.jpg" style="height:640px"><span>My video</span></div>'
               f'<div class=fig><img src="file://{A}/fixcards/h1.jpg" style="height:640px"><span>Possible fix: AI-made picture</span></div></div></div>',
        'noproof': '<div class=panel style="top:852px"><p style="color:#ff7a3d;font-weight:700;font-size:37px;text-align:right">Not proof anything was fixed.</p></div>',
        'film': panel('After a fix', 'Film the item again'),
        'same': '<div class=panel style="top:270px"><div class="card warn"><b>The same video again?</b><p>A SHA-256 check catches it before any model runs.</p></div></div>',
        'change': '<div class=panel style="top:560px"><div class="card src"><b>To show a change, a new video needs</b><p>The same object, and a visible difference.</p></div></div>',
        'rooms': '<div class=full><div class=eye>Tested on known answers · AI-made with Muse Image</div><h2>Three test rooms, hazards placed on purpose</h2></div>'
                 + ''.join(f'<div class=label style="left:{x}px">{t}</div>' for x, t in zip(ROOM_X, ('Living room', "Children's bedroom", 'Kitchen and entrance'))),
        'qa': '<div class=full style="top:760px"><span class=chip style="display:inline-block">Muse Spark checked every view: 18 of 18 passed</span></div>',
        'score': ''.join(f'<div class=badge style="left:{x + 18}px;color:{c}">{n}</div>' for x, n, c in zip(ROOM_X, ('5/5', '4/4', '4/5'), ('#78e08c', '#78e08c', '#ff7a3d'))),
        'miss': '<div class=full style="top:760px;text-align:right"><span class=chip style="display:inline-block;background:#3a2015;color:#ffb08c">Missed: boxes and shoe cabinet narrowing the path to the front door</span></div>',
        'not': '<div class=full style="top:850px"><p class=small style="text-align:center;font-size:32px">One run per room, matched by hand. Test scenes, not real homes.</p></div>',
        'close1': '<div class=panel style="top:120px"><div class=line>A visual check, not a building inspection.</div></div>',
        'close2': '<div class=panel style="top:310px"><div class=line style="color:#ffb454">Shows the evidence.</div><div class=line style="color:#ffb454">Honest about what it can\'t see.</div></div>',
        'close3': '<div class=panel style="top:640px"><div class=line style="color:#ff7a3d">One room at a time.</div></div>',
        'end': '<div class=full style="top:150px"><div class=brand>RiskLens</div><p style="font-size:50px;color:#f4f4f2;margin:10px 0 44px">Film a room. See what could fall in an earthquake.</p>'
               '<div class=link>selcuksntrk--risklens-web.us-east.modal.run</div><div class=link>github.com/selcuksntrk/risklens</div>'
               '<p style="margin-top:52px;font-size:36px">Muse Spark 1.3 · SAM 3.1 · Muse Image 1.0 · FEMA E-74</p>'
               '<p class=small style="margin-top:16px;font-size:30px">Built solo in Istanbul for the Meta Global AI Developer Hackathon · Indie Developer · Build for Your World.<br>'
               'Real home: my own recording, personal photos blurred. Test rooms: AI-made with Muse Image.</p></div>',
    }


async def render_layers(layers, out):
    out.mkdir(parents=True, exist_ok=True); result = {}
    async with Browser(width=W, height=H, scale=1, port=9336) as b:
        await b.send('Emulation.setDefaultBackgroundColorOverride', color={'r': 0, 'g': 0, 'b': 0, 'a': 0})
        for name, body in layers.items():
            page = out / f'{name}.html'; page.write_text(f'<!doctype html><meta charset=utf-8><style>{CSS}</style><body>{body}</body>')
            await b.goto(page.as_uri(), settle=.05)
            await b.wait_for('[...document.images].every(i => i.complete) && document.fonts.status === "loaded"', 15, .05)
            shot = await b.send('Page.captureScreenshot', format='png')
            image = Image.open(io.BytesIO(base64.b64decode(shot['data']))).convert('RGBA'); arr = np.asarray(image, np.uint8)
            ys, xs = np.nonzero(arr[..., 3]); box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1) if len(xs) else (0, 0, 1, 1)
            crop = arr[box[1]:box[3], box[0]:box[2]].astype(np.float32)
            result[name] = (box[0], box[1], crop[..., :3], crop[..., 3:] / 255)
            page.unlink()
    out.rmdir()
    return result


class Clip:
    """Sequential 30 fps reader for one time-remapped piece of a recording; holds the last frame when it runs out."""
    def __init__(self, path, a, b, seconds, size, cover=False):
        self.w, self.h = size; self.last = None
        rate = seconds / max(b - a, .001)
        fit = f'scale={self.w}:-2:flags=lanczos,crop={self.w}:{self.h}' if cover else f'scale={self.w}:{self.h}:flags=lanczos'
        vf = f'trim={a:.3f}:{b:.3f},setpts=(PTS-STARTPTS)*{rate:.4f},fps={FPS},{fit}'
        self.proc = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(path), '-vf', vf, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)

    def read(self):
        raw = self.proc.stdout.read(self.w * self.h * 3)
        if len(raw) == self.w * self.h * 3:
            self.last = np.frombuffer(raw, np.uint8).reshape(self.h, self.w, 3).astype(np.float32)
        return self.last

    def close(self):
        self.proc.stdout.close(); self.proc.terminate(); self.proc.wait()


def rounded(w, h, r):
    image = Image.new('L', (w * 3, h * 3), 0); ImageDraw.Draw(image).rounded_rectangle((0, 0, w * 3 - 1, h * 3 - 1), r * 3, fill=255)
    return np.asarray(image.resize((w, h), Image.LANCZOS), np.float32)[..., None] / 255


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
        parts = chunks(s['text']); weights = [len(p) for p in parts]; total = sum(weights); spoken = sum(y - x for x, y in spans); done = 0; cues = []
        for p, w in zip(parts, weights):
            cues.append((place(done, total, spans, spoken, 0), place(done + w, total, spans, spoken, 0), p)); done += w
        sections.append({'start': start, 'end': t, 'pieces': pieces, 'cues': cues}); t += SECTION_GAP
    return sections, t - SECTION_GAP


def main(out, until=None):
    plan = json.loads((P / 'voice-plan.json').read_text()); report = json.loads((A / 'report.json').read_text())
    S, voice_end = timeline(plan); total = voice_end + .6 + END_CARD
    def at(i, prefix):
        return next(c[0] for c in S[i]['cues'] if c[2].lower().startswith(prefix.lower()))
    layers = build_layers(report)
    # the "why" card and the test rooms use the full width, so their captions sit at the bottom
    why_end = at(1, 'Film one room')
    for i, s in enumerate(S):
        for j, c in enumerate(s['cues']):
            place_class = 'bottom' if i == 5 or (i == 1 and c[0] < why_end - .01) else 'right'
            layers[f'cap{i}_{j}'] = f'<div class="cap {place_class}">{html.escape(c[2])}</div>'
    rendered = asyncio.run(render_layers(layers, out / 'layers-tmp'))

    video = lambda name: F / f'{name}.mp4'
    focus, allh = HERO / 'hero-focus.mp4', HERO / 'hero-all.mp4'
    t1, t2, t3, t4 = S[0], S[1], S[2], S[3]; t5, t6, t7 = S[4], S[5], S[6]
    gap = lambda s: s['end'] + SECTION_GAP
    shots = [  # start, end, file, source from, source to, slot
        (0, at(0, 'RiskLens found'), focus, 25.4, 29.2, WIDE), (at(0, 'RiskLens found'), at(0, "It can't"), focus, 29.2, 31.0, WIDE), (at(0, "It can't"), t2['start'], focus, 31.0, 31.4, WIDE),
        (why_end, gap(t2), video('home'), .8, 8.0, PHONE),
        (t3['start'], at(2, 'First'), video('run'), 3.0, 10.0, PHONE), (at(2, 'First'), at(2, 'Then SAM'), video('run'), 10.0, 19.0, PHONE),
        (at(2, 'Then SAM'), at(2, 'So every'), allh, 24.0, 29.6, WIDE),
        (at(2, 'So every'), at(2, 'Then Spark'), video('run'), 38.0, 56.0, PHONE), (at(2, 'Then Spark'), at(2, 'Last'), video('run'), 56.0, 96.0, PHONE), (at(2, 'Last'), gap(t3), video('run'), 96.0, 126.0, PHONE),
        (t4['start'], at(3, 'Each next'), video('finding'), 7.5, 15.0, PHONE), (at(3, 'Each next'), at(3, 'Muse Image'), video('finding'), 15.5, 22.0, PHONE), (at(3, 'Muse Image'), gap(t4), video('finding'), 33.0, 44.0, PHONE),
        (t5['start'], at(4, 'The same'), video('verify'), 5.5, 9.0, PHONE), (at(4, 'The same'), at(4, 'A real change'), video('verify'), 9.0, 9.4, PHONE),
        (at(4, 'A real change'), gap(t5), video('verify'), 10.12, 10.15, PHONE),   # holds on "Comparing…", before the result screen
        (t7['start'], at(6, 'and it helps'), video('finding'), .5, 6.5, PHONE), (at(6, 'and it helps'), t7['end'] + .6, focus, 29.2, 31.4, WIDE),
    ]
    def text(name, a, b): return (name, a, b)
    texts = [
        text('hook0', 0, at(0, 'RiskLens found')), text('hook1', at(0, 'RiskLens found'), t2['start'] - .1), text('hook2', at(0, "It can't"), t2['start'] - .1),
        text('why', t2['start'], why_end - .05), text('prod', why_end, gap(t2) - .1), text('prod2', at(1, 'Or open'), gap(t2) - .1),
        text('run', t3['start'], at(2, 'First')), text('plan', at(2, 'First'), at(2, 'Then SAM')), text('sam', at(2, 'Then SAM'), at(2, 'So every')), text('evid', at(2, 'So every'), at(2, 'Then Spark')),
        text('survey', at(2, 'Then Spark'), at(2, 'Last')), text('fema', at(2, 'Last'), gap(t3) - .1),
        text('find', t4['start'], at(3, 'Each next')), text('todo', at(3, 'Each next'), at(3, 'Muse Image')), text('nosrc', at(3, 'If that'), at(3, 'Muse Image')), text('img', at(3, 'Muse Image'), gap(t4) - .1), text('noproof', at(3, 'but it'), gap(t4) - .1),
        text('film', t5['start'], gap(t5) - .1), text('same', at(4, 'The same'), gap(t5) - .1), text('change', at(4, 'A real change'), gap(t5) - .1),
        text('rooms', t6['start'], gap(t6) - .1), text('qa', at(5, 'Spark checked'), at(5, 'It missed')), text('score', at(5, 'RiskLens found'), gap(t6) - .1), text('miss', at(5, 'It missed'), gap(t6) - .1), text('not', at(5, 'This is a test'), gap(t6) - .1),
        text('close1', t7['start'], t7['end'] + .5), text('close2', at(6, 'It shows'), t7['end'] + .5), text('close3', at(6, 'One room'), t7['end'] + .5),
        text('end', t7['end'] + .6, total),
    ]
    for i, s in enumerate(S):
        for j, c in enumerate(s['cues']):
            end = s['cues'][j + 1][0] if j + 1 < len(s['cues']) else c[1] + .25
            texts.append((f'cap{i}_{j}', c[0], end))
    print({f'section {i + 1}': (round(s['start'], 1), round(s['end'], 1)) for i, s in enumerate(S)}, 'total', round(total, 1))

    limit = min(until or total, total); n = int(limit * FPS)
    picture = out / 'picture.mp4'
    write = subprocess.Popen(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                              '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', str(picture)], stdin=subprocess.PIPE)
    base = np.empty((H, W, 3), np.float32); base[:] = BG
    masks = {PHONE: rounded(PHONE[2], PHONE[3], 40), WIDE: rounded(WIDE[2], WIDE[3], 40)}
    room_mask = rounded(ROOM_W, ROOM_H, 18); room_a, room_b = t6['start'], gap(t6) - .1; room_clips = []
    current, index = None, -1
    for frame in range(n):
        t = frame / FPS; img = base.copy()
        shot = next((k for k, s in enumerate(shots) if s[0] <= t < s[1]), None)
        if shot != index:
            if current: current.close()
            current = None; index = shot
            if shot is not None:
                s = shots[shot]; current = Clip(s[2], s[3], s[4], s[1] - s[0], s[5][2:])
        if current is not None:
            s = shots[index]; pixels = current.read()
            if pixels is not None:
                x, y, w, h = s[5]; view = img[y:y + h, x:x + w]; mask = masks[s[5]]
                view[:] = view * (1 - mask) + pixels * mask
        if room_a <= t < room_b:
            if not room_clips:
                room_clips = [Clip(EX / d / 'source.mp4', 2.0, 2.0 + room_b - room_a, room_b - room_a, (ROOM_W, ROOM_H), cover=True) for d in ('designedliving', 'designedkids', 'designedkitchen')]
            fade = min(1.0, (t - room_a) / .22, (room_b - t) / .15)
            for x, clip in zip(ROOM_X, room_clips):
                pixels = clip.read()
                if pixels is not None:
                    view = img[ROOM_Y:ROOM_Y + ROOM_H, x:x + ROOM_W]; mask = room_mask * max(fade, 0)
                    view[:] = view * (1 - mask) + pixels * mask
        for name, a, b in texts:
            if a <= t < b:
                fade = min(1.0, (t - a) / .22, (b - t) / .15) if not name.startswith('cap') else 1.0
                x, y, rgb, alpha = rendered[name]; view = img[y:y + rgb.shape[0], x:x + rgb.shape[1]]; alpha = alpha * max(fade, 0)
                view[:] = view * (1 - alpha) + rgb * alpha
        write.stdin.write(img.astype(np.uint8).tobytes())
    write.stdin.close(); write.wait()
    if current: current.close()
    for clip in room_clips: clip.close()

    inputs, filters = [], []
    for s in S:
        for src, a, b, start, gain in s['pieces']:
            i = len(inputs) // 6; inputs += ['-ss', str(a), '-to', str(b), '-i', str(src)]
            filters.append(f'[{i + 1}:a]aformat=channel_layouts=mono,volume={gain}dB,afade=in:d=0.03,afade=out:st={b - a - .05:.3f}:d=0.05,adelay={int(start * 1000)}:all=1[a{i}]')
    count = len(inputs) // 6
    filters.append(''.join(f'[a{i}]' for i in range(count)) + f'amix=inputs={count}:duration=longest:normalize=0,apad=whole_dur={limit},atrim=0:{limit},loudnorm=I=-16:TP=-1.5:LRA=11[out]')
    final = out / 'risklens-demo.mp4'
    subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(picture), *inputs, '-filter_complex', ';'.join(filters), '-map', '0:v:0', '-map', '[out]',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-t', str(limit), '-movflags', '+faststart', str(final)], check=True)
    print(final, round(limit, 1), 's')


if __name__ == '__main__':
    out_dir = Path(sys.argv[1]).resolve(); out_dir.mkdir(parents=True, exist_ok=True)
    main(out_dir, float(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[2] == '--until' else None)
