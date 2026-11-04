"""Record the final demo's app footage from the REAL deployed application in a phone viewport (390x844), on the author's real home.
Spends model budget: one live run of the real-home example (~$0.3), one Muse Image picture, one same-file comparison (no verifier call).
Outputs (git-ignored) under docs/submission/private/footage-v5/, with recording-log.json.
Usage: backend/.venv/bin/python scripts/record_phone.py [URL]
"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdp import Browser, Recorder  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/submission/private/footage-v5'
SAME_FILE = ROOT / 'examples/generated/realhomeistanbul/source.mp4'
URL = (sys.argv[1] if len(sys.argv) > 1 else 'https://selcuksntrk--risklens-web.us-east.modal.run').rstrip('/')
SCROLL = 'document.querySelector({sel})?.scrollIntoView({{behavior:"smooth", block:"{block}"}})'


async def scroll_to(b, selector, block='start', wait=4.0):
    await b.js(SCROLL.format(sel=json.dumps(selector), block=block)); await asyncio.sleep(wait)


async def open_finding(b):
    """Open the wardrobe-with-suitcases finding when this run has one, else the first finding."""
    return await b.js('(() => { const rows = [...document.querySelectorAll(".finding-row")]; '
                      'const row = rows.find(r => /wardrobe/i.test(r.textContent) && /suitcase/i.test(r.textContent)) '
                      '|| rows.find(r => /wardrobe/i.test(r.textContent)) || rows[0]; row.click(); return row.textContent })()')


async def main():
    OUT.mkdir(parents=True, exist_ok=True); log = {'url': URL, 'started': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    def save(): (OUT / 'recording-log.json').write_text(json.dumps(log, indent=2) + '\n')
    async with Browser(width=390, height=844, scale=2, mobile=True, port=9335) as b:
        await b.goto(URL + '/#/', settle=4)
        log['release'] = await b.js('fetch("/api/health").then(r => r.json()).then(j => j.version)')

        async with Recorder(b, OUT / 'home.mp4'):
            await b.goto(URL + '/#/', settle=2); await asyncio.sleep(6)
            await scroll_to(b, '#examples', wait=6)

        rec = Recorder(b, OUT / 'run.mp4')
        async with rec:
            t0 = time.time()
            await b.goto(URL + '/#/scan/realhomeistanbul', settle=4); await asyncio.sleep(2)
            await b.click_text('Run it again live'); log['t_click'] = round(time.time() - t0, 1)
            await b.wait_for('(location.hash.startsWith("#/scan/") && !location.hash.includes("realhome")) || !!document.querySelector(".error")', 90)
            if 'realhome' in await b.js('location.hash'):
                raise RuntimeError('Live run refused: ' + str(await b.js('document.querySelector(".error")?.textContent')))
            sid = log['run_scan_id'] = (await b.js('location.hash')).split('/')[2]; save()
            await b.wait_for('!!document.querySelector("article.report") || !!document.querySelector(".error")', 600, 1)
            log['t_done'] = round(time.time() - t0, 1)
            await asyncio.sleep(6)
        log['run'] = await b.js(f'fetch("/api/scans/{sid}").then(r => r.json()).then(j => ({{status: j.status, assessment: j.report?.assessment?.status, '
                                f'findings: j.report?.hazards?.map(h => [h.id, h.object, h.severity, h.relation, h.evidence_status]), plan: j.report?.plan?.concepts?.map(c => c.concept), '
                                f'seconds: j.report?.seconds ?? null, cost_usd: j.report?.cost_usd ?? null, app_version: j.report?.provenance?.app_version}}))'); save()

        async with Recorder(b, OUT / 'finding.mp4'):
            t1 = time.time()
            await b.goto(f'{URL}/#/scan/{sid}', settle=3); await asyncio.sleep(3)
            log['opened'] = await open_finding(b); await asyncio.sleep(5)
            log['t_unknown'] = round(time.time() - t1, 1); await scroll_to(b, '.unknown', block='center', wait=5)
            log['t_todo'] = round(time.time() - t1, 1); await scroll_to(b, '.todo', block='start', wait=6)
            log['t_fix_click'] = round(time.time() - t1, 1)
            clicked = await b.js('(() => { const btn = [...document.querySelectorAll("button")].find(x => x.textContent.includes("Show what the fix could look like")); '
                                 'if (!btn) return false; btn.click(); scrollTo({top: 0, behavior: "smooth"}); return true })()')
            log['illustration'] = 'requested' if clicked else 'not offered'
            if clicked:
                try:
                    await b.wait_for('[...document.querySelectorAll(".caption")].some(c => c.textContent.includes("AI-made picture"))', 120, 1)
                    log['illustration'] = 'shown'
                except Exception:
                    log['illustration'] = 'timed out or refused'
            log['t_fix_done'] = round(time.time() - t1, 1)
            await asyncio.sleep(8)
        save()

        hid = await b.js(f'fetch("/api/scans/{sid}").then(r => r.json()).then(j => {{ const h = j.report.hazards; '
                         f'return (h.find(x => /wardrobe/i.test(x.object) && /suitcase/i.test(x.object)) || h.find(x => /wardrobe/i.test(x.object)) || h[0]).id }})')
        async with Recorder(b, OUT / 'verify.mp4'):
            t2 = time.time()
            await b.goto(f'{URL}/#/verify/{sid}/{hid}', settle=3); await asyncio.sleep(3)
            doc = await b.send('DOM.getDocument', depth=-1, pierce=True)
            node = await b.send('DOM.querySelector', nodeId=doc['root']['nodeId'], selector='input[type=file]')
            await b.send('DOM.setFileInputFiles', files=[str(SAME_FILE)], nodeId=node['nodeId']); await asyncio.sleep(3)
            await b.click_text('Compare with the first video')
            log['t_compare_click'] = round(time.time() - t2, 1)
            await b.wait_for('[...document.querySelectorAll(".verdict")].some(v => v.textContent.includes("After your new video"))', 300, 1)
            log['t_verdict'] = round(time.time() - t2, 1)
            await asyncio.sleep(3)
            await b.js('[...document.querySelectorAll(".finding-row")].find(r => r.textContent.includes("Can’t tell"))?.click()'); await asyncio.sleep(3)
            log['t_cant_tell'] = round(time.time() - t2, 1)
            await scroll_to(b, '.verdict', block='center', wait=6)
        log['verify'] = {'hazard_id': hid, 'result_text': await b.js('document.querySelector(".verdict")?.innerText')}; save()

        for name, scan in (('key-living', 'designedliving'), ('key-kitchen', 'designedkitchen')):
            async with Recorder(b, OUT / f'{name}.mp4'):
                await b.goto(f'{URL}/#/scan/{scan}', settle=3)
                await b.js('[...document.querySelectorAll("details.fold summary")].find(s => s.textContent.includes("planted"))?.click()')
                await scroll_to(b, 'details.fold[open]', wait=7)
    log['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S%z'); save(); print(json.dumps(log, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
