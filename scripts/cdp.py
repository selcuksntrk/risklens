"""Minimal Chrome DevTools Protocol driver for visual QA and real screen recording.
Uses the locally installed Google Chrome (headless) and the `websockets` package; no browser download.
Recordings capture the actual rendered application; nothing is drawn or simulated by this module.
"""
import asyncio
import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import httpx
import websockets

CHROME = os.environ.get('CHROME', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')


class Browser:
    def __init__(self, width=1920, height=1080, scale=1, mobile=False, port=9333):
        self.width, self.height, self.scale, self.mobile, self.port = width, height, scale, mobile, port
        self.ws = None; self._id = 0; self._pending = {}; self._handlers = []
        self.profile = tempfile.mkdtemp(prefix='risklens-cdp-')

    async def __aenter__(self):
        self.proc = subprocess.Popen([CHROME, '--headless=new', f'--remote-debugging-port={self.port}',
                                      f'--user-data-dir={self.profile}', '--no-first-run', '--hide-scrollbars',
                                      '--force-color-profile=srgb', '--lang=en-US', '--mute-audio',
                                      f'--window-size={self.width},{self.height}', 'about:blank'],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                tabs = httpx.get(f'http://127.0.0.1:{self.port}/json').json()
                page = next(t for t in tabs if t['type'] == 'page'); break
            except Exception:
                await asyncio.sleep(.1)
        self.ws = await websockets.connect(page['webSocketDebuggerUrl'], max_size=None)
        self.reader = asyncio.create_task(self._read())
        await self.send('Page.enable'); await self.send('Runtime.enable')
        await self.send('Emulation.setDeviceMetricsOverride', width=self.width, height=self.height,
                        deviceScaleFactor=self.scale, mobile=self.mobile)
        if self.mobile:
            await self.send('Emulation.setTouchEmulationEnabled', enabled=True)
            await self.send('Emulation.setUserAgentOverride', userAgent=(
                'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 '
                '(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'))
        return self

    async def __aexit__(self, *exc):
        self.reader.cancel(); await self.ws.close(); self.proc.terminate(); self.proc.wait()
        shutil.rmtree(self.profile, ignore_errors=True)

    async def _read(self):
        async for raw in self.ws:
            msg = json.loads(raw)
            if 'id' in msg and msg['id'] in self._pending:
                self._pending.pop(msg['id']).set_result(msg)
            else:
                for h in list(self._handlers): h(msg)

    async def send(self, method, **params):
        self._id += 1; fut = asyncio.get_running_loop().create_future(); self._pending[self._id] = fut
        await self.ws.send(json.dumps({'id': self._id, 'method': method, 'params': params}))
        msg = await asyncio.wait_for(fut, 60)
        if 'error' in msg: raise RuntimeError(f"{method}: {msg['error']}")
        return msg.get('result', {})

    async def js(self, expression):
        r = await self.send('Runtime.evaluate', expression=expression, awaitPromise=True, returnByValue=True)
        if 'exceptionDetails' in r: raise RuntimeError(r['exceptionDetails'])
        return r['result'].get('value')

    async def goto(self, url, settle=1.5):
        await self.send('Page.navigate', url=url); await asyncio.sleep(settle)

    async def wait_for(self, expression, timeout=30, interval=.25):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if await self.js(expression): return True
            await asyncio.sleep(interval)
        raise TimeoutError(expression)

    async def screenshot(self, path, full_page=False):
        params = {'format': 'png'}
        if full_page:
            h = await self.js('document.documentElement.scrollHeight')
            params.update(captureBeyondViewport=True, clip={'x': 0, 'y': 0, 'width': self.width, 'height': h, 'scale': 1})
        data = await self.send('Page.captureScreenshot', **params)
        Path(path).write_bytes(base64.b64decode(data['data']))

    async def click_text(self, text, selector='button, a, [role=tab], summary'):
        ok = await self.js(f'''(() => {{ const el = [...document.querySelectorAll({json.dumps(selector)})]
            .find(e => e.textContent.trim().includes({json.dumps(text)}) && e.offsetParent !== null);
            if (!el) return false; el.scrollIntoView({{block: 'center', behavior: 'smooth'}});
            setTimeout(() => el.click(), 600); return true; }})()''')
        if not ok: raise LookupError(text)
        await asyncio.sleep(.9)

    async def smooth_scroll(self, dy, seconds=2.0, steps=40):
        for _ in range(steps):
            await self.js(f'window.scrollBy(0, {dy/steps})'); await asyncio.sleep(seconds/steps)


class Recorder:
    """Records Page.screencastFrame output with its real timestamps, then encodes a constant-30fps MP4."""
    def __init__(self, browser, out):
        self.b, self.out = browser, Path(out); self.frames = []; self.dir = Path(tempfile.mkdtemp(prefix='rec-'))

    def _on(self, msg):
        if msg.get('method') != 'Page.screencastFrame': return
        p = msg['params']; path = self.dir / f'{len(self.frames):06d}.jpg'
        path.write_bytes(base64.b64decode(p['data'])); self.frames.append((time.time(), path))  # receipt time: same clock as `ended`
        asyncio.ensure_future(self.b.send('Page.screencastFrameAck', sessionId=p['sessionId']))

    async def __aenter__(self):
        self.b._handlers.append(self._on)
        await self.b.send('Page.startScreencast', format='jpeg', quality=92,
                          maxWidth=round(self.b.width * self.b.scale), maxHeight=round(self.b.height * self.b.scale), everyNthFrame=1)
        self.started = time.time(); return self

    async def __aexit__(self, *exc):
        await asyncio.sleep(.3); await self.b.send('Page.stopScreencast'); self.b._handlers.remove(self._on)
        ended = time.time()
        if not self.frames: raise RuntimeError('no frames captured')
        lines = []
        for i, (ts, path) in enumerate(self.frames):
            nxt = self.frames[i + 1][0] if i + 1 < len(self.frames) else ended
            lines += [f"file '{path}'", f'duration {max(nxt - ts, 0.001):.4f}']  # real intervals; fps=30 resamples
        lines.append(f"file '{self.frames[-1][1]}'")
        listing = self.dir / 'list.txt'; listing.write_text('\n'.join(lines) + '\n')
        self.out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(listing),
                        '-vf', f'scale={round(self.b.width*self.b.scale)}:{round(self.b.height*self.b.scale)}:flags=lanczos,fps=30,format=yuv420p',
                        '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-movflags', '+faststart', str(self.out)], check=True)
        shutil.rmtree(self.dir, ignore_errors=True)
