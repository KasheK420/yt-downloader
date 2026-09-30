"""Strict input boundary; provider code never receives the user's original URL."""

import re
from urllib.parse import parse_qs, urlsplit

VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")
HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}


def normalize_url(value: str) -> str:
    value = value.strip()
    if not value or len(value) > 2048 or re.search(r"[\x00-\x20\x7f\\]", value):
        raise ValueError("Enter a valid YouTube video URL.")
    parts = urlsplit(value)
    if (
        parts.scheme not in {"http", "https"}
        or parts.username is not None
        or parts.password is not None
        or parts.port not in {None, 443 if parts.scheme == "https" else 80}
    ):
        raise ValueError("Unsupported URL.")
    video_id = ""
    if parts.hostname == "youtu.be":
        video_id = parts.path.removeprefix("/")
    elif parts.hostname in HOSTS:
        if parts.path == "/watch":
            ids = parse_qs(parts.query, keep_blank_values=True).get("v", [])
            if len(ids) == 1:
                video_id = ids[0]
        else:
            match = re.fullmatch(r"/(?:shorts|live|embed)/([A-Za-z0-9_-]{11})", parts.path)
            if match:
                video_id = match[1]
    if not VIDEO_ID.fullmatch(video_id):
        raise ValueError("Use a link to one YouTube video.")
    return f"https://www.youtube.com/watch?v={video_id}"
