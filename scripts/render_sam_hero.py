"""Draw real SAM 3.1 masks from saved API output onto the source walkthrough (nothing is hand-placed).
Inputs: hero/<concept>.txt = raw SAM text for a 15 fps, 540x960 proxy of the source. Output: 608x1080, 30 fps.
Usage: uv run --no-project --with meta-sam-parser --with numpy --with pillow python scripts/render_sam_hero.py <hero dir> <source.mp4> <out.mp4> concept[,concept]
"""
import re
import subprocess
import sys
from pathlib import Path

import meta_sam_parser as sam
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 608, 1080
COLORS = {'wardrobe': (255, 214, 10), 'suitcase': (255, 59, 48), 'bed': (255, 255, 255)}
TOK = re.compile(r"(?m)^<(\d+)f>|(?:^|(?<=,)|(?<=f>))(\d+)<\|box;([^|]*)\|><\|mask;x=(\d+);y=(\d+);data=(\d+),(\d+),(!.*?)\|>")
FONT = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 22, index=1)


def load(path):
    frame, out = 0, {}
    for t in TOK.finditer(Path(path).read_text()):
        if t.group(1) is not None:
            frame = int(t.group(1)); continue
        f = dict(kv.split('=') for kv in t.group(3).split(';'))
        out.setdefault(frame, {})[t.group(2)] = ([int(f[k]) for k in ('x1', 'y1', 'x2', 'y2')], int(t.group(6)), int(t.group(7)), t.group(8))
    return out


def main(hero, source, output, concepts):
    tracks = {c: load(Path(hero) / f'{c}.txt') for c in concepts}
    k = W / 540
    read = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', source, '-vf', f'scale={W}:{H}:flags=lanczos,fps=30',
                             '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    write = subprocess.Popen(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', '30', '-i', '-',
                              '-c:v', 'libx264', '-crf', '15', '-pix_fmt', 'yuv420p', output], stdin=subprocess.PIPE)
    n = 0
    while True:
        raw = read.stdout.read(W * H * 3)
        if len(raw) < W * H * 3:
            break
        img = np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(np.float32)
        labels, f = [], n // 2
        for concept in concepts:
            color = np.array(COLORS[concept], np.float32)
            for box, rows, cols, payload in tracks[concept].get(f, {}).values():
                mask = np.frombuffer(sam.decode_mask_to_raster(sam.SegmentationMask(encoding='one_bit', payload=payload, width=cols, height=rows)), np.uint8).reshape(rows, cols) > 0
                x0, y0 = round(box[0] * k), round(box[1] * k)
                w = min(max(round(cols * k), 1), W - x0); h = min(max(round(rows * k), 1), H - y0)
                m = np.array(Image.fromarray((mask * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR), np.float32) / 255
                on = m > .5
                edge = on & ~(np.roll(on, 3, 0) & np.roll(on, -3, 0) & np.roll(on, 3, 1) & np.roll(on, -3, 1))
                alpha = (on * .26 + edge * .74)[..., None]
                view = img[y0:y0 + h, x0:x0 + w]
                view[:] = view * (1 - alpha) + color * alpha
                labels.append((concept, x0, y0, tuple(COLORS[concept])))
        frame = Image.fromarray(img.astype(np.uint8)); draw = ImageDraw.Draw(frame)
        for name, x, y, color in labels:
            tw = draw.textlength(name, font=FONT); x = min(x + 8, W - tw - 24); y = max(y + 8, 8)
            draw.rectangle((x, y, x + tw + 16, y + 32), fill=color); draw.text((x + 8, y + 3), name.upper(), font=FONT, fill=(17, 17, 17))
        write.stdin.write(frame.tobytes()); n += 1
    write.stdin.close(); write.wait(); read.wait(); print(output, n, 'frames')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(','))
