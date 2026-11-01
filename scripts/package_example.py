"""Publish ONLY a verified Hypersim-derived report into the explicit example allowlist.
No personal scan can be packaged merely by passing its ID: the original source must match the licensed clip.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SHA256 = '7c8b51a659cb7614b5a05156d5e6569d013c2d3abd102469e7c0932ddbaaf54c'

def package(scan: Path, video: Path):
    report = json.loads((scan/'report.json').read_text())
    digest = hashlib.sha256(video.read_bytes()).hexdigest()
    approved = digest == EXPECTED_SHA256
    attribution_file = video.parent/'attribution.json'
    if not approved and attribution_file.is_file():
        source = json.loads(attribution_file.read_text())
        manifest_path = ROOT/'examples/hypersim-source.json'
        approved = (source.get('clip_sha256') == digest and source.get('manifest_sha256') == hashlib.sha256(manifest_path.read_bytes()).hexdigest())
        manifest = json.loads(manifest_path.read_text())
        approved = approved and all((video.parent/'frames'/f'{i:04d}.jpg').is_file() and
            hashlib.sha256((video.parent/'frames'/f'{i:04d}.jpg').read_bytes()).hexdigest() == h
            for i, h in enumerate(manifest['frame_sha256']))
    if not approved or report['provenance']['source_sha256'] != digest:
        raise SystemExit('Source is not the approved Hypersim ai_048_004/cam_00 clip. Nothing published.')
    if report.get('schema_version') != 2:
        raise SystemExit('Run the current pipeline first; legacy results are not upgraded or presented as current.')
    out = ROOT/'examples/generated/hypersimbedroom'
    out.mkdir(parents=True, exist_ok=True)
    # Change only the locator in a COPY. Provenance, observations and original version remain intact.
    report['scan_id'] = 'hypersimbedroom'
    (out/'report.json').write_text(json.dumps(report, indent=2) + '\n')
    for folder in ('evidence', 'marked'):
        if (scan/folder).exists(): shutil.copytree(scan/folder, out/folder, dirs_exist_ok=True)
    shutil.copyfile(video, out/'source.mp4')
    attribution = {'id': 'hypersim-bedroom', 'scan_id': 'hypersimbedroom', 'title': 'A synthetic bedroom walkthrough',
        'description': 'A completed screening of sampled Hypersim views. No real-world fix or installation is demonstrated.',
        'license': 'Hypersim © Apple Inc. · CC BY-SA 3.0', 'license_url': 'https://creativecommons.org/licenses/by-sa/3.0/',
        'source_url': 'https://github.com/apple-aiml-research/ml-hypersim', 'synthetic': True,
        'scene': 'ai_048_004', 'camera': 'cam_00', 'source_sha256': digest,
        'modifications': '100 tonemapped preview frames encoded as a 6 fps video; evidence frames sampled and marked by RiskLens.',
        'context': 'Synthetic bedroom from Hypersim. Attachment conditions are unknown.'}
    (ROOT/'examples/generated/catalog.json').write_text(json.dumps([attribution], indent=2) + '\n')
    (out/'ATTRIBUTION.json').write_text(json.dumps(attribution, indent=2) + '\n')
    print(out)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('scan', type=Path); parser.add_argument('licensed_video', type=Path)
    args = parser.parse_args(); package(args.scan, args.licensed_video)
