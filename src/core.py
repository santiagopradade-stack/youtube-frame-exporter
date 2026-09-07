from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse


VALID_INTERVALS = (1, 2, 4, 8, 16)
VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".m4v", ".webm"}


def is_youtube_url(value: str) -> bool:
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


def make_ffmpeg_command(
    ffmpeg: str,
    video: Path,
    output_pattern: Path,
    interval: int,
) -> list[str]:
    if interval not in VALID_INTERVALS:
        raise ValueError(f"Intervalo no permitido: {interval}")
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video),
        "-vf",
        f"fps=1/{interval}",
        "-q:v",
        "2",
        "-start_number",
        "0",
        str(output_pattern),
    ]

