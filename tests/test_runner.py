import asyncio
import sys
import time

import pytest

from app.config import Settings
from app.runner import Runner
from app.store import Store

URL = "https://www.youtube.com/watch?v=BaW_jenozKc"


async def wait_state(store: Store, job_id: str, state: str) -> dict:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        job = store.get(job_id, "alice")
        if job and job["state"] == state:
            return job
        await asyncio.sleep(0.05)
    pytest.fail(f"Expected {state}, got {store.get(job_id, 'alice')}")


@pytest.mark.asyncio
async def test_runner_processes_real_child_and_persists_output(settings: Settings, monkeypatch):
    store = Store(settings)
    runner = Runner(store, settings)
    await runner.start()
    try:
        assert getattr(runner, "task", None) is not None
        script = (
            "import json,pathlib; "
            "pathlib.Path('media.mp4').write_bytes(b'video'); "
            "print(json.dumps({'event':'metadata','title':'Fixture'})); "
            "print(json.dumps({'event':'complete'}))"
        )
        monkeypatch.setattr(runner, "command", lambda _: [sys.executable, "-c", script])
        job = store.create("alice", "ip", URL, "mp4", 720)
        result = await wait_state(store, job["id"], "complete")
        assert result["title"] == "Fixture"
        assert result["file_bytes"] == 5
    finally:
        await runner.stop()


@pytest.mark.asyncio
async def test_timeout_kills_child_and_removes_partial_output(settings: Settings, monkeypatch):
    settings.job_timeout_seconds = 1
    store = Store(settings)
    runner = Runner(store, settings)
    await runner.start()
    try:
        assert getattr(runner, "task", None) is not None
        script = "import pathlib,time; pathlib.Path('media.part').write_bytes(b'x'); time.sleep(30)"
        monkeypatch.setattr(runner, "command", lambda _: [sys.executable, "-c", script])
        job = store.create("alice", "ip", URL, "mp4", 720)
        result = await wait_state(store, job["id"], "failed")
        assert result["error"] == "timeout"
        assert not (settings.data_dir / "media" / job["id"]).exists()
        assert runner.process is None
    finally:
        await runner.stop()


@pytest.mark.asyncio
async def test_cancel_kills_active_process(settings: Settings, monkeypatch):
    store = Store(settings)
    runner = Runner(store, settings)
    await runner.start()
    try:
        assert getattr(runner, "task", None) is not None
        monkeypatch.setattr(
            runner, "command", lambda _: [sys.executable, "-c", "import time; time.sleep(30)"]
        )
        job = store.create("alice", "ip", URL, "mp4", 720)
        await wait_state(store, job["id"], "downloading")
        await runner.cancel(job["id"])
        assert store.get(job["id"], "alice")["state"] == "cancelled"
        assert not (settings.data_dir / "media" / job["id"]).exists()
    finally:
        await runner.stop()


@pytest.mark.asyncio
async def test_oversized_process_output_is_rejected(settings: Settings, monkeypatch):
    settings.max_file_bytes = 32
    settings.max_job_bytes = 64
    store = Store(settings)
    runner = Runner(store, settings)
    await runner.start()
    try:
        assert getattr(runner, "task", None) is not None
        script = (
            "import pathlib,time; pathlib.Path('media.mp4').write_bytes(b'x'*100); time.sleep(30)"
        )
        monkeypatch.setattr(runner, "command", lambda _: [sys.executable, "-c", script])
        job = store.create("alice", "ip", URL, "mp4", 720)
        result = await wait_state(store, job["id"], "failed")
        assert result["error"] == "size_limit"
        assert not (settings.data_dir / "media" / job["id"]).exists()
    finally:
        await runner.stop()


@pytest.mark.asyncio
async def test_restart_cleans_orphans_and_preserves_completed_media(settings: Settings):
    store = Store(settings)
    complete = store.create("alice", "ip", URL, "mp3", 192)
    store.update(complete["id"], state="complete")
    unfinished = store.create("alice", "ip", URL, "mp4", 720)
    for job_id in (complete["id"], unfinished["id"], "a" * 32):
        folder = settings.data_dir / "media" / job_id
        folder.mkdir(parents=True)
        (folder / "media.mp3").write_bytes(b"data")
    runner = Runner(store, settings)
    await runner.start()
    try:
        assert store.get(unfinished["id"], "alice")["state"] == "failed"
        assert (settings.data_dir / "media" / complete["id"]).exists()
        assert not (settings.data_dir / "media" / unfinished["id"]).exists()
        assert not (settings.data_dir / "media" / ("a" * 32)).exists()
    finally:
        await runner.stop()


@pytest.mark.parametrize(
    "error", ["playlist_unsupported", "link_unresolved", "audio_unavailable", "processing_error"]
)
async def test_worker_failures_remain_actionable_and_remove_partial_files(
    settings, monkeypatch, error
):
    store = Store(settings)
    runner = Runner(store, settings)
    script = (
        "import json,pathlib; pathlib.Path('media.part').write_bytes(b'partial'); "
        f"print(json.dumps({{'event':'error','code':{error!r}}})); raise SystemExit(1)"
    )
    monkeypatch.setattr(runner, "command", lambda _: [sys.executable, "-c", script])
    await runner.start()
    try:
        job = store.create("alice", "ip", "https://www.instagram.com/reel/Abc_123/", "mp4", 720)
        result = await wait_state(store, job["id"], "failed")
        assert result["error"] == error
        assert not runner.files.folder(job["id"]).exists()
    finally:
        await runner.stop()


async def test_worker_does_not_inherit_social_login_credentials(settings, monkeypatch):
    monkeypatch.setenv("YTD_GOOGLE_CLIENT_SECRET", "synthetic-secret")
    monkeypatch.setenv("YTD_FACEBOOK_CLIENT_SECRET", "synthetic-secret")
    monkeypatch.setenv("UNRELATED_PRIVATE_TOKEN", "synthetic-secret")
    store = Store(settings)
    runner = Runner(store, settings)
    script = (
        "import os,pathlib; "
        "assert not any(k in os.environ for k in "
        "['YTD_GOOGLE_CLIENT_SECRET','YTD_FACEBOOK_CLIENT_SECRET','UNRELATED_PRIVATE_TOKEN']); "
        "pathlib.Path('media.mp4').write_bytes(b'media')"
    )
    monkeypatch.setattr(runner, "command", lambda _: [sys.executable, "-c", script])
    await runner.start()
    try:
        job = store.create("alice", "ip", URL, "mp4", 720)
        await wait_state(store, job["id"], "complete")
    finally:
        await runner.stop()
