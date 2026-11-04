"""Assemble seven REAL application recordings and Selçuk's selected voice take.
No generated UI or placeholder footage. Produces a REVIEW export with soft subtitles
and a separate SRT. Human visual/audio review is required before renaming/uploading.
Rehearsal: python scripts/assemble_demo.py --silent-preview --captions docs/submission/captions-draft.srt --output docs/submission/output/preview
Usage: python scripts/assemble_demo.py --voice docs/submission/private/voice-take-1.m4a
       --captions docs/submission/private/captions-aligned.srt
"""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DURATIONS = (15,20,40,30,25,25,20)


def duration(path):
    data=subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(path)])
    return float(json.loads(data)['format']['duration'])


def assemble(folder, voice, captions, out):
    clips=[folder/f'{i:02d}.mp4' for i in range(1,8)]
    for file in [*clips,voice,captions]:
        if not file.is_file(): raise ValueError(f'Missing required actual recording/captions: {file.name}')
    if captions.name=='captions-draft.srt': raise ValueError('Align the draft against the actual voice take first.')
    if out.exists(): raise ValueError('Use a fresh output directory; previous review exports are preserved.')
    for clip,seconds in zip(clips,DURATIONS):
        if duration(clip)<seconds: raise ValueError(f'{clip.name} needs at least {seconds}s of actual footage.')
    if not 150 <= duration(voice) <= 175:
        raise ValueError('Voice take must be 150–175 seconds; adjust delivery instead of silently speeding speech.')
    timestamps=re.findall(r'(\d\d):(\d\d):(\d\d),(\d\d\d)',captions.read_text())
    if not timestamps or any(int(h)*3600+int(m)*60+int(s)+int(ms)/1000>175 for h,m,s,ms in timestamps):
        raise ValueError('Captions must contain valid timestamps within the 175-second timeline.')
    out.mkdir(parents=True)
    parts=[]
    for i,(clip,seconds) in enumerate(zip(clips,DURATIONS),1):
        part=out/f'part-{i:02d}.mp4';parts.append(part)
        # Input recordings must already contain labeled time compression if used.
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(clip),'-t',str(seconds),
                        '-an','-vf','scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30',
                        '-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(part)],check=True)
    listing=out/'concat.txt'
    listing.write_text(''.join(f"file '{p.name}'\n" for p in parts))
    joined=out/'picture.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','concat','-safe','1','-i',str(listing),
                    '-c','copy',str(joined)],check=True)
    exported=out/'risklens-review.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(joined),'-i',str(voice),'-i',str(captions),
                    '-map','0:v:0','-map','1:a:0','-map','2:0','-c:v','copy','-c:a','aac','-b:a','192k',
                    '-af','loudnorm=I=-16:TP=-1.5:LRA=11,apad','-c:s','mov_text','-metadata:s:s:0','language=eng',
                    '-t','175','-movflags','+faststart',str(exported)],check=True)
    shutil.copyfile(captions,out/'risklens.srt')
    actual=duration(exported)
    if not 174 <= actual <= 176: raise ValueError('Unexpected export duration; do not publish.')
    (out/'review-checklist.txt').write_text('REVIEW EXPORT, NOT SUBMITTED\nCheck actual footage matches narration; labels on compressed waits; no private tabs; captions in chosen player; phone legibility; no overclaims; source credits in description.\n')
    print(exported)


def silent_preview(folder, captions, out):
    """Rehearsal cut: the 175 s picture with draft captions as a soft track and NO audio. Never a submission file."""
    clips=[folder/f'{i:02d}.mp4' for i in range(1,8)]
    for clip,seconds in zip(clips,DURATIONS):
        if not clip.is_file() or duration(clip)<seconds: raise ValueError(f'{clip.name} missing or shorter than {seconds}s')
    out.mkdir(parents=True,exist_ok=True); parts=[]
    for i,(clip,seconds) in enumerate(zip(clips,DURATIONS),1):
        part=out/f'preview-part-{i:02d}.mp4';parts.append(part)
        subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(clip),'-t',str(seconds),'-an',
                        '-vf','scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30',
                        '-c:v','libx264','-crf','20','-pix_fmt','yuv420p',str(part)],check=True)
    listing=out/'preview-concat.txt';listing.write_text(''.join(f"file '{p.name}'\n" for p in parts))
    joined=out/'preview-picture.mp4'
    subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','1','-i',str(listing),'-c','copy',str(joined)],check=True)
    final=out/'SILENT-PREVIEW-not-for-submission.mp4'
    subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(joined),'-i',str(captions),'-map','0:v:0','-map','1:0',
                    '-c:v','copy','-c:s','mov_text','-metadata:s:s:0','language=eng','-movflags','+faststart',str(final)],check=True)
    for p in [*parts,joined]: p.unlink()
    print(final, round(duration(final),1),'s')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--voice',type=Path);p.add_argument('--captions',type=Path,required=True)
    p.add_argument('--clips',type=Path,default=ROOT/'docs/submission/private/footage-v3')
    p.add_argument('--output',type=Path,default=ROOT/'docs/submission/output/review-1')
    p.add_argument('--silent-preview',action='store_true',help='rehearsal cut without voice; draft captions allowed')
    args=p.parse_args()
    if args.silent_preview: silent_preview(args.clips,args.captions,args.output)
    elif not args.voice: p.error('--voice is required for a review export')
    else: assemble(args.clips,args.voice,args.captions,args.output)
