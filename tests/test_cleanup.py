import asyncio
import time

from app.files import MediaFiles, MediaResponse
from app.runner import Runner
from app.store import Store

URL = "https://www.youtube.com/watch?v=BaW_jenozKc"


def completed(store, files):
    job = store.create("alice", "ip", URL, "mp4", 720)
    store.update(job["id"], state="complete")
    files.folder(job["id"]).mkdir()
    files.output(job["id"], "mp4").write_bytes(b"media")
    store.remove(job["id"])
    return job["id"]


def test_removal_hides_job_but_keeps_metadata_until_files_are_deleted(settings, monkeypatch):
    store = Store(settings)
    runner = Runner(store, settings)
    job_id = completed(store, runner.files)
    remove = runner.files.remove
    monkeypatch.setattr(runner.files, "remove", lambda _: (_ for _ in ()).throw(PermissionError()))
    runner.cleanup()
    assert store.get(job_id, "alice") is None
    assert job_id in store.cleanup_ids()
    assert runner.files.output(job_id, "mp4").exists()
    monkeypatch.setattr(runner.files, "remove", remove)
    runner.cleanup()
    assert job_id not in store.cleanup_ids()
    assert not runner.files.folder(job_id).exists()


def test_stream_lease_defers_removal_until_all_readers_finish(settings):
    store = Store(settings)
    runner = Runner(store, settings)
    job_id = completed(store, runner.files)
    with runner.files.hold(job_id), runner.files.hold(job_id):
        runner.cleanup()
        assert runner.files.output(job_id, "mp4").exists()
        assert job_id in store.cleanup_ids()
    runner.cleanup()
    assert not runner.files.folder(job_id).exists()
    assert job_id not in store.cleanup_ids()


async def test_cleanup_runs_while_a_download_is_busy(settings, monkeypatch):
    settings.cleanup_interval_seconds = 0.05
    store = Store(settings)
    runner = Runner(store, settings)
    working = asyncio.Event()

    async def slow(_):
        working.set()
        await asyncio.sleep(30)

    monkeypatch.setattr(runner, "_execute", slow)
    await runner.start()
    try:
        store.create("alice", "ip", URL, "mp4", 720)
        await asyncio.wait_for(working.wait(), timeout=3)
        job_id = completed(store, runner.files)
        deadline = time.monotonic() + 3
        while runner.files.folder(job_id).exists() and time.monotonic() < deadline:
            await asyncio.sleep(0.05)
        assert not runner.files.folder(job_id).exists()
        assert runner.current_task and not runner.current_task.done()
    finally:
        await runner.stop()


async def test_cancel_succeeds_even_if_partial_file_is_temporarily_locked(settings, monkeypatch):
    store = Store(settings)
    runner = Runner(store, settings)
    job = store.create("alice", "ip", URL, "mp4", 720)
    monkeypatch.setattr(MediaFiles, "remove", lambda *_: (_ for _ in ()).throw(PermissionError()))
    await runner.cancel(job["id"])
    assert store.get(job["id"], "alice")["state"] == "cancelled"


async def test_http_transfer_holds_file_until_last_body_chunk(settings):
    store = Store(settings)
    runner = Runner(store, settings)
    job_id = completed(store, runner.files)
    body = b"media" * 20000
    runner.files.output(job_id, "mp4").write_bytes(body)
    response = MediaResponse(runner.files, job_id, "mp4", "example.mp4", False)
    delivered = bytearray()

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        if message["type"] == "http.response.body":
            runner.cleanup()
            assert runner.files.output(job_id, "mp4").exists()
            delivered.extend(message["body"])

    await response(
        {"type": "http", "method": "GET", "headers": [], "extensions": {}}, receive, send
    )
    assert delivered == body
    runner.cleanup()
    assert not runner.files.folder(job_id).exists()
