"""Enforce output dimensions with actual stream metadata, including portrait video."""

import json
import math
import subprocess
from pathlib import Path
from typing import Any

from app.sources import SourceError


def executable(name: str, location: str | None) -> str:
    if not location:
        return name
    root = Path(location)
    if root.is_file():
        root = root.parent
    return str(root / (f"{name}.exe" if (root / f"{name}.exe").exists() else name))


def inspect_media(path: Path, max_duration: int, location: str | None) -> dict[str, Any]:
    probe = subprocess.run(
        [
            executable("ffprobe", location),
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    metadata = json.loads(probe.stdout)
    duration = float(metadata.get("format", {}).get("duration", "nan"))
    if not math.isfinite(duration) or duration <= 0 or duration > max_duration:
        raise SourceError("duration_limit")
    return dict(metadata)


def fit_video(path: Path, quality: int, max_duration: int, location: str | None) -> None:
    metadata = inspect_media(path, max_duration, location)
    video = next(
        (stream for stream in metadata["streams"] if stream["codec_type"] == "video"), None
    )
    if not video:
        raise SourceError("provider_error")
    width, height = video["width"], video["height"]
    if min(width, height) <= quality:
        return
    if any(abs(data.get("rotation", 0)) % 180 == 90 for data in video.get("side_data_list", [])):
        width, height = height, width
    scale = f"{quality}:-2" if width < height else f"-2:{quality}"
    output = path.with_name("normalized.mp4")
    subprocess.run(
        [
            executable("ffmpeg", location),
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-vf",
            f"scale={scale}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=1800,
    )
    output.replace(path)
