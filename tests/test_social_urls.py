import pytest

from app.urls import normalize_url, provider_for


@pytest.mark.parametrize(
    "url,expected,provider",
    [
        (
            "https://m.facebook.com/watch/?v=123456789&ref=share",
            "https://www.facebook.com/watch/?v=123456789",
            "facebook",
        ),
        (
            "https://www.facebook.com/video.php?v=123456789",
            "https://www.facebook.com/watch/?v=123456789",
            "facebook",
        ),
        (
            "https://facebook.com/Example/videos/123456789/",
            "https://www.facebook.com/watch/?v=123456789",
            "facebook",
        ),
        (
            "https://www.facebook.com/Example/videos/a-video-title/123456789/?foo=bar",
            "https://www.facebook.com/watch/?v=123456789",
            "facebook",
        ),
        (
            "https://www.facebook.com/reel/123456789/?mibextid=abc",
            "https://www.facebook.com/reel/123456789/",
            "facebook",
        ),
        ("https://fb.watch/Abc_123-x/?tracking=yes", "https://fb.watch/Abc_123-x/", "facebook"),
        (
            "https://m.facebook.com/share/v/1AbCdEfGh/?mibextid=abc",
            "https://www.facebook.com/share/v/1AbCdEfGh/",
            "facebook",
        ),
        (
            "https://facebook.com/share/r/1AbCdEfGh/",
            "https://www.facebook.com/share/r/1AbCdEfGh/",
            "facebook",
        ),
        (
            "https://instagram.com/reel/Abc_123-x/?igsh=tracking",
            "https://www.instagram.com/reel/Abc_123-x/",
            "instagram",
        ),
        (
            "https://www.instagram.com/reels/Abc_123-x/",
            "https://www.instagram.com/reel/Abc_123-x/",
            "instagram",
        ),
        (
            "https://www.instagram.com/user.name/reel/Abc_123-x/",
            "https://www.instagram.com/reel/Abc_123-x/",
            "instagram",
        ),
        (
            "https://www.instagram.com/p/Abc_123-x/?img_index=2",
            "https://www.instagram.com/p/Abc_123-x/",
            "instagram",
        ),
        (
            "https://www.instagram.com/tv/Abc_123-x/",
            "https://www.instagram.com/tv/Abc_123-x/",
            "instagram",
        ),
        (
            "https://www.instagram.com/share/reel/Abc_123-x/",
            "https://www.instagram.com/share/reel/Abc_123-x/",
            "instagram",
        ),
        (
            "https://www.instagram.com/share/Abc_123-x/",
            "https://www.instagram.com/share/Abc_123-x/",
            "instagram",
        ),
    ],
)
def test_normalizes_supported_social_video_links(url, expected, provider):
    assert normalize_url(url) == expected
    assert normalize_url(expected) == expected
    assert provider_for(expected) == provider


@pytest.mark.parametrize(
    "url",
    [
        "https://facebook.com/Example/",
        "https://facebook.com/watch/",
        "https://facebook.com/watch?v=123&v=456",
        "https://facebook.com/watch?v=%0A123",
        "https://facebook.com/reel/123/extra",
        "https://facebook.com/share/p/abc/",
        "https://facebook.com/share/v/../abc/",
        "https://facebook.com/flx/warn/?u=http://127.0.0.1/",
        "https://l.facebook.com/l.php?u=http://127.0.0.1/",
        "https://facebook.com.evil.test/reel/123",
        "https://user@facebook.com/reel/123",
        "https://facebook.com:444/reel/123",
        "https://fb.watch/abc/extra",
        "https://instagram.com/a_profile/",
        "https://instagram.com/stories/a_profile/123/",
        "https://instagram.com/explore/tags/videos/",
        "https://instagram.com/reels/audio/123/",
        "https://instagram.com/p/abc%2Fdef/",
        "https://instagram.com/p/abc/extra",
        "https://instagram.com/share/p/abc/",
        "https://instagram.com/share/reel/abc/extra",
        "https://instagram.com/accounts/login/",
        "https://instagram.com.evil.test/reel/abc/",
        "https://instagram.com\\@127.0.0.1/reel/abc/",
        "https://127.0.0.1/reel/abc/",
    ],
)
def test_rejects_collections_redirectors_and_ambiguous_social_links(url):
    with pytest.raises(ValueError):
        normalize_url(url)
