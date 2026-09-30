import hashlib
import hmac
import re
import secrets
import shutil
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import Settings
from app.files import MediaFiles
from app.runner import Runner
from app.security import BodyLimitMiddleware, signing_secret
from app.store import LimitExceeded, Store
from app.urls import normalize_url

STATIC = Path(__file__).parent / "static"
COOKIE = "ytd_session"


class JobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(max_length=2048)
    kind: Literal["mp4", "mp3"]
    quality: int

    @field_validator("url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        return normalize_url(value)

    @model_validator(mode="after")
    def valid_quality(self) -> "JobRequest":
        if self.quality not in ({360, 720, 1080} if self.kind == "mp4" else {128, 192, 320}):
            raise ValueError("Unsupported quality")
        return self


def runtime_status(settings: Settings) -> dict[str, bool]:
    def available(name: str) -> bool:
        if settings.ffmpeg_location:
            root = Path(settings.ffmpeg_location)
            if root.is_file():
                root = root.parent
            return any((root / candidate).is_file() for candidate in (name, f"{name}.exe"))
        return shutil.which(name) is not None

    return {
        "ffmpeg": available("ffmpeg"),
        "ffprobe": available("ffprobe"),
        settings.js_runtime: shutil.which(settings.js_runtime) is not None,
    }


def public_job(job: dict[str, Any]) -> dict[str, Any]:
    keys = {
        "id",
        "kind",
        "quality",
        "state",
        "title",
        "progress",
        "error",
        "file_bytes",
        "created_at",
        "expires_at",
    }
    return {key: value for key, value in job.items() if key in keys}


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    secret = signing_secret(settings.data_dir)
    signer = URLSafeTimedSerializer(secret, salt="anonymous-session-v1")
    store = Store(settings)
    files = MediaFiles(settings.data_dir)
    runner = Runner(store, settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await runner.start()
        try:
            yield
        finally:
            await runner.stop()

    app = FastAPI(
        title="yt-downloader",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.store = store
    app.state.runner = runner

    @app.middleware("http")
    async def boundaries(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            expected = str(request.base_url).rstrip("/")
            if request.headers.get("x-requested-with") != "yt-downloader" or (
                origin and origin != expected
            ):
                return JSONResponse({"detail": "invalid_origin"}, status_code=403)
        owner = None
        try:
            value = signer.loads(request.cookies.get(COOKIE, ""), max_age=7 * 86400)
            if isinstance(value, str) and re.fullmatch(r"[a-f0-9]{32}", value):
                owner = value
        except BadSignature:
            pass
        request.state.owner = owner
        response = await call_next(request)
        response.headers.update(
            {
                "Content-Security-Policy": (
                    "default-src 'self'; script-src 'self'; style-src 'self'; "
                    "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; "
                    "frame-ancestors 'none'; form-action 'self'"
                ),
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
                "X-Frame-Options": "DENY",
                "Cache-Control": "no-store",
            }
        )
        return response

    # Register host validation last so it runs before origin/session handling.
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts, www_redirect=False
    )

    def owner_of(request: Request) -> str:
        if not request.state.owner:
            raise HTTPException(401, "session_required")
        return str(request.state.owner)

    def owned(job_id: str, request: Request) -> dict[str, Any]:
        job = store.get(job_id, owner_of(request))
        if job is None:
            raise HTTPException(404, "job_not_found")
        return job

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, __: RequestValidationError) -> JSONResponse:
        return JSONResponse({"detail": "invalid_request"}, status_code=422)

    @app.get("/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readiness() -> JSONResponse:
        checks = runtime_status(settings)
        alive = runner.task is not None and not runner.task.done()
        checks["worker"] = alive
        return JSONResponse(
            {"status": "ok" if all(checks.values()) else "unavailable", "checks": checks},
            status_code=200 if all(checks.values()) else 503,
        )

    @app.get("/api/session")
    async def session(request: Request, response: Response) -> dict[str, Any]:
        owner = request.state.owner or secrets.token_hex(16)
        response.set_cookie(
            COOKIE,
            signer.dumps(owner),
            httponly=True,
            samesite="strict",
            secure=settings.secure_cookies,
            max_age=7 * 86400,
        )
        return {
            "max_duration_seconds": settings.max_duration_seconds,
            "max_file_bytes": settings.max_file_bytes,
            "retention_seconds": settings.retention_seconds,
            "ready": all(runtime_status(settings).values()),
            "server_time": time.time(),
        }

    @app.get("/api/jobs")
    async def list_jobs(request: Request) -> list[dict[str, Any]]:
        return [public_job(job) for job in store.list_jobs(owner_of(request))]

    @app.post("/api/jobs", status_code=202)
    async def create_job(payload: JobRequest, request: Request) -> dict[str, Any]:
        owner = owner_of(request)
        if not all(runtime_status(settings).values()):
            raise HTTPException(503, "runtime_unavailable")
        if files.size() + settings.max_job_bytes > settings.max_storage_bytes:
            raise HTTPException(503, "storage_full")
        address = request.client.host if request.client else "unknown"
        client_key = hmac.new(secret.encode(), address.encode(), hashlib.sha256).hexdigest()
        try:
            return public_job(
                store.create(owner, client_key, payload.url, payload.kind, payload.quality)
            )
        except LimitExceeded as exc:
            raise HTTPException(
                429, str(exc), headers={"Retry-After": str(settings.rate_window_seconds)}
            ) from exc

    @app.get("/api/jobs/{job_id}")
    async def get_job(job_id: str, request: Request) -> dict[str, Any]:
        return public_job(owned(job_id, request))

    @app.delete("/api/jobs/{job_id}")
    async def cancel_job(job_id: str, request: Request) -> dict[str, Any]:
        job = owned(job_id, request)
        if job["state"] in {"queued", "downloading", "processing"}:
            await runner.cancel(job_id)
        return public_job(owned(job_id, request))

    @app.api_route("/api/jobs/{job_id}/file", methods=["GET", "HEAD"])
    async def download(job_id: str, request: Request) -> FileResponse:
        job = owned(job_id, request)
        if job["state"] != "complete":
            raise HTTPException(409, "file_not_ready")
        try:
            path = files.output(job_id, job["kind"])
        except ValueError as exc:
            raise HTTPException(410, "file_expired") from exc
        if not path.is_file():
            raise HTTPException(410, "file_expired")
        name = (
            re.sub(r"[^\w .()-]", "_", job["title"], flags=re.UNICODE).strip(" .")[:100]
            or "download"
        )
        return FileResponse(
            path,
            filename=f"{name}.{job['kind']}",
            media_type="video/mp4" if job["kind"] == "mp4" else "audio/mpeg",
        )

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    if STATIC.exists():
        app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
