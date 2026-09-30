from concurrent.futures import ThreadPoolExecutor

import pytest

from app.policy import policy_for
from app.store import LimitExceeded, Store

URL = "https://www.youtube.com/watch?v=BaW_jenozKc"


def test_guest_budget_survives_cookie_reset_and_removed_history(settings):
    settings.public_mode = True
    settings.guest_downloads = 2
    store = Store(settings)
    policy = policy_for(settings, authenticated=False)
    for owner in ("one", "two"):
        job = store.create(owner, "same-ip", URL, "mp4", 720, policy=policy)
        store.update(job["id"], state="failed")
        store.remove(job["id"])
        store.purge(job["id"])
    with pytest.raises(LimitExceeded, match="quota_exhausted"):
        store.create("fresh-cookie", "same-ip", URL, "mp4", 720, policy=policy)
    assert store.budget("fresh-cookie", "same-ip", policy)["remaining"] == 0


def test_free_account_budget_follows_account_across_ips_and_is_atomic(settings):
    settings.public_mode = True
    settings.free_downloads = 2
    store = Store(settings)
    policy = policy_for(settings, authenticated=True)

    def submit(i):
        try:
            job = store.create("account", f"ip-{i}", URL, "mp4", 1080, policy=policy)
            store.update(job["id"], state="complete")
            return True
        except LimitExceeded:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(submit, range(8))) == 2
    with pytest.raises(LimitExceeded, match="quota_exhausted"):
        store.create("account", "new-ip", URL, "mp4", 1080, policy=policy)


def test_idempotent_submission_charges_once_and_rejects_key_reuse(settings):
    store = Store(settings)
    first = store.create("alice", "ip", URL, "mp4", 720, request_key="unique")
    second = store.create("alice", "ip", URL, "mp4", 720, request_key="unique")
    assert first["id"] == second["id"]
    assert len(store.list_jobs("alice")) == 1
    with pytest.raises(ValueError, match="idempotency_conflict"):
        store.create("alice", "ip", URL, "mp3", 192, request_key="unique")


def test_job_keeps_effective_limits_after_login_or_config_change(settings):
    settings.public_mode = True
    store = Store(settings)
    job = store.create("guest", "ip", URL, "mp4", 720, policy=policy_for(settings, False))
    assert job["max_duration_seconds"] == 1800
    assert job["max_file_bytes"] == 250 * 1024**2


def test_guest_limits_never_exceed_operator_global_ceilings(settings):
    settings.public_mode = True
    settings.max_file_bytes = 32
    settings.max_duration_seconds = 10
    policy = policy_for(settings, False)
    assert policy.max_file_bytes == 32
    assert policy.max_duration_seconds == 10
