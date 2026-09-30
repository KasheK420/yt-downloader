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
from app.media import fit_video, inspect_media
from app.sources import SourceError
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


def generate_video(path, media_tools, encoder="libx264", pixels="yuv420p", audio="aac"):
    command = [
        media_tools[0],
        "-v",
        "error",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=s=160x90:r=12",
    ]
    if audio:
        command += ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000"]
    command += ["-t", "0.5", "-c:v", encoder, "-pix_fmt", pixels]
    if encoder == "libaom-av1":
        command += ["-cpu-used", "8", "-row-mt", "1"]
    if encoder == "libx265":
        command += ["-x265-params", "log-level=error:pools=1"]
    if audio:
        command += ["-c:a", audio]
    subprocess.run([*command, str(path)], check=True, capture_output=True, timeout=30)


def video_packets(path, media_tools):
    result = subprocess.run(
        [
            media_tools[1],
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_packets",
            "-show_entries",
            "packet=pos,size,data_hash",
            "-show_data_hash",
            "sha256",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)["packets"]


@pytest.mark.parametrize(
    "encoder,pixels,audio",
    [
        ("libaom-av1", "yuv420p", "aac"),
        ("libx265", "yuv420p", "aac"),
        ("libx264", "yuv444p", "aac"),
        ("libx264", "yuv420p", "libopus"),
        ("libx264", "yuv420p", "aac"),
        ("libx264", "yuv420p", None),
    ],
)
def test_small_mp4_is_playable_h264_aac_with_faststart(
    tmp_path, media_tools, encoder, pixels, audio
):
    path = tmp_path / "media.mp4"
    generate_video(path, media_tools, encoder, pixels, audio)
    original_packets = video_packets(path, media_tools)
    fit_video(path, 720, 10, media_tools[2])
    streams = inspect_media(path, 10, media_tools[2])["streams"]
    video = next(stream for stream in streams if stream["codec_type"] == "video")
    assert (video["codec_name"], video["pix_fmt"]) == ("h264", "yuv420p")
    assert (video["width"], video["height"]) == (160, 90)
    sounds = [stream for stream in streams if stream["codec_type"] == "audio"]
    assert bool(sounds) == bool(audio)
    assert all(stream["codec_name"] == "aac" for stream in sounds)
    if encoder == "libx264" and pixels == "yuv420p":
        assert [p["data_hash"] for p in video_packets(path, media_tools)] == [
            p["data_hash"] for p in original_packets
        ]  # Compatible video packets must not incur another lossy encoding.
    data = path.read_bytes()
    boxes, offset = [], 0
    while offset + 8 <= len(data):
        size = int.from_bytes(data[offset : offset + 4], "big")
        boxes.append(data[offset + 4 : offset + 8])
        if size == 1:
            size = int.from_bytes(data[offset + 8 : offset + 16], "big")
        if size == 0:
            break
        offset += size
    assert boxes.index(b"moov") < boxes.index(b"mdat")
    subprocess.run(
        [media_tools[0], "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"],
        check=True,
        capture_output=True,
        timeout=30,
    )


def test_mp4_with_readable_metadata_but_broken_frames_is_rejected(tmp_path, media_tools):
    path = tmp_path / "media.mp4"
    generate_video(path, media_tools)
    packet = video_packets(path, media_tools)[-1]
    data = bytearray(path.read_bytes())
    start, size = int(packet["pos"]), int(packet["size"])
    data[start + 4 : start + size] = b"\0" * (size - 4)
    path.write_bytes(data)
    assert inspect_media(path, 10, media_tools[2])["format"]["duration"]
    with pytest.raises(SourceError, match="processing_error"):
        fit_video(path, 720, 10, media_tools[2])
    assert path.read_bytes() == data


@pytest.fixture
def media_server(tmp_path: Path, media_tools, request):
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
            f"color=c=blue:s={request.param}:r=12",
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
        width, height = map(int, request.param.split("x"))
        yield f"http://127.0.0.1:{server.server_port}/sample.mp4", width, height
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("media_server", ["160x90", "450x800", "800x450"], indirect=True)
@pytest.mark.parametrize("kind,quality,codec", [("mp3", 192, "mp3"), ("mp4", 360, "h264")])
@pytest.mark.parametrize(
    "duration,limit,error", [(1, 10, None), (None, 10, None), (None, 0.5, "duration_limit")]
)
def test_worker_converts_real_synthetic_media(
    tmp_path,
    media_tools,
    media_server,
    monkeypatch,
    capsys,
    kind,
    quality,
    codec,
    duration,
    limit,
    error,
):
    original = yt_dlp.YoutubeDL

    class YoutubeIE(InfoExtractor):
        _VALID_URL = r"https://www.youtube.com/watch\?v=(?P<id>BaW_jenozKc)"

        def _real_extract(self, url):
            return {
                "id": "video",
                "title": "Synthetic test",
                "duration": duration,
                "url": media_server[0],
                "ext": "mp4",
                "width": media_server[1],
                "height": media_server[2],
                "vcodec": "h264",
                "acodec": "aac",
            }

    def fixture_downloader(options):
        downloader = original(options, auto_init=False)
        downloader.add_info_extractor(YoutubeIE())
        return downloader

    monkeypatch.setattr(yt_dlp, "YoutubeDL", fixture_downloader)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.chdir(output_dir)
    args = argparse.Namespace(
        url="https://www.youtube.com/watch?v=BaW_jenozKc",
        kind=kind,
        quality=quality,
        max_duration=limit,
        max_file_bytes=1024 * 1024,
        js_runtime="node",
        ffmpeg_location=media_tools[2],
    )
    if error:
        assert download(args) == 1
        events = capsys.readouterr().out
        assert f'"code": "{error}"' in events
        assert '"event": "complete"' not in events
        return
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
    else:
        video = next(stream for stream in streams if stream["codec_type"] == "video")
        assert min(video["width"], video["height"]) <= quality
        assert video["width"] <= media_server[1] and video["height"] <= media_server[2]
        assert (video["height"] > video["width"]) == (media_server[2] > media_server[1])
        assert any(stream["codec_type"] == "audio" for stream in streams)
    assert '"event": "complete"' in capsys.readouterr().out


@pytest.mark.parametrize(
    "metadata,expected",
    [
        ({"duration": 7201}, "duration_limit"),
        ({"duration": float("nan")}, "duration_limit"),
        ({"duration": float("inf")}, "duration_limit"),
        ({"duration": -1}, "duration_limit"),
        ({"duration": 30, "is_live": True}, "live_unsupported"),
        ({"duration": 30, "acodec": "none"}, "audio_unavailable"),
    ],
)
def test_worker_rejects_ineligible_media_before_download(
    tmp_path, monkeypatch, capsys, metadata, expected
):
    original = yt_dlp.YoutubeDL

    class YoutubeIE(InfoExtractor):
        _VALID_URL = r"https://www.youtube.com/watch\?v=(?P<id>BaW_jenozKc)"

        def _real_extract(self, url):
            return {
                "id": "video",
                "title": "Rejected fixture",
                "url": "http://127.0.0.1:1/must-not-be-fetched.mp4",
                "ext": "mp4",
                "height": 90,
                **metadata,
            }

    def fixture_downloader(options):
        downloader = original(options, auto_init=False)
        downloader.add_info_extractor(YoutubeIE())
        return downloader

    monkeypatch.setattr(yt_dlp, "YoutubeDL", fixture_downloader)
    monkeypatch.chdir(tmp_path)
    args = argparse.Namespace(
        url="https://www.youtube.com/watch?v=BaW_jenozKc",
        kind="mp3" if expected == "audio_unavailable" else "mp4",
        quality=192 if expected == "audio_unavailable" else 720,
        max_duration=7200,
        max_file_bytes=1024 * 1024,
        js_runtime="node",
        ffmpeg_location=None,
    )
    assert download(args) == 1
    assert f'"code": "{expected}"' in capsys.readouterr().out
    assert not list(tmp_path.iterdir())
