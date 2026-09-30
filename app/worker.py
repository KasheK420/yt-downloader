"""Isolated media worker. Run only with server-generated arguments."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yt_dlp


def emit(event: str, **values: Any) -> None:
    print(json.dumps({"event": event, **values}), flush=True)


class QuietLogger:
    def debug(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass


def download(args: argparse.Namespace) -> int:
    failure = "provider_error"

    def metadata(info: dict[str, Any], *, incomplete: bool = False) -> str | None:
        nonlocal failure
        if incomplete:
            return None
        if info.get("is_live") or info.get("live_status") in {"is_live", "is_upcoming"}:
            failure = "live_unsupported"
            return failure
        duration = info.get("duration")
        if not isinstance(duration, (int, float)) or duration > args.max_duration:
            failure = "duration_limit"
            return failure
        emit("metadata", title=str(info.get("title") or "YouTube video")[:300])
        return None

    def progress(data: dict[str, Any]) -> None:
        nonlocal failure
        downloaded = data.get("downloaded_bytes", 0)
        total = data.get("total_bytes") or data.get("total_bytes_estimate")
        if downloaded > args.max_file_bytes:
            failure = "size_limit"
            raise yt_dlp.utils.DownloadError("Media exceeds the size limit")
        if data.get("status") == "downloading" and total:
            emit("progress", percent=min(98, downloaded / total * 98))

    def postprocess(data: dict[str, Any]) -> None:
        if data.get("status") == "started":
            emit("processing")

    options: dict[str, Any] = {
        "outtmpl": {"default": str(Path.cwd() / "media.%(ext)s")},
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "logger": QuietLogger(),
        "progress_hooks": [progress],
        "postprocessor_hooks": [postprocess],
        "match_filter": metadata,
        "max_filesize": args.max_file_bytes,
        "socket_timeout": 20,
        "retries": 2,
        "fragment_retries": 2,
        "extractor_retries": 1,
        "concurrent_fragment_downloads": 1,
        "overwrites": False,
        "cachedir": False,
        "restrictfilenames": True,
        "js_runtimes": {args.js_runtime: {}},
        "remote_components": set(),
        "ffmpeg_location": args.ffmpeg_location,
        "postprocessors": [],
    }
    if args.kind == "mp3":
        options["format"] = "bestaudio/best"
        options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(args.quality),
            },
            {"key": "FFmpegMetadata", "add_metadata": True},
        ]
    else:
        options["format"] = (
            f"bestvideo[height<={args.quality}][ext=mp4]+bestaudio[ext=m4a]/"
            f"best[height<={args.quality}][ext=mp4]"
        )
        options["merge_output_format"] = "mp4"
        options["postprocessors"] = [{"key": "FFmpegMetadata", "add_metadata": True}]
    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            downloader.download([args.url])
        output = Path(f"media.{args.kind}")
        if not output.is_file():
            emit("error", code=failure)
            return 1
        if output.stat().st_size > args.max_file_bytes:
            emit("error", code="size_limit")
            return 1
        emit("complete")
        return 0
    except Exception:
        emit("error", code=failure)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--kind", choices=["mp3", "mp4"], required=True)
    parser.add_argument("--quality", type=int, required=True)
    parser.add_argument("--max-duration", type=int, required=True)
    parser.add_argument("--max-file-bytes", type=int, required=True)
    parser.add_argument("--js-runtime", choices=["node", "deno"], default="node")
    parser.add_argument("--ffmpeg-location")
    return download(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
