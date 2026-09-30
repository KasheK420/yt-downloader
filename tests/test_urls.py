import pytest

from app.urls import normalize_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=BaW_jenozKc",
        "https://youtube.com/watch?v=BaW_jenozKc&list=example&t=10",
        "https://youtu.be/BaW_jenozKc?si=tracking",
        "https://m.youtube.com/shorts/BaW_jenozKc",
        "https://www.youtube.com/live/BaW_jenozKc",
        "  https://music.youtube.com/watch?v=BaW_jenozKc  ",
    ],
)
def test_canonicalizes_single_video_and_discards_tracking(url: str) -> None:
    assert normalize_url(url) == "https://www.youtube.com/watch?v=BaW_jenozKc"


@pytest.mark.parametrize(
    "url",
    [
        "",
        "file:///etc/passwd",
        "http://127.0.0.1/",
        "https://youtube.com.evil.test/watch?v=BaW_jenozKc",
        "https://youtube.com@evil.test/watch?v=BaW_jenozKc",
        "https://user:pass@youtube.com/watch?v=BaW_jenozKc",
        "https://youtube.com:444/watch?v=BaW_jenozKc",
        "https://youtube.com/playlist?list=anything",
        "https://youtube.com/watch?v=short",
        "https://youtube.com/watch?v=BaW_jenozKc&v=abcdefghijk",
        "https://youtu.be/BaW_jenozKc/extra",
        "https://youtube.com/redirect?q=https://127.0.0.1",
        "https://youtube.com/watch?v=BaW_jenozKc%0A",
        "https://youtube.com\\@127.0.0.1/watch?v=BaW_jenozKc",
        "--exec touch /tmp/injection",
        "https://youtube.com/watch?v=BaW_jenozKc\n&x=1",
    ],
)
def test_rejects_non_video_or_ambiguous_urls(url: str) -> None:
    with pytest.raises(ValueError):
        normalize_url(url)
