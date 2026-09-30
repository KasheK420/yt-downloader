"""Real yt-dlp and FFmpeg against generated media, never the public provider."""

import argparse
import functools
import json
import os
import shutil
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yt_dlp
from yt_dlp.extractor.common import InfoExtractor

from app.config import Settings
from app.worker import download


@pytest.fixture
def media_tools():
    root = Settings().ffmpeg_location
    suffix = ".exe" if os.name == "nt" else ""
    ffmpeg = str(Path(root) / f"ffmpeg{suffix}") if root else shutil.which("ffmpeg")
    ffprobe = str(Path(root) / f"ffprobe{suffix}") if root else shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        if os.environ.get("CI"):
            pytest.fail("CI must provide FFmpeg and ffprobe")
        pytest.skip("Install FFmpeg or set YTD_FFMPEG_LOCATION for real conversion tests")
    return ffmpeg, ffprobe, root


@pytest.fixture
def media_server(tmp_path: Path, media_tools):
    ffmpeg, _, _ = media_tools
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=160x90:r=12",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(source / "sample.mp4"),
        ],
        check=True,
        capture_output=True,
    )

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(QuietHandler, directory=source)
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/sample.mp4"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("kind,quality,codec", [("mp3", 192, "mp3"), ("mp4", 720, "h264")])
def test_worker_converts_real_synthetic_media(
    tmp_path, media_tools, media_server, monkeypatch, capsys, kind, quality, codec
):
    original = yt_dlp.YoutubeDL

    class FixtureIE(InfoExtractor):
        _VALID_URL = r"fixture:(?P<id>video)"

        def _real_extract(self, url):
            return {
                "id": "video",
                "title": "Synthetic test",
                "duration": 1,
                "url": media_server,
                "ext": "mp4",
                "height": 90,
                "vcodec": "h264",
                "acodec": "aac",
            }

    def fixture_downloader(options):
        downloader = original(options, auto_init=False)
        downloader.add_info_extractor(FixtureIE())
        return downloader

    monkeypatch.setattr(yt_dlp, "YoutubeDL", fixture_downloader)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.chdir(output_dir)
    args = argparse.Namespace(
        url="fixture:video",
        kind=kind,
        quality=quality,
        max_duration=10,
        max_file_bytes=1024 * 1024,
        js_runtime="node",
        ffmpeg_location=media_tools[2],
    )
    assert download(args) == 0
    output = output_dir / f"media.{kind}"
    assert output.is_file()
    result = subprocess.run(
        [media_tools[1], "-v", "error", "-show_streams", "-of", "json", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    streams = json.loads(result.stdout)["streams"]
    assert codec in {stream["codec_name"] for stream in streams}
    if kind == "mp3":
        assert all(stream["codec_type"] == "audio" for stream in streams)
    assert '"event": "complete"' in capsys.readouterr().out
