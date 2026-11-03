"""Fetch only Hypersim's public ai_048_004/cam_00 JPEG previews, then encode a clip.
Uses HTTP ranges; never downloads an entire multi-GB scene. Uses the backend httpx dependency and ffmpeg; run with backend/.venv/bin/python.
Attribution: Apple Inc., Hypersim, CC BY-SA 3.0; derived video shares that license.
"""
import io
import hashlib
import json
import subprocess
import httpx
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://docs-assets.developer.apple.com/ml-research/datasets/hypersim/v1/scenes/ai_048_004.zip'

class RangeFile(io.RawIOBase):
    BLOCK = 1024*1024
    def __init__(self, url=URL):
        self.url = url
        self.pos, self.cache = 0, {}
        self.client = httpx.Client(transport=httpx.HTTPTransport(local_address='0.0.0.0', retries=2), timeout=30)
        response = self.client.head(self.url)
        response.raise_for_status()
        self.size = int(response.headers['Content-Length'])
    def close(self):
        self.client.close()
        super().close()
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        self.pos = (0, self.pos, self.size)[whence]+offset
        return self.pos
    def read(self, n=-1):
        n = min(n if n >= 0 else self.size-self.pos, self.size-self.pos)
        output = bytearray()
        while len(output) < n:
            index, offset = divmod(self.pos, self.BLOCK)
            if index not in self.cache:
                start = index*self.BLOCK; end = min(start+self.BLOCK, self.size)-1
                with self.client.stream('GET', self.url, headers={'Range': f'bytes={start}-{end}'}) as response:
                    if response.status_code != 206: raise RuntimeError('Server does not support bounded range downloads')
                    chunks = bytearray()
                    for chunk in response.iter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > end-start+1: raise RuntimeError('Oversized range')
                    block = bytes(chunks)
                    if len(block) != end-start+1: raise RuntimeError('Incomplete range')
                if len(self.cache) >= 32: self.cache.pop(next(iter(self.cache)))
                self.cache[index] = block
            chunk = self.cache[index][offset:offset+n-len(output)]
            if not chunk: raise RuntimeError('Unexpected EOF')
            output.extend(chunk); self.pos += len(chunk)
        return bytes(output)

if __name__ == '__main__':
    out = ROOT/'eval/data/hypersim/ai_048_004_cam_00'
    (out/'frames').mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT/'examples/hypersim-source.json'
    manifest = json.loads(manifest_path.read_text())
    print('Verifying/downloading 100 licensed preview frames…', flush=True)
    with RangeFile() as remote, zipfile.ZipFile(remote) as archive:
        names = sorted(n for n in archive.namelist() if '/scene_cam_00_final_preview/' in n and n.endswith('.tonemap.jpg'))[:100]
        if len(names) != 100: raise RuntimeError('Expected 100 public preview frames')
        for i, name in enumerate(names):
            destination = out/'frames'/f'{i:04d}.jpg'
            if destination.is_file() and hashlib.sha256(destination.read_bytes()).hexdigest() == manifest['frame_sha256'][i]:
                if (i+1) % 10 == 0: print(f'{i+1}/100 frames verified', flush=True)
                continue
            data = archive.read(name)
            if hashlib.sha256(data).hexdigest() != manifest['frame_sha256'][i]:
                raise RuntimeError('Preview frame differs from the reviewed licensed source manifest')
            destination.write_bytes(data)
            if (i+1) % 10 == 0: print(f'{i+1}/100 frames verified', flush=True)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','6','-i',str(out/'frames/%04d.jpg'),
                    '-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'clip.mp4')], check=True)
    (out/'attribution.json').write_text(json.dumps({'source': URL, 'license': 'CC BY-SA 3.0', 'creator': 'Apple Inc.',
        'frames': names, 'clip_sha256': hashlib.sha256((out/'clip.mp4').read_bytes()).hexdigest(),
        'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(), 'modifications': 'Tonemapped previews encoded at 6 fps.'}, indent=2))
    print(out/'clip.mp4')
