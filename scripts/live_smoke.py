"""Opt-in live provider check. Runs both formats and verifies them with ffprobe."""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.media import executable as media_executable


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="A short public video you are allowed to download")
    parser.add_argument(
        "--kind", choices=["mp4", "mp3"], help="Check one output format (default: both)"
    )
    args = parser.parse_args()
    failed = False
    with tempfile.TemporaryDirectory(prefix="ytd-live-") as directory:
        settings = Settings(
            data_dir=Path(directory), allowed_hosts=["testserver"], job_timeout_seconds=90
        )
        with TestClient(create_app(settings)) as client:
            client.get("/api/session")
            if client.get("/readyz").status_code != 200:
                print("Runtime unavailable: install FFmpeg, ffprobe and Node.js.")
                return 1
            for kind, quality in [("mp4", 360), ("mp3", 192)]:
                if args.kind and args.kind != kind:
                    continue
                response = client.post(
                    "/api/jobs",
                    json={"url": args.url, "kind": kind, "quality": quality},
                    headers={"X-Requested-With": "yt-downloader"},
                )
                if response.status_code != 202:
                    print(
                        json.dumps(
                            {"kind": kind, "status": response.status_code, "error": response.json()}
                        )
                    )
                    failed = True
                    continue
                job = response.json()
                while job["state"] in {"queued", "downloading", "processing"}:
                    time.sleep(0.5)
                    job = client.get(f"/api/jobs/{job['id']}").json()
                result = {
                    "provider": job["provider"],
                    "kind": kind,
                    "state": job["state"],
                    "error": job["error"],
                    "bytes": job["file_bytes"],
                }
                if job["state"] == "complete":
                    response = client.get(f"/api/jobs/{job['id']}/file")
                    output = Path(directory) / f"verified.{kind}"
                    output.write_bytes(response.content)
                    executable = shutil.which("ffprobe")
                    if settings.ffmpeg_location:
                        root = Path(settings.ffmpeg_location)
                        executable = str(
                            root / ("ffprobe.exe" if sys.platform == "win32" else "ffprobe")
                        )
                    assert executable
                    probe = subprocess.run(
                        [executable, "-v", "error", "-show_streams", "-of", "json", str(output)],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    streams = json.loads(probe.stdout)["streams"]
                    codecs = [stream["codec_name"] for stream in streams]
                    result["codecs"] = codecs
                    if kind == "mp4":
                        video = next(
                            (stream for stream in streams if stream["codec_type"] == "video"), None
                        )
                        if (
                            not video
                            or video["codec_name"] != "h264"
                            or video.get("pix_fmt") != "yuv420p"
                            or min(video["width"], video["height"]) > quality
                            or any(
                                s["codec_name"] != "aac"
                                for s in streams
                                if s["codec_type"] == "audio"
                            )
                        ):
                            failed = True
                        elif video:
                            result["dimensions"] = [video["width"], video["height"]]
                    if response.status_code != 200 or (kind == "mp3" and "mp3" not in codecs):
                        failed = True
                    decoded = subprocess.run(
                        [
                            media_executable("ffmpeg", settings.ffmpeg_location),
                            "-nostdin",
                            "-v",
                            "error",
                            "-xerror",
                            "-err_detect",
                            "explode",
                            "-i",
                            str(output),
                            "-f",
                            "null",
                            "-",
                        ],
                        capture_output=True,
                        timeout=90,
                    )
                    result["full_decode"] = decoded.returncode == 0
                    if decoded.returncode:
                        failed = True
                else:
                    failed = True
                print(json.dumps(result), flush=True)
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
