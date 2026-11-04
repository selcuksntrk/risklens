"""Record the demo's screen footage from the REAL deployed application (headless Chrome, 1920x1080), Nov 4 storyboard.

Spends model budget: one live run of the designed children's-bedroom sample (~$0.3), one Muse Image illustration
($0.01), one same-file comparison (hash guard, no verifier model call).
Outputs (git-ignored) under docs/submission/private/footage-v3/:
  01 real-home report · 02 home + samples · 03 live run (wait shortened, labelled) · 04 evidence, next steps, illustration
  05 same-file guard · 06 designed scenes + answer key · 07 real-home replay + end card
  cards/*.html and recording-log.json (timings, scan IDs, release, outcomes)
Usage: backend/.venv/bin/python scripts/record_demo.py [URL]
"""
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdp import Browser, Recorder  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/submission/private/footage-v3'
SAME_FILE = ROOT / 'examples/generated/designedkids/source.mp4'
FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
URL = (sys.argv[1] if len(sys.argv) > 1 else 'https://selcuksntrk--risklens-web.us-east.modal.run').rstrip('/')
LIVE_SAMPLE = 'designed-kids-bedroom'

CARD_CSS = '''*{box-sizing:border-box}body{margin:0;background:#131313;color:#e7eef5;font:20px/1.4 -apple-system,"Helvetica Neue",Arial,sans-serif;
height:100vh;display:flex;align-items:center;justify-content:center}main{width:1180px}h1{font-size:46px;margin:0 0 6px;letter-spacing:-.02em}h2{font-size:30px;margin:0 0 12px;letter-spacing:-.01em}
.muted{color:#a5a5a5}.tag{display:inline-block;color:#ff7a3d;font-size:16px;letter-spacing:.08em;font-weight:700;margin-bottom:10px}
table{width:100%;border-collapse:collapse;margin:10px 0 14px}th,td{text-align:left;padding:6px 12px;border-bottom:1px solid #2e2e2e}th{color:#a5a5a5;font-weight:600;font-size:17px}
td.n{font-weight:800;font-size:22px;color:#ff7a3d;font-variant-numeric:tabular-nums}
.flow{display:flex;gap:12px;align-items:stretch;margin:10px 0}.box{flex:1;background:#1b1b1b;border:1px solid #2e2e2e;border-radius:14px;padding:14px;font-size:18px}
.box b{display:block;color:#ff7a3d;font-size:19px;margin-bottom:4px}.arrow{align-self:center;color:#a5a5a5;font-size:26px}.note{font-size:17px;color:#a5a5a5;margin-top:12px}
img{width:100%;border-radius:12px;border:1px solid #2e2e2e}a{color:#ff7a3d}.big{font-size:30px;margin:8px 0}'''


