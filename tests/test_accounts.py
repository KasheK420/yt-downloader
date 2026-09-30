import time
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.main import create_app
from app.runner import Runner

HEADERS = {"X-Requested-With": "yt-downloader"}
PAYLOAD = {"url": "https://youtu.be/BaW_jenozKc", "kind": "mp4", "quality": 720}


@pytest.fixture
def auth_client(settings, monkeypatch):
    settings.public_mode = True
    settings.public_origin = "http://localhost"
    settings.google_client_id = "google-test"
    settings.google_client_secret = SecretStr("test-secret")

    async def offline(_):
        pass

    monkeypatch.setattr(Runner, "start", offline)
    monkeypatch.setattr(Runner, "available", lambda _: True)
    monkeypatch.setattr("app.main.runtime_status", lambda _: {"ffmpeg": True})
    app = create_app(settings)

    async def authorize(provider, state, verifier, nonce):
        return f"https://accounts.google.com/test?state={state}"

    async def identity(provider, code, flow):
        return code, "Test account"

    monkeypatch.setattr(app.state.oauth, "authorize", authorize)
    monkeypatch.setattr(app.state.oauth, "identity", identity)
    with TestClient(app, base_url="http://localhost") as client:
        client.get("/api/session")
        yield client


def begin(client):
    result = client.post("/api/auth/google", headers=HEADERS)
    assert result.status_code == 200
    state = parse_qs(urlsplit(result.json()["url"]).query)["state"][0]
    return f"/auth/google/callback?state={state}&code=subject-1"


def login(client):
    callback = begin(client)
    result = client.get(callback, follow_redirects=False)
    assert result.status_code == 303
    assert result.headers["location"] == "/?auth=success"
    return callback


def test_login_rotates_session_transfers_guest_jobs_and_counts_attempts(auth_client):
    client = auth_client
    old = client.cookies.get("ytd_session")
    job = client.post("/api/jobs", json=PAYLOAD, headers=HEADERS).json()
    login(client)
    session = client.get("/api/session").json()
    assert session["account"] == {"name": "Test account", "provider": "google"}
    assert session["tier"] == "free" and session["quota"]["remaining"] == 19
    assert client.cookies.get("ytd_session") != old
    assert client.get(f"/api/jobs/{job['id']}").status_code == 200
    assert client.app.state.accounts.session(old) is None


def test_callback_requires_browser_binding_and_is_one_use(auth_client):
    client = auth_client
    callback = begin(client)
    binding = client.cookies.get("ytd_login")
    client.cookies.delete("ytd_login")
    assert "login_expired" in client.get(callback, follow_redirects=False).headers["location"]
    client.cookies.set("ytd_login", binding)
    assert "success" in client.get(callback, follow_redirects=False).headers["location"]
    assert "login_expired" in client.get(callback, follow_redirects=False).headers["location"]


def test_logout_revokes_session_and_preserves_account_library(auth_client):
    client = auth_client
    login(client)
    old = client.cookies.get("ytd_session")
    job = client.post("/api/jobs", json=PAYLOAD, headers=HEADERS).json()
    assert client.post("/api/logout", headers=HEADERS).status_code == 204
    assert client.app.state.accounts.session(old) is None
    assert client.get("/api/session").json()["account"] is None
    assert client.get(f"/api/jobs/{job['id']}").status_code == 404
    login(client)
    assert client.get(f"/api/jobs/{job['id']}").status_code == 200


def test_delete_account_revokes_all_devices_and_removes_identity_and_media(auth_client):
    client = auth_client
    login(client)
    old = client.cookies.get("ytd_session")
    account = client.app.state.accounts.session(old)
    job = client.post("/api/jobs", json=PAYLOAD, headers=HEADERS).json()
    store, files = client.app.state.store, client.app.state.runner.files
    store.update(job["id"], state="complete")
    files.folder(job["id"]).mkdir()
    files.output(job["id"], "mp4").write_bytes(b"private")
    assert client.delete("/api/account", headers=HEADERS).status_code == 204
    assert not files.folder(job["id"]).exists()
    assert client.app.state.accounts.session(old) is None
    with store._db() as db:
        assert db.execute("SELECT count(*) FROM accounts").fetchone()[0] == 0
        assert (
            db.execute("SELECT count(*) FROM jobs WHERE owner = ?", (account["owner"],)).fetchone()[
                0
            ]
            == 0
        )
        assert db.execute("SELECT count(*) FROM submissions").fetchone()[0] == 1


