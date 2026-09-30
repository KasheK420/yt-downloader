from urllib.error import HTTPError

import pytest

from app.sources import SourceError, extract_video, resolve_url


class RedirectOpener:
    def __init__(self, redirects):
        self.redirects = redirects
        self.calls = []

    def open(self, request, timeout):
        self.calls.append(request.full_url)
        target = self.redirects[request.full_url]
        raise HTTPError(request.full_url, 302, "Found", {"Location": target}, None)


def test_resolves_short_link_without_contacting_final_video(monkeypatch):
    opener = RedirectOpener(
        {
            "https://fb.watch/abc/": "https://www.facebook.com/share/v/xyz/?tracking=yes",
            "https://www.facebook.com/share/v/xyz/": "/reel/123456789/?tracking=yes",
        }
    )
    monkeypatch.setattr("app.sources.build_opener", lambda *args: opener)
    assert resolve_url("https://fb.watch/abc/") == "https://www.facebook.com/reel/123456789/"
    assert len(opener.calls) == 2


@pytest.mark.parametrize(
    "destination",
    [
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data/",
        "https://facebook.com.evil.test/reel/123",
        "https://user:pass@facebook.com/reel/123",
        "https://facebook.com/flx/warn/?u=http://localhost/",
        "https://www.facebook.com/login/",
        "https://www.instagram.com/reel/abc/",
    ],
)
def test_never_requests_unapproved_redirect_destination(monkeypatch, destination):
    opener = RedirectOpener({"https://fb.watch/abc/": destination})
    monkeypatch.setattr("app.sources.build_opener", lambda *args: opener)
    with pytest.raises(SourceError, match="link_unresolved"):
        resolve_url("https://fb.watch/abc/")
    assert opener.calls == ["https://fb.watch/abc/"]


def test_redirect_loop_is_bounded(monkeypatch):
    opener = RedirectOpener({"https://fb.watch/abc/": "/abc/"})
    monkeypatch.setattr("app.sources.build_opener", lambda *args: opener)
    with pytest.raises(SourceError, match="link_unresolved"):
        resolve_url("https://fb.watch/abc/")
    assert len(opener.calls) <= 5


def test_direct_video_does_not_use_redirect_resolver(monkeypatch):
    opener = RedirectOpener({})
    monkeypatch.setattr("app.sources.build_opener", lambda *args: opener)
    url = "https://www.instagram.com/reel/Abc_123/"
    assert resolve_url(url) == url
    assert opener.calls == []


def test_instagram_share_keeps_its_own_provider(monkeypatch):
    opener = RedirectOpener(
        {
            "https://www.instagram.com/share/reel/abc/": "/reel/Abc_123/?igsh=tracking",
        }
    )
    monkeypatch.setattr("app.sources.build_opener", lambda *args: opener)
    assert (
        resolve_url("https://www.instagram.com/share/reel/abc/")
        == "https://www.instagram.com/reel/Abc_123/"
    )


class Extractor:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    def extract_info(self, url, **options):
        self.calls.append((url, options))
        return next(self.results)


@pytest.mark.parametrize("result_type", ["playlist", "multi_video", "compat_list"])
def test_collections_are_rejected_before_processing_entries(result_type):
    def entries():
        pytest.fail("Collection entries must not be evaluated")
        yield

    downloader = Extractor([{"_type": result_type, "entries": entries()}])
    with pytest.raises(SourceError, match="playlist_unsupported"):
        extract_video(downloader, "https://www.instagram.com/p/Abc_123/")
    assert downloader.calls[0][1] == {"download": False, "process": False, "ie_key": "Instagram"}


def test_reel_delegates_only_to_an_approved_facebook_video():
    result = {"id": "123456789", "title": "Video", "formats": []}
    downloader = Extractor(
        [
            {
                "_type": "url",
                "url": "https://m.facebook.com/watch/?v=123456789&_rdr",
                "ie_key": "Generic",
            },
            result,
        ]
    )
    assert extract_video(downloader, "https://www.facebook.com/reel/123456789/") == result
    assert [call[1]["ie_key"] for call in downloader.calls] == ["FacebookReel", "Facebook"]
    assert downloader.calls[1][0] == "https://www.facebook.com/watch/?v=123456789"


@pytest.mark.parametrize(
    "target",
    [
        "http://127.0.0.1/video",
        "https://www.instagram.com/reel/abc/",
        "https://www.instagram.com/share/reel/abc/",
    ],
)
def test_extractor_cannot_delegate_to_another_provider(target, monkeypatch):
    opener = RedirectOpener({})
    monkeypatch.setattr("app.sources.build_opener", lambda *args: opener)
    downloader = Extractor([{"_type": "url", "url": target}])
    with pytest.raises(SourceError, match="provider_error"):
        extract_video(downloader, "https://www.facebook.com/reel/123/")
    assert len(downloader.calls) == 1
    assert opener.calls == []