def cards():
    d = OUT / 'cards'; d.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((ROOT / 'examples/generated/catalog.json').read_text())
    rows = ''.join(
        f"<tr><td>{r['title'].replace('Designed scene: ', '').capitalize()}</td><td class=n>{r['answer_key']['matched']}/{r['answer_key']['designed']}</td>"
        f"<td>{', '.join(h['label'] for h in r['answer_key']['hazards'] if not h['matched_finding']) or '—'}</td>"
        f"<td>{'none' if not any(c.get('flagged') for c in r['answer_key']['controls']) else 'flagged'}</td></tr>"
        for r in catalog if r.get('answer_key'))
    sheet = (ROOT / 'examples/build/strip.jpg').as_uri()
    (d / 'designed.html').write_text(f'''<!doctype html><meta charset=utf-8><style>{CARD_CSS}</style><main>
<span class=tag>TESTING ON KNOWN CONTENT · DESIGNED SCENES</span><h2>We designed three Istanbul rooms with hazards placed on purpose</h2>
<div class=flow><div class=box><b>Scene design</b>Room, objects and an answer key, written before any analysis</div><div class=arrow>→</div>
<div class=box><b>Muse Image 1.0</b>Six views per room, each anchored to the first shot</div><div class=arrow>→</div>
<div class=box><b>Muse Spark 1.3</b>QA gate: same room? designed hazards visible? 18/18 passed</div><div class=arrow>→</div>
<div class=box><b>Phone-style video</b>Handheld walkthrough, labelled AI-generated</div></div>
<img src="{sheet}" style="width:100%;height:auto;border:0">
<table><tr><th>Scene</th><th>Matched</th><th>Missed</th><th>Secured control flagged</th></tr>{rows}</table>
<div class=note>One recorded run per scene; author-matched from each finding's object and evidence box; second human check pending.
These are designed scenes, not real homes: this is not an accuracy measurement.</div></main>''')
    (d / 'end.html').write_text(f'''<!doctype html><meta charset=utf-8><style>{CARD_CSS}</style><main>
<h1>RiskLens</h1><div class=muted style="font-size:26px;margin-bottom:26px">See what could fall before the ground shakes.</div>
<div class=big>Try it: <a>{URL.replace('https://', '')}</a></div><div class=big>Code: <a>github.com/selcuksntrk/risklens</a></div>
<div class=note style="margin-top:30px">Built during the Meta Global AI Developer Hackathon · Indie Developer · Build for Your World.<br>
Muse Spark 1.3 · SAM 3.1 · Muse Image 1.0 · FEMA E-74. Visual screening prototype, not a building inspection or safety certificate.<br>
Real recording: Selçuk's home, Istanbul (personal photos blurred). Designed scenes generated with Muse Image and labelled as AI-generated. No music.</div></main>''')
    return d


def label_png(text, path):
    img = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0)); draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, 32); w = draw.textlength(text, font=font)
    x0, y0 = 1920 - w - 90, 1080 - 110
    draw.rounded_rectangle((x0, y0, x0 + w + 48, y0 + 62), 18, fill=(0, 0, 0, 205))
    draw.text((x0 + 24, y0 + 12), text, font=font, fill=(255, 255, 255, 255)); img.save(path)


def ff(*args):
    subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', *map(str, args)], check=True)


def cut(src, dst, start, end, speed=1.0, label=None):
    vf = f'trim={start:.2f}:{end:.2f},setpts=(PTS-STARTPTS)/{speed}'
    if label:
        png = OUT / (dst.stem + '-label.png'); label_png(label, png)
        ff('-i', src, '-i', png, '-filter_complex', f'[0:v]{vf}[v];[v][1:v]overlay=0:0,fps=30,format=yuv420p', '-c:v', 'libx264', '-crf', '16', dst)
    else:
        ff('-i', src, '-vf', f'{vf},fps=30,format=yuv420p', '-c:v', 'libx264', '-crf', '16', dst)


def labelled(src, dst, text):
    cut(src, dst, 0, 9999, label=text)


def concat(parts, dst):
    lst = OUT / (dst.stem + '-concat.txt'); lst.write_text(''.join(f"file '{p}'\n" for p in parts))
    ff('-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', dst)


SCROLL_TO = 'document.querySelector({sel})?.scrollIntoView({{behavior:"smooth", block:"{block}"}})'


async def scroll_to(b, selector, block='start', wait=4.0):
    await b.js(SCROLL_TO.format(sel=json.dumps(selector), block=block)); await asyncio.sleep(wait)