def test_expired_state_and_cancelled_consent_do_not_create_accounts(auth_client):
    callback = begin(auth_client)
    with auth_client.app.state.store._db() as db:
        db.execute("UPDATE login_flows SET expires_at = ?", (time.time() - 1,))
    assert "login_expired" in auth_client.get(callback, follow_redirects=False).headers["location"]
    callback = begin(auth_client).replace("code=subject-1", "error=access_denied")
    assert (
        "login_cancelled" in auth_client.get(callback, follow_redirects=False).headers["location"]
    )
    assert auth_client.get("/api/session").json()["account"] is None


def test_guest_quality_and_retry_admission_are_enforced(auth_client):
    client = auth_client
    assert (
        client.post("/api/jobs", json={**PAYLOAD, "quality": 1080}, headers=HEADERS).status_code
        == 403
    )
    job = client.post("/api/jobs", json=PAYLOAD, headers=HEADERS).json()
    assert client.post(f"/api/jobs/{job['id']}/retry", headers=HEADERS).status_code == 409
    client.app.state.store.update(job["id"], state="failed")
    retried = client.post(f"/api/jobs/{job['id']}/retry", headers=HEADERS)
    assert retried.status_code == 202 and retried.json()["id"] != job["id"]
    assert "url" not in retried.json()


def test_disabled_provider_and_cross_origin_login_are_rejected(auth_client):
    assert auth_client.post("/api/auth/facebook", headers=HEADERS).status_code == 503
    assert auth_client.post("/api/auth/google").status_code == 403


def test_recreating_deleted_account_does_not_reset_allowance(auth_client):
    client = auth_client
    login(client)
    job = client.post("/api/jobs", json=PAYLOAD, headers=HEADERS).json()
    client.app.state.store.update(job["id"], state="complete")
    assert client.delete("/api/account", headers=HEADERS).status_code == 204
    client.get("/api/session")
    login(client)
    assert client.get("/api/session").json()["quota"]["remaining"] == 19


def test_foreign_callback_provider_does_not_accept_google_state(auth_client):
    callback = begin(auth_client).replace("/auth/google/", "/auth/facebook/")
    assert "login_expired" in auth_client.get(callback, follow_redirects=False).headers["location"]


def test_logged_out_transaction_cannot_finish(auth_client):
    callback = begin(auth_client)
    auth_client.post("/api/logout", headers=HEADERS)
    assert "login_expired" in auth_client.get(callback, follow_redirects=False).headers["location"]
    assert (
        auth_client.get("/api/session", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    )


def test_all_device_logout_revokes_both_sessions(auth_client):
    login(auth_client)
    with TestClient(auth_client.app, base_url="http://localhost") as other:
        other.get("/api/session")
        login(other)
        first = auth_client.cookies.get("ytd_session")
        second = other.cookies.get("ytd_session")
        assert first != second
        assert auth_client.post("/api/logout?all_devices=true", headers=HEADERS).status_code == 204
        assert other.get("/api/jobs").status_code == 401
        assert auth_client.app.state.accounts.session(first) is None
        assert auth_client.app.state.accounts.session(second) is None


def test_provider_timeout_is_sanitized_and_does_not_create_an_account(auth_client, monkeypatch):
    async def broken(*args):
        raise TimeoutError("secret-provider-payload")

    callback = begin(auth_client)
    monkeypatch.setattr(auth_client.app.state.oauth, "identity", broken)
    response = auth_client.get(callback, follow_redirects=False)
    assert response.headers["location"] == "/?auth=login_failed"
    assert "secret-provider-payload" not in str(response.headers) + response.text
    assert auth_client.get("/api/session").json()["account"] is None
