from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse


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


def make_ffmpeg_command(ffmpeg: str, video: Path, output_pattern: Path) -> list[str]:
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video),
        "-vf",
        "fps=1",
        "-q:v",
        "2",
        "-start_number",
        "0",
        str(output_pattern),
    ]
