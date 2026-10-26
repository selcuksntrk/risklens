"""Set-of-marks: draw SAM boxes with short numeric marks on keyframes so Spark can refer to tracked objects by ID."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.meta.sam import Track

PALETTE = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#42d4f4", "#f032e6", "#bfef45",
           "#469990", "#9a6324", "#800000", "#000075"]
MAX_MARKS = 30


def assign_marks(tracks: list[Track]) -> dict[str, Track]:
    """Mark the longest-lived tracks first; '1', '2', ... are what Spark sees and answers with."""
    ranked = sorted(tracks, key=lambda t: len(t.boxes), reverse=True)[:MAX_MARKS]
    return {str(i + 1): t for i, t in enumerate(ranked)}


def box_near(track: Track, frame: int, window: int = 2) -> list[float] | None:
    """Box at `frame`, or at the nearest frame within `window` (SAM can skip a frame or two)."""
    for delta in range(window + 1):
        for f in (frame - delta, frame + delta):
            if f in track.boxes:
                return track.boxes[f]
    return None


def _font(size: int):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size)
    except OSError:
        return ImageFont.load_default(size)


def draw_marks(frame_path: Path, frame: int, marks: dict[str, Track], out: Path,
               only: set[str] | None = None) -> list[str]:
    """Draw every mark visible on this frame; return the marks drawn."""
    image = Image.open(frame_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = _font(max(16, image.height // 28))
    drawn = []
    for mark, track in marks.items():
        if only is not None and mark not in only:
            continue
        box = box_near(track, frame)
        if box is None:
            continue
        color = PALETTE[(int(mark) - 1) % len(PALETTE)]
        draw.rectangle(box, outline=color, width=max(3, image.height // 240))
        label = f"{mark} {track.concept}" if only is not None else mark
        width = draw.textlength(label, font=font)
        x = min(max(box[0] + 4, 3), image.width - width - 6)    # keep labels inside the frame
        y = max(box[1] + 4, 3)
        tb = draw.textbbox((x, y), label, font=font)
        draw.rectangle((tb[0] - 3, tb[1] - 3, tb[2] + 3, tb[3] + 3), fill=color)
        draw.text((x, y), label, fill="white", font=font)
        drawn.append(mark)
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, quality=88)
    return drawn
