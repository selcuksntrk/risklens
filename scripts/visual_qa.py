"""Desktop and phone-size visual QA of the deployed app (headless Chrome emulation, no model calls).
Writes screenshots plus a machine-readable overflow/legibility check. Emulation is not a physical-phone test.
Usage: backend/.venv/bin/python scripts/visual_qa.py URL OUTPUT_DIR
"""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdp import Browser  # noqa: E402

PROBE = '''(() => {
  const vw = document.documentElement.clientWidth;
  const wide = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect();
    return r.width > 0 && (r.right > vw + 1 || r.left < -1) && getComputedStyle(e).position !== 'fixed'; })
    .slice(0, 8).map(e => e.tagName + '.' + e.className + ' ' + e.textContent.trim().slice(0, 40));
  const small = [...document.querySelectorAll('p, span, small, a, button, li, dd, dt, label')].filter(e =>
    e.offsetParent && e.textContent.trim() && parseFloat(getComputedStyle(e).fontSize) < 12)
    .slice(0, 8).map(e => getComputedStyle(e).fontSize + ' ' + e.textContent.trim().slice(0, 40));
  const tiny = [...document.querySelectorAll('button, a, summary, input, select')].filter(e => { const r = e.getBoundingClientRect();
    return e.offsetParent && r.width > 0 && (r.height < 24 || r.width < 24); })
    .slice(0, 8).map(e => Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height) + ' ' + e.textContent.trim().slice(0, 30));
  return {scrollWidth: document.documentElement.scrollWidth, viewport: vw, overflowing: wide, small_text: small, small_targets: tiny};
})()'''

PAGES = [('home', '#/'), ('report', '#/scan/realhomeistanbul'), ('designed', '#/scan/designedliving'), ('replay', '#/replay/real-home-istanbul'), ('capture', '#/capture')]
VIEWPORTS = [('desktop', dict(width=1440, height=900, scale=1)),
             ('phone-390', dict(width=390, height=844, scale=3, mobile=True)),
             ('phone-360', dict(width=360, height=740, scale=3, mobile=True))]


async def main(url, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True); results = {}
    schemes = os.environ.get('QA_SCHEMES', 'dark,light').split(',')
    for (name, vp), scheme in [(v, sc) for v in VIEWPORTS for sc in schemes]:
        name = f'{name}-{scheme}'
        async with Browser(**vp) as b:
            await b.send('Emulation.setEmulatedMedia', features=[{'name': 'prefers-color-scheme', 'value': scheme}])
            for page, route in PAGES:
                await b.goto(url.rstrip('/') + '/' + route, settle=3)
                await b.js('document.querySelectorAll("details").forEach(d => d.open = true)')
                await asyncio.sleep(.5)
                results[f'{name}/{page}'] = await b.js(PROBE)
                await b.screenshot(out / f'{name}-{page}.png', full_page=True)
    (out / 'visual-qa.json').write_text(json.dumps(results, indent=2) + '\n')
    for k, v in results.items():
        print(k, 'scrollWidth', v['scrollWidth'], '/', v['viewport'], '| overflow', len(v['overflowing']),
              '| small text', len(v['small_text']), '| small targets', len(v['small_targets']))


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1], sys.argv[2]))
