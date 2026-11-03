"""ffmpeg helpers: phone video (mp4 or webm) -> H.264 proxy that SAM accepts, and frames aligned with SAM frame indices."""
from __future__ import annotations

import json
import subprocess
import math
from pathlib import Path

from app.config import FFMPEG_TIMEOUT_S, MAX_VIDEO_SECONDS, PROXY_FPS, PROXY_HEIGHT


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-xerror", "-y", *args], check=True, timeout=FFMPEG_TIMEOUT_S)


def make_proxy(src: Path, out: Path, fps: int = PROXY_FPS, height: int = PROXY_HEIGHT,
               max_seconds: int = MAX_VIDEO_SECONDS) -> Path:
    """SAM rejects VP9/WebM; a low-fps proxy also keeps per-frame SAM billing small. Audio is dropped and the
    video is trimmed to `max_seconds` (SAM bills per frame, so an hour-long upload must not become an hour of frames)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg("-i", str(src), "-vf", f"fps={fps},scale=-2:'min({height},ih)'", "-an",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-movflags", "+faststart", "-t", str(max_seconds), str(out))
    return out


def extract_frames(proxy: Path, out_dir: Path) -> list[Path]:
    """Every proxy frame as frames/00000.jpg..., so file index == SAM frame index."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.glob("*.jpg"):     # a reused folder must not mix in frames from an older video
        stale.unlink()
    ffmpeg("-i", str(proxy), "-start_number", "0", "-q:v", "3", str(out_dir / "%05d.jpg"))
    return sorted(out_dir.glob("*.jpg"))


def probe(path: Path, allow_unknown_duration: bool = False) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,nb_frames,codec_name:format=duration", "-of", "json", str(path)],
                         check=True, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_S).stdout
    data = json.loads(out)
    if not data.get("streams"):
        raise ValueError("No decodable video stream.")
    stream = data["streams"][0]
    duration = float(data.get("format", {}).get("duration", 0))
    if not math.isfinite(duration) or (duration <= 0 and not allow_unknown_duration) or stream.get("width", 0) <= 0 or stream.get("height", 0) <= 0:
        raise ValueError("Video has no usable frames or duration.")
    frame_count = str(stream.get("nb_frames", "0"))
    return {"width": stream["width"], "height": stream["height"], "codec": stream["codec_name"],
            "frames": int(frame_count) if frame_count.isdigit() else 0, "duration_s": duration}


def validate(path: Path) -> dict:
    if not path.is_file() or not path.stat().st_size:
        raise ValueError("The video is empty.")
    info = probe(path, allow_unknown_duration=True)
    # Decode a frame before accepting quota or any inference; full proxy decode is checked in the job.
    ffmpeg("-i", str(path), "-frames:v", "1", "-f", "null", "-")
    return info


def keyframe_count(duration_s: float, minimum: int, every_s: float, maximum: int) -> int:
    """About one keyframe per `every_s` seconds, clamped to [minimum, maximum]."""
    return max(minimum, min(maximum, math.ceil(duration_s / every_s)))


def pick_keyframes(n_frames: int, k: int) -> list[int]:
    """k evenly spaced frame indices, avoiding the very first/last frames (often motion-blurred)."""
    if n_frames <= k:
        return list(range(n_frames))
    step = n_frames / k
    return [int(step * i + step / 2) for i in range(k)]
