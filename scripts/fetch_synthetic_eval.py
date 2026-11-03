"""Fetch the five frozen Hypersim camera sequences for reproducing regression.
Uses the public source manifest, bounded range downloads, and original frame hashes.
No private workspace/spike repository is needed. ffmpeg bytes can differ by version.
Usage: backend/.venv/bin/python scripts/fetch_synthetic_eval.py
"""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
from fetch_example import RangeFile

ROOT=Path(__file__).resolve().parents[1]


def fetch(destination):
    source=json.loads((ROOT/'eval/synthetic-frame-manifest.json').read_text())
    for scene in source['scenes']:
        folder=destination/f"{scene['scene']}_{scene['camera']}"
        frames=folder/'frames';frames.mkdir(parents=True,exist_ok=True)
        wanted=scene['frame_sha256']
        missing=[i for i,h in enumerate(wanted) if not (frames/f'{i:04d}.jpg').is_file()
                 or hashlib.sha256((frames/f'{i:04d}.jpg').read_bytes()).hexdigest()!=h]
        if missing:
            with RangeFile(scene['source_url']) as remote, zipfile.ZipFile(remote) as archive:
                prefix=f"{scene['scene']}/images/scene_{scene['camera']}_final_preview/"
                names=sorted(n for n in archive.namelist() if n.startswith(prefix) and n.endswith('.tonemap.jpg'))
                if len(names)!=len(wanted): raise ValueError('Source frame count changed')
                for i in missing:
                    data=archive.read(names[i])
                    if hashlib.sha256(data).hexdigest()!=wanted[i]: raise ValueError('Source frame hash changed')
                    (frames/f'{i:04d}.jpg').write_bytes(data)
        clip=folder/'clip.mp4'
        if not clip.exists():
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-framerate','6','-i',str(frames/'%04d.jpg'),
                '-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(clip)],check=True)
        # Legacy name is retained for the preparation interface; this is NOT hazard ground truth.
        (folder/'gt.json').write_text(json.dumps({'scene':scene['scene'],'camera':scene['camera'],
            'license':'Hypersim, CC BY-SA 3.0 (Apple Inc.)','frames':len(wanted),'fps':6,
            'note':'Source metadata only; no hazard ground truth is asserted.'},indent=2)+'\n')
        print(f"Verified {scene['scene']}/{scene['camera']}: {len(wanted)} original frames",flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--destination',type=Path,default=ROOT/'eval/data/regression')
    args=p.parse_args();fetch(args.destination)
