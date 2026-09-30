"""Resolve approved share links and enforce a single-video extraction result."""

from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.urls import normalize_url, provider_for


class SourceError(Exception):
    """A stable, non-sensitive error code safe for a job response."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


def is_share_url(url: str) -> bool:
    parts = urlsplit(url)
    return parts.hostname == "fb.watch" or parts.path.startswith("/share/")


def resolve_url(value: str) -> str:
    url = normalize_url(value)
    provider = provider_for(url)
    opener = build_opener(NoRedirect())
    visited: set[str] = set()
    for _ in range(5):
        if not is_share_url(url):
            return url
        if url in visited:
            break
        visited.add(url)
        try:
            # Do not fetch bodies or automatically follow Location headers. Each destination
            # must pass the exact video/short-link boundary before the next network request.
            with opener.open(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=15):
                break  # A login page or a non-redirect share page is not a resolved video.
        except HTTPError as exc:
            try:
                if exc.code not in {301, 302, 303, 307, 308} or not exc.headers.get("Location"):
                    break
                target = normalize_url(urljoin(url, exc.headers["Location"]))
                if provider_for(target) != provider:
                    break
                url = target
            except ValueError:
                break
            finally:
                exc.close()
        except (URLError, TimeoutError, OSError):
            break
    # Allow the last permitted redirect to end at a direct video.
    if not is_share_url(url):
        return url
    raise SourceError("link_unresolved")


def extract_video(downloader: Any, value: str) -> dict[str, Any]:
    url = resolve_url(value)
    provider = provider_for(url)
    for _ in range(5):
        key = {"youtube": "Youtube", "facebook": "Facebook", "instagram": "Instagram"}[provider]
        if provider == "facebook" and urlsplit(url).path.startswith("/reel/"):
            key = "FacebookReel"
        # process=False is essential: noplaylist alone does not reject Instagram carousels.
        info = downloader.extract_info(url, download=False, process=False, ie_key=key)
        if not isinstance(info, dict):
            raise SourceError("provider_error")
        result_type = info.get("_type", "video")
        if result_type == "video":
            return info
        if result_type not in {"url", "url_transparent"}:
            raise SourceError("playlist_unsupported")
        try:
            target = info.get("url")
            if not isinstance(target, str):
                raise ValueError("Invalid extraction target")
            target = normalize_url(target)
            if provider_for(target) != provider:
                raise ValueError("Cross-provider extraction")
            url = resolve_url(target)
        except ValueError as exc:
            raise SourceError("provider_error") from exc
    raise SourceError("provider_error")
