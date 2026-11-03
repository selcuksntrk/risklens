"""Record the "own video" path from the REAL deployed app: home → Upload a video → preview → analysis → report.

Spends model budget for one scan (~$0.3). The video must already be privacy-reviewed (people, photos,
documents, screens blurred). The scan is private to this headless browser session; nothing is published.
Outputs (git-ignored) under docs/submission/private/footage/real/:
  raw.mp4                         uncut recording
  01.mp4 02.mp4 03.mp4 04.mp4     hook (finding) · upload · shortened run + report · source-linked steps
  07.mp4                          sample report + end card (no model calls)
  recording-log.json
Usage: backend/.venv/bin/python scripts/record_own_video.py VIDEO "CONTEXT" "FOCUS_WORD" [URL]
FOCUS_WORD picks the finding to feature (e.g. "suitcase"); the first finding is used if none matches.
"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdp import Browser, Recorder  # noqa: E402
import record_demo as rd  # noqa: E402

VIDEO, CONTEXT, FOCUS = Path(sys.argv[1]).resolve(), sys.argv[2], sys.argv[3].lower()
URL = (sys.argv[4] if len(sys.argv) > 4 else 'https://selcuksntrk--risklens-web.us-east.modal.run').rstrip('/')
OUT = rd.OUT / 'real'
REAL_LABEL = "Real recording · Selçuk's home, Istanbul · personal photos blurred"

FOCUS_JS = '''(() => { const cards = [...document.querySelectorAll(".hazards > li")];
  return cards.findIndex(c => c.textContent.toLowerCase().includes(%s)); })()''' % json.dumps(FOCUS)


async def scroll_to_card(b, index, block='start'):
    await b.js(f'document.querySelectorAll(".hazards > li")[{max(index, 0)}].scrollIntoView({{behavior:"smooth", block:"{block}"}})')


async def main():
    OUT.mkdir(parents=True, exist_ok=True); rd.OUT = OUT; d = rd.cards()
    log = {'url': URL, 'video': VIDEO.name, 'started': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    async with Browser(width=1097, height=617, scale=1.75, port=9335) as b:
        await b.goto(URL + '/#/', settle=3)
        log['release'] = await b.js('fetch("/api/health").then(r => r.json()).then(j => j.version)')
        async with Recorder(b, OUT / 'raw.mp4'):
            t0 = time.time()
            await b.goto(URL + '/#/', settle=2); await b.js('scrollTo(0, 0)'); await asyncio.sleep(6)
            doc = await b.send('DOM.getDocument', depth=-1, pierce=True)
            node = await b.send('DOM.querySelector', nodeId=doc['root']['nodeId'], selector='.task-panel input[type=file]')
            await b.send('DOM.setFileInputFiles', files=[str(VIDEO)], nodeId=node['nodeId'])
            await b.wait_for('location.hash === "#/capture" && !!document.querySelector("textarea")', 20); await asyncio.sleep(3)
            await b.js('document.querySelector("textarea").focus()')
            await b.send('Input.insertText', text=CONTEXT); await asyncio.sleep(3)
            await b.click_text('Use video'); t_click = time.time() - t0
            await b.wait_for('location.hash.startsWith("#/scan/")', 120)
            log['scan_id'] = (await b.js('location.hash')).split('/')[2]
            await b.wait_for('!!document.querySelector("article.report") || !!document.querySelector(".error")', 600, 1)
            t_done = time.time() - t0
            await asyncio.sleep(3)
            idx = await b.js(FOCUS_JS); log['focus_index'] = idx
            await scroll_to_card(b, idx); await asyncio.sleep(16)                 # evidence + observation
            t_sources = time.time() - t0
            await b.js(f'document.querySelectorAll(".hazards > li")[{max(idx, 0)}].querySelector(".fix, .notice")?.scrollIntoView({{behavior:"smooth", block:"center"}})')
            await asyncio.sleep(18); await b.smooth_scroll(160, 2); await asyncio.sleep(12)
            t_end = time.time() - t0
        log['report'] = await b.js(f'fetch("/api/scans/{log["scan_id"]}").then(r => r.json()).then(j => ({{status: j.status, '
                                   f'assessment: j.report?.assessment?.status, findings: j.report?.hazards?.map(h => [h.severity, h.evidence_status, h.object]), '
                                   f'seconds: j.report?.seconds, cost_usd: j.report?.cost_usd?.total, keyframes: j.report?.provenance?.keyframes?.length, '
                                   f'app_version: j.report?.provenance?.app_version}}))')
        # 07 · close: sample path stays available + end card (no model calls).
        async with Recorder(b, OUT / '07.mp4'):
            await b.goto(URL + '/#/', settle=2); await b.js('document.getElementById("sample-title").scrollIntoView({block: "start"})')
            await asyncio.sleep(7)
            await b.goto((d / 'end.html').as_uri(), settle=1); await asyncio.sleep(16)

    raw = OUT / 'raw.mp4'
    rd.cut(raw, OUT / '01.mp4', t_done + 3, t_sources + 0.5, label=REAL_LABEL)          # hook: the featured finding
    rd.cut(raw, OUT / '02.mp4', 0, t_click + 8, label=REAL_LABEL)                       # home → upload → context → send
    wait = (t_click + 8, t_done + 1); speed = max(1.0, (wait[1] - wait[0]) / 30)
    rd.cut(raw, OUT / '03a.mp4', *wait, speed=speed, label=f'Recorded run · waiting shortened {speed:.1f}× · actual {t_done - t_click:.0f} s')
    rd.cut(raw, OUT / '03b.mp4', t_done + 1, t_sources, label=REAL_LABEL)
    rd.concat([OUT / '03a.mp4', OUT / '03b.mp4'], OUT / '03.mp4')
    rd.cut(raw, OUT / '04.mp4', t_sources, t_end, label=REAL_LABEL)                       # source-linked next steps
    log.update(t_click=round(t_click, 1), t_done=round(t_done, 1), click_to_report_seconds=round(t_done - t_click, 1),
               wait_speedup=round(speed, 2), finished=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
    (OUT / 'recording-log.json').write_text(json.dumps(log, indent=2) + '\n'); print(json.dumps(log, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
