from concurrent.futures import ThreadPoolExecutor

import pytest

from app.config import Settings
from app.store import LimitExceeded, Store

URL = "https://www.youtube.com/watch?v=BaW_jenozKc"


def test_persists_owned_jobs_and_hides_foreign_jobs(settings: Settings) -> None:
    store = Store(settings)
    job = store.create("alice", "client", URL, "mp4", 720)
    assert job.get("state") == "queued"
    assert Store(settings).get(job["id"], "alice")["url"] == URL
    assert store.get(job["id"], "bob") is None
    assert store.list_jobs("bob") == []


def test_per_session_limit_is_atomic_under_concurrent_requests(settings: Settings) -> None:
    store = Store(settings)

    def submit(_: int) -> bool:
        try:
            store.create("alice", "client", URL, "mp3", 192)
            return True
        except LimitExceeded:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(submit, range(12))) == 2


def test_new_session_does_not_bypass_ip_rate_limit(settings: Settings) -> None:
    settings.rate_limit = 2
    store = Store(settings)
    store.create("alice", "same-ip", URL, "mp3", 192)
    store.create("bob", "same-ip", URL, "mp3", 192)
    with pytest.raises(LimitExceeded, match="rate_limit"):
        store.create("charlie", "same-ip", URL, "mp3", 192)


def test_global_queue_limit_cannot_be_bypassed_by_new_visitors(settings: Settings) -> None:
    settings.max_queue = 1
    store = Store(settings)
    store.create("alice", "ip1", URL, "mp4", 720)
    with pytest.raises(LimitExceeded, match="queue_full"):
        store.create("bob", "ip2", URL, "mp3", 192)


def test_interrupted_jobs_fail_on_recovery_and_terminal_jobs_expire(settings: Settings) -> None:
    store = Store(settings)
    job = store.create("alice", "client", URL, "mp4", 720)
    assert job.get("state") == "queued"
    assert store.claim()["id"] == job["id"]
    store.recover()
    recovered = store.get(job["id"], "alice")
    assert recovered["state"] == "failed"
    assert recovered["error"] == "interrupted"
    store.expire(now=recovered["expires_at"] + 1)
    assert store.get(job["id"], "alice") is None
