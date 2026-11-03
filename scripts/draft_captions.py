"""Draft SRT from docs/submission/NARRATION.md: each segment's text spread over its fixed slot by word count.
A rehearsal aid only; align against the actual voice take before export (assemble_demo.py refuses the draft).
Usage: python3 scripts/draft_captions.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DURATIONS = (15, 20, 40, 30, 25, 25, 20)


def ts(x):
    ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def wrap(text, width=42):
    lines, line = [], ''
    for w in text.split():
        if line and len(line) + len(w) + 1 > width:
            lines.append(line); line = w
        else:
            line = f'{line} {w}'.strip()
    return '\n'.join(lines + [line])


def main():
    text = (ROOT / 'docs/submission/NARRATION.md').read_text()
    segments = re.findall(r'## \d\d · [^\n]+\n\n(.+?)\n\n', text, re.S)
    assert len(segments) == len(DURATIONS), 'expected 7 narration segments'
    out, start, k = [], 0.0, 1
    for seg, dur in zip(segments, DURATIONS):
        chunks = []
        for sentence in re.split(r'(?<=[.!?])\s+', seg.strip()):
            words = sentence.split()
            while len(words) > 14:
                chunks.append(' '.join(words[:12])); words = words[12:]
            chunks.append(' '.join(words))
        total = sum(len(c.split()) for c in chunks); t0 = start + .3
        for c in chunks:
            dt = (dur - .6) * len(c.split()) / total
            out.append(f'{k}\n{ts(t0)} --> {ts(t0 + dt)}\n{wrap(c)}\n'); k += 1; t0 += dt
        print(f'{dur:>3}s {len(seg.split()):>3} words {len(seg.split()) / dur:.2f} w/s')
        start += dur
    (ROOT / 'docs/submission/captions-draft.srt').write_text('\n'.join(out))


if __name__ == '__main__':
    main()
