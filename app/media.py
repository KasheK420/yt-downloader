"""Publish decodable H.264/AAC MP4 files with bounded, orientation-aware dimensions."""

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
    if any(abs(data.get("rotation", 0)) % 180 == 90 for data in video.get("side_data_list", [])):
        width, height = height, width
    resize = min(width, height) > quality
    transcode = resize or video.get("codec_name") != "h264" or video.get("pix_fmt") != "yuv420p"
    audio = next(
        (stream for stream in metadata["streams"] if stream["codec_type"] == "audio"), None
    )
    options = ["-c:v", "copy"]
    if transcode:
        scale = (
            (f"{quality}:-2" if width < height else f"-2:{quality}")
            if resize
            else ("trunc(iw/2)*2:trunc(ih/2)*2")
        )
        options = [
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
        ]
    if audio and (audio.get("codec_name") != "aac" or audio.get("profile") != "LC"):
        options += ["-c:a", "aac", "-profile:a", "aac_low", "-b:a", "192k"]
    else:
        options += ["-c:a", "copy"]
    output = path.with_name("normalized.mp4")
    base = [executable("ffmpeg", location), "-nostdin", "-v", "error", "-xerror"]
    try:
        normalized = subprocess.run(
            [
                *base,
                "-err_detect",
                "explode",
                "-i",
                str(path),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                *options,
                "-movflags",
                "+faststart",
                str(output),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=1800,
        )
        if normalized.stderr.strip():
            raise SourceError("processing_error")
        inspect_media(output, max_duration, location)
        # Container metadata alone can look valid while compressed frames are damaged.
        decoded = subprocess.run(
            [
                *base,
                "-err_detect",
                "explode",
                "-i",
                str(output),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-f",
                "null",
                "-",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=1800,
        )
        # Some older FFmpeg versions log decoder errors but still return exit status zero.
        if decoded.stderr.strip():
            raise SourceError("processing_error")
    except (subprocess.SubprocessError, OSError) as exc:
        raise SourceError("processing_error") from exc
    output.replace(path)
