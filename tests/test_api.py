import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

HEADERS = {"X-Requested-With": "yt-downloader"}
PAYLOAD = {"url": "https://youtu.be/BaW_jenozKc", "kind": "mp4", "quality": 720}


@pytest.fixture
def client(settings: Settings, monkeypatch: pytest.MonkeyPatch):
    # Keep real persistence/HTTP behavior; do not make provider requests in tests.
    try:
        from app.runner import Runner

        async def offline_start(self):
            pass

        monkeypatch.setattr(Runner, "start", offline_start)
        monkeypatch.setattr(
            "app.main.runtime_status", lambda _: {"ffmpeg": True, "ffprobe": True, "node": True}
        )
    except ImportError:
        pass
    with TestClient(create_app(settings)) as instance:
        instance.get("/api/session")
        yield instance


@pytest.mark.parametrize(
    "url", [PAYLOAD["url"], "https://facebook.com/reel/123/", "https://instagram.com/reel/Abc_123/"]
)
def test_create_list_and_owner_isolation(client: TestClient, settings: Settings, url: str) -> None:
    response = client.post("/api/jobs", json={**PAYLOAD, "url": url}, headers=HEADERS)
    assert response.status_code == 202
    job = response.json()
    assert job["state"] == "queued"
    assert "owner" not in job and "url" not in job
    assert len(client.get("/api/jobs").json()) == 1
    with TestClient(create_app(settings)) as stranger:
        stranger.get("/api/session")
        for method, suffix in [("GET", ""), ("GET", "/file"), ("DELETE", "")]:
            result = stranger.request(method, f"/api/jobs/{job['id']}{suffix}", headers=HEADERS)
            assert result.status_code == 404
        assert stranger.get("/api/jobs").json() == []


def test_mutations_require_same_origin_custom_header(client: TestClient) -> None:
    assert client.post("/api/jobs", json=PAYLOAD).status_code == 403
    result = client.post(
        "/api/jobs", json=PAYLOAD, headers={**HEADERS, "Origin": "https://evil.example"}
    )
    assert result.status_code == 403


@pytest.mark.parametrize(
    "payload",
    [
        {**PAYLOAD, "url": "http://127.0.0.1/admin"},
        {**PAYLOAD, "kind": "mp3", "quality": 720},
        {**PAYLOAD, "quality": 9999},
        {**PAYLOAD, "output_path": "/etc/passwd"},
    ],
)
def test_invalid_download_requests_are_rejected(client: TestClient, payload: dict) -> None:
    assert client.post("/api/jobs", json=payload, headers=HEADERS).status_code == 422


def test_queue_limit_reports_actionable_error(client: TestClient) -> None:
    for _ in range(2):
        assert client.post("/api/jobs", json=PAYLOAD, headers=HEADERS).status_code == 202
    response = client.post("/api/jobs", json=PAYLOAD, headers=HEADERS)
    assert response.status_code == 429
    assert response.json()["detail"] == "session_limit"


def test_cancel_removes_partial_files(client: TestClient, settings: Settings) -> None:
    response = client.post("/api/jobs", json=PAYLOAD, headers=HEADERS)
    assert response.status_code == 202
    job_id = response.json()["id"]
    folder = settings.data_dir / "media" / job_id
    folder.mkdir(parents=True)
    (folder / "media.mp4.part").write_bytes(b"partial")
    assert client.delete(f"/api/jobs/{job_id}", headers=HEADERS).status_code == 200
    assert client.get(f"/api/jobs/{job_id}").json()["state"] == "cancelled"
    assert not folder.exists()


def test_download_checks_completion_and_uses_attachment(
    client: TestClient, settings: Settings
) -> None:
    response = client.post("/api/jobs", json=PAYLOAD, headers=HEADERS)
    assert response.status_code == 202
    job_id = response.json()["id"]
    assert client.get(f"/api/jobs/{job_id}/file").status_code == 409
    folder = settings.data_dir / "media" / job_id
    folder.mkdir(parents=True)
    (folder / "media.mp4").write_bytes(b"test-media-content")
    client.app.state.store.update(job_id, state="complete", title="A / tricky title", file_bytes=18)
    result = client.get(f"/api/jobs/{job_id}/file")
    assert result.status_code == 200
    assert result.content == b"test-media-content"
    assert result.headers["content-disposition"].startswith("attachment;")
    assert result.headers["cache-control"] == "no-store"
    assert result.headers["x-content-type-options"] == "nosniff"


def test_refuses_oversized_body_and_foreign_host(client: TestClient) -> None:
    result = client.post("/api/jobs", content=b"x" * 5000, headers=HEADERS)
    assert result.status_code == 413
    assert client.get("/", headers={"Host": "evil.example"}).status_code == 400


def test_session_cookie_and_security_headers(client: TestClient) -> None:
    result = client.get("/api/session")
    assert result.status_code == 200
    assert "httponly" in result.headers["set-cookie"].lower()
    assert "samesite=strict" in result.headers["set-cookie"].lower()
    assert "default-src 'self'" in result.headers["content-security-policy"]


def test_missing_file_is_reported_as_gone(client: TestClient) -> None:
    response = client.post("/api/jobs", json=PAYLOAD, headers=HEADERS)
    assert response.status_code == 202
    job_id = response.json()["id"]
    client.app.state.store.update(job_id, state="complete")
    assert client.get(f"/api/jobs/{job_id}/file").status_code == 410


@pytest.mark.parametrize(
    "url,provider,canonical",
    [
        (
            "https://facebook.com/reel/123456789/?ref=tracking",
            "facebook",
            "https://www.facebook.com/reel/123456789/",
        ),
        (
            "https://instagram.com/reels/Abc_123/?igsh=tracking",
            "instagram",
            "https://www.instagram.com/reel/Abc_123/",
        ),
        (PAYLOAD["url"], "youtube", "https://www.youtube.com/watch?v=BaW_jenozKc"),
    ],
)
def test_social_jobs_expose_only_provider_and_keep_canonical_input(
    client, url, provider, canonical
):
    response = client.post("/api/jobs", json={**PAYLOAD, "url": url}, headers=HEADERS)
    assert response.status_code == 202
    job = response.json()
    assert job["provider"] == provider
    assert "url" not in job and "owner" not in job
    assert client.get(f"/api/jobs/{job['id']}").json()["provider"] == provider
    with client.app.state.store._db() as db:
        assert (
            db.execute("SELECT url FROM jobs WHERE id = ?", (job["id"],)).fetchone()[0] == canonical
        )


def test_session_reports_supported_providers(client):
    assert client.get("/api/session").json()["providers"] == ["youtube", "facebook", "instagram"]
