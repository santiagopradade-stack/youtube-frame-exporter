from __future__ import annotations

import math
import re
from pathlib import Path
from urllib.parse import urlparse


INTERVALS = (1, 3, 5)


def is_youtube_url(value: str) -> bool:
    """Return True for normal YouTube and youtu.be video URLs."""
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    return host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")


def safe_folder_name(title: str, video_id: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip(" .")
    cleaned = re.sub(r"\s+", " ", cleaned)[:100].rstrip(" .")
    return f"{cleaned or 'youtube_video'} [{video_id}]"


def sample_seconds(duration_seconds: float) -> list[int]:
    """Return whole-second timestamps from zero to just before the video ends."""
    if not math.isfinite(duration_seconds) or duration_seconds <= 0:
        raise ValueError("Video duration must be a positive finite number.")
    return list(range(math.ceil(duration_seconds)))


def intervals_for_second(second: int) -> tuple[int, ...]:
    """Return the output intervals that should receive a timestamped frame."""
    if second < 0:
        raise ValueError("Second cannot be negative.")
    return tuple(interval for interval in INTERVALS if second % interval == 0)


def scene_frame_targets(scenes: list[tuple[int, int]]) -> dict[int, list[str]]:
    """Retained for compatibility with older app builds."""
    targets: dict[int, list[str]] = {}
    for index, (start, end) in enumerate(scenes, start=1):
        if start < 0 or end <= start:
            raise ValueError(f"Invalid scene range: {start}, {end}")
        targets.setdefault(start, []).append(f"scene_{index:04d}_first.jpg")
        targets.setdefault(end - 1, []).append(f"scene_{index:04d}_last.jpg")
    return targets


def unique_output_folder(parent: Path, name: str) -> Path:
    candidate = parent / name
    suffix = 2
    while candidate.exists():
        candidate = parent / f"{name} ({suffix})"
        suffix += 1
    return candidate