async def main():
    OUT.mkdir(parents=True, exist_ok=True); d = cards(); log = {'url': URL, 'started': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    async with Browser(width=1097, height=617, scale=1.75, port=9334) as b:
        await b.goto(URL + '/#/', settle=3)
        log['release'] = await b.js('fetch("/api/health").then(r => r.json()).then(j => j.version)')

        # 01 · the real home: the list of things to check, then the top finding on its own screen.
        async with Recorder(b, OUT / '01-raw.mp4'):
            await b.goto(URL + '/#/scan/realhomeistanbul', settle=4); await asyncio.sleep(4)
            await b.js('document.querySelector(".finding-row").click()'); await asyncio.sleep(5)
            await scroll_to(b, '.unknown', block='center', wait=6)
            await scroll_to(b, '.todo', block='center', wait=6)

        # 02 · home: the question, the examples, the process told with the real run.
        async with Recorder(b, OUT / '02.mp4'):
            await b.goto(URL + '/#/', settle=3); await asyncio.sleep(6)
            await scroll_to(b, '#examples', wait=6)
            await scroll_to(b, '#how', wait=5)
            await b.smooth_scroll(420, 4); await asyncio.sleep(4)

        # 03 · a genuinely new live run of a designed example, started from its report (wait shortened later, labelled).
        rec = Recorder(b, OUT / 'raw-run.mp4')
        async with rec:
            t0 = time.time()
            await b.goto(URL + '/#/scan/designedkids', settle=4); await asyncio.sleep(3)
            await b.click_text('Run it again live'); t_click = time.time() - t0
            await b.wait_for('(location.hash.startsWith("#/scan/") && !location.hash.includes("designed")) || !!document.querySelector(".error")', 60)
            if not (await b.js('location.hash')).startswith('#/scan/') or 'designed' in await b.js('location.hash'):
                raise RuntimeError('Live run refused: ' + await b.js('document.querySelector(".error")?.textContent'))
            log['run_scan_id'] = (await b.js('location.hash')).split('/')[2]
            await b.wait_for('!!document.querySelector("article.report") || !!document.querySelector(".error")', 600, 1)
            t_done = time.time() - t0
            await asyncio.sleep(6)
            t_end = time.time() - t0
        log['run'] = await b.js(f'fetch("/api/scans/{log["run_scan_id"]}").then(r => r.json()).then(j => ({{status: j.status, '
                                f'assessment: j.report?.assessment?.status, findings: j.report?.hazards?.length, objects: j.report?.hazards?.map(h => h.object), '
                                f'seconds: j.report?.seconds ?? null, cost_usd: j.report?.cost_usd ?? null, app_version: j.report?.provenance?.app_version}}))')
        log['run']['click_to_report_seconds'] = round(t_done - t_click, 1)

        # 04 · one finding: photo, what we couldn't see, FEMA-linked steps, then a labelled Muse Image picture of a fix.
        async with Recorder(b, OUT / '04-raw.mp4'):
            await b.goto(f'{URL}/#/scan/{log["run_scan_id"]}', settle=4)
            await b.js('document.querySelector(".finding-row").click()'); await asyncio.sleep(5)
            await scroll_to(b, '.todo', block='center', wait=4)
            await b.js('(() => { const a = document.querySelector(".todo .src a"); if (a) { a.style.outline = "3px solid #d9480f"; a.style.outlineOffset = "4px"; } })()')
            await asyncio.sleep(4)
            t_ill = time.time()
            clicked = await b.js('(() => { const btn = [...document.querySelectorAll("button")].find(x => x.textContent.includes("Show what the fix could look like")); '
                                 'if (!btn) return false; btn.click(); scrollTo({top: 0, behavior: "smooth"}); return true })()')
            log['illustration'] = 'requested' if clicked else 'no source-linked finding offered a picture'
            if clicked:
                try:
                    await b.wait_for('[...document.querySelectorAll(".caption")].some(c => c.textContent.includes("AI-made picture"))', 120, 1)
                    log['illustration'] = 'shown'
                except Exception:
                    log['illustration'] = 'timed out or refused'
            log['illustration_wait_s'] = round(time.time() - t_ill, 1)
            await asyncio.sleep(8)

        # 05 · film again with the same file: SHA-256 guard, no verifier model call.
        hid = await b.js(f'fetch("/api/scans/{log["run_scan_id"]}").then(r => r.json()).then(j => j.report.hazards[0].id)')
        async with Recorder(b, OUT / '05-raw.mp4'):
            t1 = time.time()
            await b.goto(f'{URL}/#/verify/{log["run_scan_id"]}/{hid}', settle=4); await asyncio.sleep(4)
            doc = await b.send('DOM.getDocument', depth=-1, pierce=True)
            node = await b.send('DOM.querySelector', nodeId=doc['root']['nodeId'], selector='input[type=file]')
            await b.send('DOM.setFileInputFiles', files=[str(SAME_FILE)], nodeId=node['nodeId']); await asyncio.sleep(4)
            await b.click_text('Compare with the first video')
            await b.wait_for('[...document.querySelectorAll(".verdict")].some(v => v.textContent.includes("After your new video"))', 300, 1)
            t_verify = time.time() - t1
            await asyncio.sleep(5)
            await b.js('[...document.querySelectorAll(".finding-row")].find(r => r.textContent.includes("Can’t tell"))?.click()'); await asyncio.sleep(4)
            await scroll_to(b, '.verdict', block='center', wait=6)
        log['verify'] = {'hazard_id': hid, 'seconds_to_result': round(t_verify, 1), 'file': 'same bytes as the packaged example',
                         'result_text': await b.js('document.querySelector(".verdict")?.innerText')}

        # 06 · the test rooms: how they were made, then the answer key on the living room.
        async with Recorder(b, OUT / '06.mp4'):
            await b.goto((d / 'designed.html').as_uri(), settle=1); await asyncio.sleep(13)
            await b.goto(URL + '/#/scan/designedliving', settle=4)
            await b.js('[...document.querySelectorAll("details.fold summary")].find(s => s.textContent.includes("planted"))?.click()')
            await scroll_to(b, 'details.fold[open]', wait=12)

        # 07 · the real home's run replayed, then the end card.
        async with Recorder(b, OUT / '07.mp4'):
            await b.goto(URL + '/#/replay/real-home-istanbul', settle=2); await asyncio.sleep(12)
            await b.goto((d / 'end.html').as_uri(), settle=1); await asyncio.sleep(12)

    labelled(OUT / '01-raw.mp4', OUT / '01.mp4', "Real recording · Selçuk's home, Istanbul · personal photos blurred")
    raw = OUT / 'raw-run.mp4'
    pre = OUT / '03-pre.mp4'; cut(raw, pre, max(0, t_click - 3), t_click + 6)
    wait = (t_click + 6, t_done + 1); speed = max(1.0, (wait[1] - wait[0]) / 28.0)
    cut(raw, OUT / '03a.mp4', *wait, speed=speed, label=f'Live run · waiting shortened {speed:.1f}× · actual {t_done - t_click:.0f} s')
    cut(raw, OUT / '03b.mp4', t_done + 1, t_end)
    concat([pre, OUT / '03a.mp4', OUT / '03b.mp4'], OUT / '03.mp4')
    w = log.get('illustration_wait_s', 0); start_w = 17.0
    if w > 6:
        r4 = max(1.0, w / 3)
        cut(OUT / '04-raw.mp4', OUT / '04a.mp4', 0, start_w)
        cut(OUT / '04-raw.mp4', OUT / '04b.mp4', start_w, start_w + w, speed=r4, label=f'Muse Image drawing · shortened {r4:.0f}× · actual {w:.0f} s')
        cut(OUT / '04-raw.mp4', OUT / '04c.mp4', start_w + w, 9999)
        concat([OUT / '04a.mp4', OUT / '04b.mp4', OUT / '04c.mp4'], OUT / '04.mp4')
    else:
        cut(OUT / '04-raw.mp4', OUT / '04.mp4', 0, 9999)
    g = 'Same-file guard · SHA-256 match · no verifier model call'
    up = max(0.0, t_verify - 8)
    r5 = max(1.0, up / 4)
    cut(OUT / '05-raw.mp4', OUT / '05a.mp4', 0, 8, label=g)
    cut(OUT / '05-raw.mp4', OUT / '05b.mp4', 8, 8 + up, speed=r5, label=f'Upload and file check · shortened {r5:.0f}× · actual {up:.0f} s')
    cut(OUT / '05-raw.mp4', OUT / '05c.mp4', 8 + up, 9999, label=g)
    concat([OUT / '05a.mp4', OUT / '05b.mp4', OUT / '05c.mp4'], OUT / '05.mp4')
    log.update(t_click=round(t_click, 1), t_done=round(t_done, 1), wait_speedup=round(speed, 2), finished=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
    (OUT / 'recording-log.json').write_text(json.dumps(log, indent=2) + '\n'); print(json.dumps(log, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
