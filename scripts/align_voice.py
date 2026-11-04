"""Place a recorded narration on the fixed 175 s picture timeline and write matching captions.
Each section of the plan lists the pieces of the voice recording to use and the words spoken in them.
Every section starts 0.3 s after its slot starts; captions are timed from the speech actually detected
in each piece (silences excluded, words spread by length). Check the result by ear before export.
Usage: python3 scripts/align_voice.py docs/submission/private/voice-plan.json
"""
import json
import re
import subprocess
import sys
from pathlib import Path

DURATIONS = (15, 20, 40, 30, 25, 25, 20)
TOTAL = sum(DURATIONS)


def ts(x):
    ms = int(round(x * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def speech_spans(src, a, b):
    """Speech intervals in [a, b] of src, relative to a."""
    out = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-ss', str(a), '-to', str(b), '-i', str(src),
                          '-af', 'silencedetect=noise=-38dB:d=0.35', '-f', 'null', '-'], capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', out)]
    ends = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', out)]
    spans, t, length = [], 0.0, b - a
    for s, e in zip(starts, ends + [length] * (len(starts) - len(ends))):
        if s > t: spans.append((t, s))
        t = e
    if t < length: spans.append((t, length))
    return [(x, y) for x, y in spans if y - x > .12] or [(0.0, length)]


def chunks(text, limit=74):
    """Single-line caption chunks, split at sentence ends, then commas, then spaces."""
    out = []
    for sentence in re.split(r'(?<=[.!?])\s+', text.strip()):
        while len(sentence) > limit:
            head = sentence[:limit]
            comma = head.rfind(', ') + 1
            cut = comma if comma > limit * .4 else head.rfind(' ')
            out.append(sentence[:cut].strip()); sentence = sentence[cut:].strip()
        out.append(sentence)
    return out


def place(words_weight, total_weight, spans, spoken, position):
    """Timeline position `position` of speech time spent, mapped back through the speech spans."""
    target = spoken * words_weight / total_weight + position
    used = 0.0
    for x, y in spans:
        if used + (y - x) >= target: return x + (target - used)
        used += y - x
    return spans[-1][1]


def main(plan_path):
    plan_path = Path(plan_path); plan = json.loads(plan_path.read_text()); base = plan_path.parent
    assert len(plan['sections']) == len(DURATIONS), 'expected 7 sections'
    cues, filters, inputs, start = [], [], [], 0.0
    for section, slot in zip(plan['sections'], DURATIONS):
        t = start + .3; spans = []
        for piece in section['pieces']:
            src = base / piece['src']; a, b = piece['start'], piece['end']; n = len(inputs) // 6
            inputs += ['-ss', str(a), '-to', str(b), '-i', str(src)]
            gain = piece.get('gain_db', 0)
            filters.append(f'[{n}:a]aformat=channel_layouts=mono,volume={gain}dB,afade=in:d=0.03,'
                           f'afade=out:st={b - a - .05:.3f}:d=0.05,adelay={int(t * 1000)}:all=1[a{n}]')
            spans += [(t + x, t + y) for x, y in speech_spans(src, a, b)]
            t += b - a + piece.get('gap_after', 0)
        if t - .3 > start + slot:
            raise ValueError(f'section overruns its {slot}s slot by {t - .3 - start - slot:.1f}s')
        print(f'slot {start:>5.1f}–{start + slot:>5.1f} · speech ends {t:.1f}')
        parts = chunks(section['text']); weights = [len(p) for p in parts]; total = sum(weights)
        spoken = sum(y - x for x, y in spans); done = 0
        for p, w in zip(parts, weights):
            c0 = place(done, total, spans, spoken, 0); c1 = place(done + w, total, spans, spoken, 0)
            cues.append((c0, c1, p)); done += w
        start += slot
    n = len(inputs) // 6
    filters.append(''.join(f'[a{i}]' for i in range(n)) +
                   f'amix=inputs={n}:duration=longest:normalize=0,apad=whole_dur={TOTAL - .1},atrim=0:{TOTAL - .1}[out]')
    voice = base / plan['output']
    subprocess.run(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', *inputs, '-filter_complex', ';'.join(filters),
                    '-map', '[out]', '-ac', '1', '-c:a', 'aac', '-b:a', '192k', str(voice)], check=True)
    srt = '\n'.join(f'{i}\n{ts(a)} --> {ts(b)}\n{text}\n' for i, (a, b, text) in enumerate(cues, 1))
    (base / plan['captions']).write_text(srt)
    print(voice, base / plan['captions'], len(cues), 'cues')


if __name__ == '__main__':
    main(sys.argv[1])
