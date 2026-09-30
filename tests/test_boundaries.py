import asyncio
from pathlib import Path

import pytest

from app.config import Settings
from app.files import MediaFiles
from app.runner import Runner
from app.security import BodyLimitMiddleware
from app.store import Store


def test_path_traversal_never_reaches_the_filesystem(tmp_path: Path) -> None:
    files = MediaFiles(tmp_path)
    with pytest.raises(ValueError):
        files.remove("../../outside")
    with pytest.raises(ValueError):
        files.output("a" * 32, "../secret")


def test_output_symlink_is_not_served(tmp_path: Path) -> None:
    files = MediaFiles(tmp_path)
    folder = files.folder("a" * 32)
    folder.mkdir()
    secret = tmp_path / "secret"
    secret.write_text("sensitive")
    try:
        (folder / "media.mp3").symlink_to(secret)
    except OSError:
        pytest.skip("Windows developer mode or symlink privilege is required")
    with pytest.raises(ValueError):
        files.output("a" * 32, "mp3")


@pytest.mark.asyncio
async def test_chunked_request_limit_does_not_call_application():
    called = False
    responses = []
    chunks = iter(
        [
            {"type": "http.request", "body": b"x" * 3000, "more_body": True},
            {"type": "http.request", "body": b"x" * 3000, "more_body": False},
        ]
    )

    async def app(scope, receive, send):
        nonlocal called
        called = True

    async def receive():
        return next(chunks)

    async def send(message):
        responses.append(message)

    await BodyLimitMiddleware(app)({"type": "http", "method": "POST"}, receive, send)
    assert responses[0]["status"] == 413
    assert not called


@pytest.mark.asyncio
async def test_expiry_removes_media_and_database_rows(settings: Settings):
    settings.retention_seconds = 1
    settings.cleanup_interval_seconds = 0.1
    store = Store(settings)
    job = store.create("alice", "ip", "https://www.youtube.com/watch?v=BaW_jenozKc", "mp3", 192)
    store.update(job["id"], state="complete")
    files = MediaFiles(settings.data_dir)
    files.folder(job["id"]).mkdir()
    files.output(job["id"], "mp3").write_bytes(b"media")
    runner = Runner(store, settings)
    await runner.start()
    try:
        await asyncio.sleep(1.5)
        assert not files.folder(job["id"]).exists()
        assert store.get(job["id"], "alice") is None
    finally:
        await runner.stop()
