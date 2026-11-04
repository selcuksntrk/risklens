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


def burn_captions(picture, captions, out, dst):
    """Burn single-line captions into a band under the footage labels (label box ends at y=1032).
    Uses rendered PNGs because this ffmpeg build has no subtitles/drawtext filter. Needs Pillow."""
    from PIL import Image, ImageDraw, ImageFont
    font=ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',36)
    band=(1920,46); folder=out/'caption-frames'; folder.mkdir()
    blank=folder/'blank.png'; Image.new('RGBA',band,(0,0,0,0)).save(blank)
    def secs(h,m,s,ms): return int(h)*3600+int(m)*60+int(s)+int(ms)/1000
    cues=re.findall(r'(\d\d):(\d\d):(\d\d),(\d\d\d) --> (\d\d):(\d\d):(\d\d),(\d\d\d)\n(.+?)(?:\n\n|\n*\Z)',captions.read_text(),re.S)
    lines,t=[],0.0
    for i,c in enumerate(cues):
        a,b,text=secs(*c[:4]),secs(*c[4:8]),' '.join(c[8].split())
        img=Image.new('RGBA',band,(0,0,0,0));d=ImageDraw.Draw(img);w=d.textlength(text,font=font)
        if w>1840: raise ValueError(f'Caption too wide for one line: {text}')
        x=(1920-w)/2
        d.rounded_rectangle((x-18,0,x+w+18,45),10,fill=(0,0,0,215));d.text((x,3),text,font=font,fill=(255,255,255,255))
        png=folder/f'{i:03d}.png';img.save(png)
        if a>t: lines+= [f"file '{blank.name}'",f'duration {a-t:.3f}']
        lines+=[f"file '{png.name}'",f'duration {b-a:.3f}'];t=b
    lines+=[f"file '{blank.name}'",f'duration {max(175-t,.1):.3f}',f"file '{blank.name}'"]
    listing=folder/'captions.ffconcat';listing.write_text('ffconcat version 1.0\n'+'\n'.join(lines)+'\n')
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(picture),'-f','concat','-safe','0','-i',str(listing),
                    '-filter_complex','[1:v]fps=30,format=rgba[c];[0:v][c]overlay=0:1033:shortest=1,format=yuv420p',
                    '-c:v','libx264','-crf','18',str(dst)],check=True)
    shutil.rmtree(folder)


def assemble(folder, voice, captions, out, burn=False):
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
    if burn:
        burned=out/'picture-captioned.mp4';burn_captions(joined,captions,out,burned)
        subs_in,subs_out=[],[]
        joined=burned
    else:
        subs_in,subs_out=['-i',str(captions)],['-map','2:0','-c:s','mov_text','-metadata:s:s:0','language=eng']
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(joined),'-i',str(voice),*subs_in,
                    '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k',
                    '-af','loudnorm=I=-16:TP=-1.5:LRA=11,apad',*subs_out,
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
    p.add_argument('--burn-captions',action='store_true',help='burn captions into the picture instead of a soft track (needs Pillow)')
    args=p.parse_args()
    if args.silent_preview: silent_preview(args.clips,args.captions,args.output)
    elif not args.voice: p.error('--voice is required for a review export')
    else: assemble(args.clips,args.voice,args.captions,args.output,args.burn_captions)
