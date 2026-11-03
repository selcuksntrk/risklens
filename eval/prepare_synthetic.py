"""Prepare ONLY the five existing Hypersim clips; no network or model calls.
Usage: python eval/prepare_synthetic.py --source-root ../spikes/data/r
Outputs ignored eval/private/synthetic inputs and a public source/hash registry.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = 'ai_048_004_cam_00'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(source_root, destination):
    observations_path = ROOT/'eval/synthetic-observations.json'
    observations = json.loads(observations_path.read_text())
    if destination.exists():
        raise ValueError('Use a new destination: frozen inputs must not be overwritten')
    for name in observations['scenes']:
        folder = source_root/name
        gt = json.loads((folder/'gt.json').read_text())
        if gt['license'] != 'Hypersim, CC BY-SA 3.0 (Apple Inc.)' or not (folder/'clip.mp4').is_file():
            raise ValueError('Missing source or unexpected license')
    destination.mkdir(parents=True)
    shutil.copyfile(observations_path, destination/'observations.json')
    rows, registry = [], []
    for name in sorted(observations['scenes']):
        folder = source_root/name
        gt = json.loads((folder/'gt.json').read_text())
        video = destination/(name+'.mp4')
        shutil.copyfile(folder/'clip.mp4', video)
        rows.append({'clip_id': name, 'room_id': gt['scene'], 'split': 'development', 'case': 'A0',
                     'video': video.name, 'sha256': sha(video), 'pre_model_observations_recorded': True,
                     'context': 'Synthetic interior. Attachment conditions are unknown.',
                     'repetitions': {'full': 3 if name == DEMO else 1}})
        registry.append({'scene': gt['scene'], 'camera': gt['camera'], 'clip_sha256': sha(video),
                         'legacy_gt_sha256': sha(folder/'gt.json'), 'previously_used_in_development': True,
                         'license': 'CC BY-SA 3.0', 'creator': 'Apple Inc.',
                         'source_url': f"https://docs-assets.developer.apple.com/ml-research/datasets/hypersim/v1/scenes/{gt['scene']}.zip",
                         'modifications': 'Existing tonemapped previews encoded at 6 fps; see spike downloader.'})
    original = destination/(DEMO+'.mp4')
    controls = [('B0', original, 'Exact original file; deterministic hash guard, not model perception.'),
                ('B1', destination/'unchanged-reencoded.mp4', 'Same rendered sequence re-encoded; no physical change or new camera recording.'),
                ('B3', destination/'cropped-view.mp4', 'Central crop of the unchanged sequence; tests evidence loss, not a new camera recording.'),
                ('B4', destination/'ai_048_005_cam_01.mp4', 'Different synthetic bedroom and different objects; not a physical change.')]
    for case, dest, description in controls:
        if case in ('B1', 'B3'):
            filters = 'scale=640:-2' if case == 'B1' else 'crop=iw/2:ih/2,scale=640:-2'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(original),'-vf',filters,
                            '-c:v','libx264','-crf','25','-pix_fmt','yuv420p',str(dest)],check=True)
        rows.append({'clip_id': 'control-'+case.lower(), 'room_id': DEMO.rsplit('_cam_',1)[0],
                     'split':'development','case':case,'baseline_clip_id':DEMO,'video':dest.name,
                     'sha256':sha(dest),'pre_model_observations_recorded':True,'variants':['full'],
                     'control_description':description})
    manifest = {'data_type':'synthetic','evaluation_kind':'development_regression',
                'observations_file':'observations.json','observations_sha256':sha(destination/'observations.json'),
                'physical_positive_cases':0,'clips':rows}
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (ROOT/'eval/synthetic-sources.json').write_text(json.dumps({'data_type':'synthetic',
       'dataset_url':'https://github.com/apple-aiml-research/ml-hypersim',
       'license_url':'https://creativecommons.org/licenses/by-sa/3.0/',
       'observations_sha256':sha(observations_path),'scenes':registry},indent=2)+'\n')
    print(destination/'manifest.json')


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--destination',type=Path,default=ROOT/'eval/private/synthetic')
    args=p.parse_args(); prepare(args.source_root,args.destination)
