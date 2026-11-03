"""Build both sides with one content-derived release ID. Run from any directory."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def release_id():
    paths = [*ROOT.joinpath('backend/app').rglob('*.py'), *ROOT.joinpath('frontend/src').rglob('*'),
             ROOT/'backend/uv.lock', ROOT/'frontend/package-lock.json', ROOT/'backend/app/knowledge/fema_e74.json',
             ROOT/'deploy/modal_app.py', ROOT/'deploy/requirements.txt', ROOT/'backend/pyproject.toml',
             ROOT/'frontend/vite.config.ts', ROOT/'scripts/build_release.py']
    digest = hashlib.sha256()
    for path in sorted(p for p in paths if p.is_file() and '__pycache__' not in p.parts):
        digest.update(str(path.relative_to(ROOT)).encode()); digest.update(path.read_bytes())
    return 'v2-' + digest.hexdigest()[:12]

if __name__ == '__main__':
    version = release_id()
    (ROOT / 'VERSION').write_text(version + '\n')
    subprocess.run(['npm', 'run', 'build'], cwd=ROOT/'frontend', check=True,
                   env={**os.environ, 'VITE_RISKLENS_VERSION': version})
    manifest = {'version': version, 'report_schema_version': 2,
                'assets': {str(p.relative_to(ROOT/'frontend/dist')): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted((ROOT/'frontend/dist').rglob('*')) if p.is_file()}}
    (ROOT/'release.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(version)
