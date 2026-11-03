"""Record the demo's screen footage from the REAL deployed application (headless Chrome, 1920x1080).

Spends model budget: one new sample run (~$0.2) and one same-file comparison (hash guard, $0 model calls).
Outputs (git-ignored) under docs/submission/private/footage/:
  raw-run.mp4         uncut recording from homepage through the completed new sample run
  01.mp4 … 07.mp4     segments matching NARRATION.md; shortened waits carry a visible label
  cards/*.html        evaluation / model-role / end cards, generated from eval/synthetic-results.json
  recording-log.json  timings, scan IDs, release and outcomes for the handoff record
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
OUT = ROOT / 'docs/submission/private/footage'
SAMPLE = ROOT / 'docs/submission/private/phone-sample.mp4'
FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
URL = (sys.argv[1] if len(sys.argv) > 1 else 'https://selcuksntrk--risklens-web.us-east.modal.run').rstrip('/')

CARD_CSS = '''*{box-sizing:border-box}body{margin:0;background:#0f1720;color:#e8eef4;font:22px/1.45 -apple-system,"Helvetica Neue",Arial,sans-serif;
height:100vh;display:flex;align-items:center;justify-content:center}main{width:1120px}h1{font-size:44px;margin:0 0 6px}h2{font-size:30px;margin:0 0 18px}
.muted{color:#8d9aa8}.tag{display:inline-block;color:#8d9aa8;font-size:17px;letter-spacing:.04em;font-weight:650;margin-bottom:10px}
table{width:100%;border-collapse:collapse;margin:12px 0 18px}th,td{text-align:right;padding:9px 12px;border-bottom:1px solid #2a3846}th:first-child,td:first-child{text-align:left}
th{color:#8d9aa8;font-weight:600;font-size:18px}.flow{display:flex;gap:14px;align-items:stretch;margin:18px 0}.box{flex:1;background:#18232f;border:1px solid #2a3846;border-radius:14px;padding:16px}
.box b{display:block;color:#f5b83d;font-size:20px;margin-bottom:6px}.arrow{align-self:center;color:#8d9aa8;font-size:28px}.note{font-size:18px;color:#8d9aa8;margin-top:14px}
a{color:#f5b83d}.big{font-size:28px;margin:8px 0}'''


def cards():
    r = json.loads((ROOT / 'eval/synthetic-results.json').read_text())
    c = r['comparisons']; d = OUT / 'cards'; d.mkdir(parents=True, exist_ok=True)
    rows = ''.join(f"<tr><td>{'Spark only' if k == 'spark_only' else 'Spark + SAM (full)'}</td><td>{v['returned_reports']}/{v['attempts']}</td>"
                   f"<td>{v['reported_findings']}</td><td>{v['tracked_findings']}</td><td>{v['seconds_successful']['median']:.0f} s</td>"
                   f"<td>${v['cost_usd_successful']['median']:.3f}</td></tr>" for k, v in c.items())
    ctrl = ''.join(f"<tr><td>{n['case']}</td><td style='text-align:left'>{n['description'].split(';')[0]}</td><td>{n['confirmed']}/{n['checked_findings']}</td><td>{n['model_called_findings']}</td></tr>"
                   for n in r['negative_controls'])
    reps = ' · '.join(f"{x['findings']} findings, {x['seconds']:.0f} s" for x in r['demo_repetitions'])
    (d / 'evaluation.html').write_text(f'''<!doctype html><meta charset=utf-8><style>{CARD_CSS}</style><main>
<span class=tag>WHAT WE MEASURED · SYNTHETIC DEVELOPMENT REGRESSION</span><h2>Five previously used Hypersim scenes, same inputs, both pipelines</h2>
<table><tr><th>Variant</th><th>Reports</th><th>Findings</th><th>Tracked</th><th>Median time</th><th>Median cost</th></tr>{rows}</table>
<table><tr><th>Control</th><th style="text-align:left">Input</th><th>Confirmed</th><th>Verifier calls</th></tr>{ctrl}</table>
<div class=muted>Demo scene repeated 3×: {reps}. Failed attempts: {r['failed_attempts']}. Recorded total ${r['recorded_total_usd']:.2f}.</div>
<div class=note>More findings ≠ higher accuracy. Precision/recall and positive physical-change verification: <b>not measured</b>. Human review pending.</div></main>''')
    (d / 'models.html').write_text(f'''<!doctype html><meta charset=utf-8><style>{CARD_CSS}</style><main>
<span class=tag>HOW THE META MODELS WORK TOGETHER</span><h2>Each model has one job; deterministic checks sit between them</h2>
<div class=flow><div class=box><b>Muse Spark 1.3</b>Planner: picks objects worth tracking from sampled frames</div><div class=arrow>→</div>
<div class=box><b>SAM 3.1</b>Tracks those objects through the clip; exact-frame boxes</div><div class=arrow>→</div>
<div class=box><b>Muse Spark 1.3</b>Surveyor: reviews marked frames; observed vs. needs checking</div><div class=arrow>→</div>
<div class=box><b>Spark + FEMA E-74</b>Suggestions linked to sections actually returned</div></div>
<div class=flow><div class=box><b>Re-filming guard</b>SHA-256 same-file check before any model call · then SAM + Spark with same-object, relevant-change and confidence requirements</div></div>
<div class=note>Optional, implemented but not needed for this demo: Muse Voice Transcribe (narration), Muse Image (labelled illustrations, never evidence).</div></main>''')
    (d / 'end.html').write_text(f'''<!doctype html><meta charset=utf-8><style>{CARD_CSS}</style><main>
<h1>RiskLens</h1><div class=muted style="font-size:26px;margin-bottom:26px">Find the evidence. Understand the uncertainty. Decide what needs a closer look.</div>
<div class=big>Try it: <a>{URL.replace('https://', '')}</a></div><div class=big>Code: <a>github.com/selcuksntrk/risklens</a></div>
<div class=note style="margin-top:30px">Built during the Meta Global AI Developer Hackathon · Indie Developer · Build for Your World.<br>
Visual screening prototype, not a building inspection or safety certificate. Demo scenes are synthetic: Hypersim © Apple Inc. / Roberts et al., ICCV 2021,
CC BY-SA 3.0, frames assembled into video and marked by RiskLens. No music.</div></main>''')
    return d


def label_png(text, path):
    img = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0)); draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, 34); w = draw.textlength(text, font=font)
    x0, y0 = 1920 - w - 90, 1080 - 110
    draw.rounded_rectangle((x0, y0, x0 + w + 48, y0 + 64), 18, fill=(0, 0, 0, 200))
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


def concat(parts, dst):
    lst = OUT / (dst.stem + '-concat.txt'); lst.write_text(''.join(f"file '{p}'\n" for p in parts))
    ff('-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', dst)


async def main():
    OUT.mkdir(parents=True, exist_ok=True); d = cards(); log = {'url': URL, 'started': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    async with Browser(width=1097, height=617, scale=1.75, port=9334) as b:
        await b.goto(URL + '/#/', settle=3)
        log['release'] = await b.js('fetch("/api/health").then(r => r.json()).then(j => j.version)')

        # 01 · completed example: finding + evidence first, synthetic label visible.
        async with Recorder(b, OUT / '01.mp4'):
            await b.goto(URL + '/#/scan/hypersimbedroom', settle=4); await asyncio.sleep(3)
            await b.js('document.querySelector(".hazards li").scrollIntoView({behavior:"smooth", block:"start"})'); await asyncio.sleep(6)
            await b.smooth_scroll(260, 3); await asyncio.sleep(7)

        # 02/03 · homepage → genuinely new sample run → completed report (uncut raw).
        rec = Recorder(b, OUT / 'raw-run.mp4')
        async with rec:
            t0 = time.time()
            await b.goto(URL + '/#/', settle=3); await asyncio.sleep(5)   # own-video actions first
            await b.js('document.getElementById("sample-title").scrollIntoView({behavior: "smooth", block: "start"})'); await asyncio.sleep(5)
            await b.click_text('Run the sample analysis'); t_click = time.time() - t0
            await b.wait_for('(location.hash.startsWith("#/scan/") && location.hash !== "#/scan/hypersimbedroom") || !!document.querySelector(".sample .error")', 60)
            if not (await b.js('location.hash')).startswith('#/scan/'):
                raise RuntimeError('Sample run refused: ' + await b.js('document.querySelector(".sample .error").textContent'))
            log['run_scan_id'] = (await b.js('location.hash')).split('/')[2]
            await b.wait_for('!!document.querySelector("article.report") || !!document.querySelector(".error")', 600, 1)
            t_done = time.time() - t0
            await asyncio.sleep(3); await b.js('document.querySelector(".hazards li")?.scrollIntoView({behavior:"smooth", block:"start"})')
            await asyncio.sleep(5); await b.smooth_scroll(300, 3); await asyncio.sleep(4)
            t_end = time.time() - t0
        log['run'] = await b.js(f'fetch("/api/scans/{log["run_scan_id"]}").then(r => r.json()).then(j => ({{status: j.status, '
                                f'assessment: j.report?.assessment?.status, findings: j.report?.hazards?.length, '
                                f'seconds: j.report?.seconds ?? null, cost_usd: j.report?.cost_usd ?? null, app_version: j.report?.provenance?.app_version}}))')
        log['run']['click_to_report_seconds'] = round(t_done - t_click, 1)

        # 04 · source-linked suggestions on the completed example (stored citation; the FEMA PDF is not opened headless).
        async with Recorder(b, OUT / '04.mp4'):
            await b.goto(URL + '/#/scan/hypersimbedroom', settle=4)
            await b.js('document.querySelector(".hazards li .fix, .hazards li section, .hazards li ol")?.scrollIntoView({behavior:"smooth", block:"center"})')
            await asyncio.sleep(10)
            await b.js('(() => { const a = document.querySelector(".hazards li a[href*=fema], .hazards li a[href*=atcouncil]"); '
                       'if (a) { a.style.outline = "3px solid #f5b83d"; a.style.outlineOffset = "4px"; } })()')
            await asyncio.sleep(10); await b.smooth_scroll(200, 3); await asyncio.sleep(10)

        # 05 · same-file comparison on the new private scan: hash guard, no verifier model call.
        hid = await b.js(f'fetch("/api/scans/{log["run_scan_id"]}").then(r => r.json()).then(j => j.report.hazards[0].id)')
        async with Recorder(b, OUT / '05-raw.mp4'):
            t1 = time.time()
            await b.goto(f'{URL}/#/verify/{log["run_scan_id"]}/{hid}', settle=4); await asyncio.sleep(4)
            doc = await b.send('DOM.getDocument', depth=-1, pierce=True)
            node = await b.send('DOM.querySelector', nodeId=doc['root']['nodeId'], selector='input[type=file]')
            await b.send('DOM.setFileInputFiles', files=[str(SAMPLE)], nodeId=node['nodeId']); await asyncio.sleep(4)
            await b.click_text('Use video')
            await b.wait_for('location.hash.includes("/v/") && !!document.querySelector("article.report section h3")', 300, 1)
            await b.wait_for('[...document.querySelectorAll("article.report section h3")].some(h => h.textContent.includes("Re-filming results"))', 300, 1)
            t_verify = time.time() - t1
            await b.js('scrollTo({top: 0, behavior: "smooth"})'); await asyncio.sleep(5)
            await b.js('document.querySelector(".hazards li")?.scrollIntoView({behavior:"smooth", block:"start"})'); await asyncio.sleep(6)
        log['verify'] = {'hazard_id': hid, 'seconds_to_result': round(t_verify, 1), 'hash': 'same bytes as the packaged sample',
                         'result_text': await b.js('[...document.querySelectorAll("article.report section")].find(s => s.textContent.includes("Re-filming results"))?.innerText')}

        # 06 / 07 · measured results, model roles, close.
        async with Recorder(b, OUT / '06.mp4'):
            await b.goto((d / 'evaluation.html').as_uri(), settle=1); await asyncio.sleep(14)
            await b.goto((d / 'models.html').as_uri(), settle=1); await asyncio.sleep(14)
        async with Recorder(b, OUT / '07.mp4'):
            await b.goto(URL + '/#/scan/hypersimbedroom', settle=4); await asyncio.sleep(8)
            await b.goto((d / 'end.html').as_uri(), settle=1); await asyncio.sleep(16)

    raw = OUT / 'raw-run.mp4'
    cut(raw, OUT / '02.mp4', 0, t_click + 10)
    wait = (t_click + 10, t_done + 1); target = 30.0; speed = max(1.0, (wait[1] - wait[0]) / target)
    cut(raw, OUT / '03a.mp4', *wait, speed=speed, label=f'Recorded run · waiting shortened {speed:.1f}× · actual {t_done - t_click:.0f} s')
    cut(raw, OUT / '03b.mp4', t_done + 1, t_end)
    concat([OUT / '03a.mp4', OUT / '03b.mp4'], OUT / '03.mp4')
    v_speed = max(1.0, t_verify / 14)
    cut(OUT / '05-raw.mp4', OUT / '05.mp4', 0, 999, speed=1.0, label='Same-file guard · SHA-256 match · no verifier model call')
    log.update(t_click=round(t_click, 1), t_done=round(t_done, 1), wait_speedup=round(speed, 2), verify_speed_hint=round(v_speed, 2),
               finished=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
    (OUT / 'recording-log.json').write_text(json.dumps(log, indent=2) + '\n'); print(json.dumps(log, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
