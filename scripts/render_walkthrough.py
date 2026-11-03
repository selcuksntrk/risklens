"""Turn accepted Muse Image shots into a phone-style room walkthrough (1080x1920 portrait, 30 fps, no audio).

Matches the author's real phone clip (1080x1920, 30 fps, ~37 s). A portrait window sweeps across each 3:2 still
(reads as the phone turning), with a slow push-in, low-frequency handheld drift and roll, micro-jitter, whip-pan
transitions with motion blur, sensor noise, vignette and exposure breathing. Every frame carries the label
"AI-generated scene · Muse Image". Deterministic (seeded), so a re-render gives the same file hash.

Run: uv run --with pillow python scripts/render_walkthrough.py istanbul-living [...]
"""
from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'examples' / 'build'
SCENES = ROOT / 'scripts' / 'scenes'
W, H, FPS = 1080, 1920, 30
SHOT_S, WHIP_S = 5.2, 0.4
BASE_ZOOM, PUSH = 1.06, 0.08
LABEL = 'AI-generated scene · Muse Image'


def ease(t: float) -> float:
    return t * t * (3 - 2 * t)


class Hand:
    """Smooth pseudo-random handheld motion: a few incommensurate sines per axis."""
    def __init__(self, seed: int):
        rnd = random.Random(seed)
        self.terms = {axis: [(rnd.uniform(.15, 1.1), rnd.uniform(0, 2 * math.pi), amp * rnd.uniform(.6, 1))
                             for amp in amps]
                      for axis, amps in {'x': (10, 5, 2.5), 'y': (8, 4, 2), 'r': (.35, .15, .05)}.items()}
        self.jitter = [(rnd.uniform(2.5, 4.5), rnd.uniform(0, 2 * math.pi)) for _ in range(2)]

    def at(self, t: float) -> tuple[float, float, float]:
        val = {a: sum(amp * math.sin(2 * math.pi * f * t + p) for f, p, amp in terms) for a, terms in self.terms.items()}
        jx = 1.5 * math.sin(2 * math.pi * self.jitter[0][0] * t + self.jitter[0][1])
        jy = 1.5 * math.sin(2 * math.pi * self.jitter[1][0] * t + self.jitter[1][1])
        return val['x'] + jx, val['y'] + jy, val['r']


def view(src: Image.Image, fx: float, zoom: float, dx: float, dy: float, rot_deg: float) -> Image.Image:
    """Portrait crop centred at horizontal fraction fx of the free pan range, rendered at W x H."""
    sw, sh = src.size
    crop_h = sh / zoom
    crop_w = crop_h * W / H
    s = crop_h / H                      # source pixels per output pixel
    margin = crop_h * .02
    lo, hi = crop_w / 2 + margin, sw - crop_w / 2 - margin
    cx = lo + (hi - lo) * min(max(fx, 0), 1) + dx * s
    cy = sh / 2 + dy * s
    th = math.radians(rot_deg)
    a, b, d, e = s * math.cos(th), -s * math.sin(th), s * math.sin(th), s * math.cos(th)
    c = cx - a * W / 2 - b * H / 2
    f = cy - d * W / 2 - e * H / 2
    return src.transform((W, H), Image.Transform.AFFINE, (a, b, c, d, e, f), resample=Image.Resampling.BICUBIC)


def label(img: Image.Image, font: ImageFont.FreeTypeFont) -> Image.Image:
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    tw = draw.textlength(LABEL, font=font)
    x, y, pad = 36, H - 120, 14
    draw.rounded_rectangle((x, y, x + tw + 2 * pad, y + 30 + 2 * pad), radius=12, fill=(0, 0, 0, 120))
    draw.text((x + pad, y + pad - 2), LABEL, font=font, fill=(255, 255, 255, 230))
    return Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')


def blur_frames(frames: list[Image.Image]) -> Image.Image:
    out = frames[0]
    for i, fr in enumerate(frames[1:], start=2):
        out = Image.blend(out, fr, 1 / i)
    return out


def render(scene_id: str) -> Path:
    bible = next(json.loads(p.read_text()) for p in SCENES.glob('*.json') if json.loads(p.read_text())['id'] == scene_id)
    shots = [(s, Image.open(BUILD / scene_id / 'shots' / f"{s['id']:02d}.png").convert('RGB')) for s in bible['shots']]
    hand = Hand(seed=sum(map(ord, scene_id)))
    font = ImageFont.load_default(size=30)
    out = BUILD / scene_id / 'walkthrough.mp4'
    ff = subprocess.Popen(
        ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
         '-vf', "eq=brightness='0.012*sin(2*PI*t/6.5)':eval=frame,noise=alls=7:allf=t,vignette=angle=PI/6",
         '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
         '-an', '-map_metadata', '-1', '-fflags', '+bitexact', str(out)], stdin=subprocess.PIPE)
    t_global = 0.0

    def pose(shot: dict, u: float, overshoot: float = 0.0) -> tuple[float, float]:
        a, b = (.18, .82) if shot['pan'] == 'lr' else (.82, .18)
        fx = a + (b - a) * ease(min(max(u, 0), 1)) + overshoot * (1 if shot['pan'] == 'lr' else -1)
        return fx, BASE_ZOOM + PUSH * u

    def emit(img: Image.Image):
        ff.stdin.write(label(img, font).tobytes())

    n_shot, n_whip = int(SHOT_S * FPS), int(WHIP_S * FPS)
    for k, (shot, src) in enumerate(shots):
        for i in range(n_shot):
            u = i / (n_shot - 1)
            fx, zoom = pose(shot, u)
            dx, dy, rot = hand.at(t_global)
            emit(view(src, fx, zoom, dx, dy, rot)); t_global += 1 / FPS
        if k + 1 == len(shots):
            break
        nxt_shot, nxt = shots[k + 1]
        for i in range(n_whip):
            w = (i + .5) / n_whip
            dx, dy, rot = hand.at(t_global)
            subs_a, subs_b = [], []
            for j in range(5):                      # sub-frame samples along the whip = motion blur
                q = w + (j - 2) * .06
                fa, za = pose(shot, 1, overshoot=.55 * q * q)
                fb, zb = pose(nxt_shot, 0, overshoot=-.55 * (1 - q) ** 2)
                subs_a.append(view(src, fa, za, dx, dy, rot)); subs_b.append(view(nxt, fb, zb, dx, dy, rot))
            emit(Image.blend(blur_frames(subs_a), blur_frames(subs_b), ease(w))); t_global += 1 / FPS
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit('ffmpeg failed')
    print(f'{out} · {t_global:.1f} s')
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('scenes', nargs='+')
    for s in parser.parse_args().scenes:
        render(s)
