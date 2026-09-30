"""Strict input boundary; provider code never receives the user's original URL."""

import re
from urllib.parse import parse_qs, urlsplit

VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")
HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
FACEBOOK_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com", "mbasic.facebook.com"}
INSTAGRAM_HOSTS = {"instagram.com", "www.instagram.com"}
TOKEN = r"[A-Za-z0-9_-]{1,64}"
NUMBER = r"[0-9]{1,30}"


def normalize_url(value: str) -> str:
    value = value.strip()
    if not value or len(value) > 2048 or re.search(r"[\x00-\x20\x7f\\]", value):
        raise ValueError("Enter a valid video URL.")
    parts = urlsplit(value)
    if (
        parts.scheme not in {"http", "https"}
        or parts.username is not None
        or parts.password is not None
        or parts.port not in {None, 443 if parts.scheme == "https" else 80}
    ):
        raise ValueError("Unsupported URL.")
    if parts.hostname == "fb.watch":
        if match := re.fullmatch(rf"/({TOKEN})/?", parts.path):
            return f"https://fb.watch/{match[1]}/"
    elif parts.hostname in FACEBOOK_HOSTS:
        if parts.path in {"/watch", "/watch/", "/video.php", "/video/video.php"}:
            ids = parse_qs(parts.query, keep_blank_values=True).get("v", [])
            if len(ids) == 1 and re.fullmatch(NUMBER, ids[0]):
                return f"https://www.facebook.com/watch/?v={ids[0]}"
        if match := re.fullmatch(rf"/reel/({NUMBER})/?", parts.path):
            return f"https://www.facebook.com/reel/{match[1]}/"
        if match := re.fullmatch(
            rf"/[A-Za-z0-9._-]+/videos/(?:[A-Za-z0-9_-]+/)?({NUMBER})/?", parts.path
        ):
            return f"https://www.facebook.com/watch/?v={match[1]}"
        if match := re.fullmatch(rf"/share/([vr])/({TOKEN})/?", parts.path):
            return f"https://www.facebook.com/share/{match[1]}/{match[2]}/"
    elif parts.hostname in INSTAGRAM_HOSTS:
        if match := re.fullmatch(rf"/share/(reel/)?({TOKEN})/?", parts.path):
            return f"https://www.instagram.com/share/{match[1] or ''}{match[2]}/"
        if match := re.fullmatch(
            rf"/(?!share/)(?:[A-Za-z0-9._]+/)?(p|tv|reels?)/({TOKEN})/?", parts.path
        ):
            kind = "reel" if match[1] == "reels" else match[1]
            return f"https://www.instagram.com/{kind}/{match[2]}/"
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
        raise ValueError("Use a link to one YouTube, Facebook, or Instagram video.")
    return f"https://www.youtube.com/watch?v={video_id}"


def provider_for(value: str) -> str:
    host = urlsplit(normalize_url(value)).hostname
    if host in FACEBOOK_HOSTS or host == "fb.watch":
        return "facebook"
    if host in INSTAGRAM_HOSTS:
        return "instagram"
    return "youtube"
