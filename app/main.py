import asyncio
import hashlib
import hmac
import re
import shutil
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.accounts import FLOW_TTL, SESSION_TTL, Accounts, LoginError
from app.config import Settings
from app.files import MediaResponse
from app.oauth import SocialLogin
from app.policy import policy_for
from app.runner import Runner
from app.security import BodyLimitMiddleware, signing_secret
from app.store import LimitExceeded, Store
from app.urls import normalize_url, provider_for

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
    return {
        **{key: value for key, value in job.items() if key in keys},
        "provider": provider_for(job["url"]),
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    secret = signing_secret(settings.data_dir)
    signer = URLSafeTimedSerializer(secret, salt="anonymous-session-v1")
    store = Store(settings)
    runner = Runner(store, settings)
    files = runner.files
    accounts = Accounts(store, secret)
    oauth = SocialLogin(settings)
    runner.prune_accounts = accounts.prune

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await runner.start()
        try:
            yield
        finally:
            await runner.stop()

    app = FastAPI(
        title="yt-downloader",
        version="0.3.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.store = store
    app.state.runner = runner
    app.state.accounts = accounts
    app.state.oauth = oauth

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
        if (
            request.url.path == "/api/session"
            and request.headers.get("sec-fetch-site") == "cross-site"
        ):
            return JSONResponse({"detail": "invalid_origin"}, status_code=403)
        request.state.session = accounts.session(request.cookies.get(COOKIE, ""))
        request.state.owner = request.state.session["owner"] if request.state.session else None
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
        current = accounts.session(request.cookies.get(COOKIE, ""))
        if not current:
            raise HTTPException(401, "session_required")
        request.state.session = current
        request.state.owner = current["owner"]
        return str(current["owner"])

    def client_key(request: Request) -> str:
        address = request.client.host if request.client else "unknown"
        return hmac.new(secret.encode(), address.encode(), hashlib.sha256).hexdigest()

    def cookie(response: Response, token: str) -> None:
        if not re.fullmatch(r"[a-f0-9]{64}", token):
            raise ValueError("Invalid session token")
        response.set_cookie(
            COOKIE,
            token,
            httponly=True,
            samesite="strict",
            secure=settings.secure_cookies,
            max_age=SESSION_TTL,
        )

    def owned(job_id: str, request: Request) -> dict[str, Any]:
        job = store.get(job_id, owner_of(request))
        if job is None:
            raise HTTPException(404, "job_not_found")
        return job

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, __: RequestValidationError) -> JSONResponse:
        return JSONResponse({"detail": "invalid_request"}, status_code=422)

    @app.exception_handler(LimitExceeded)
    async def limited(_: Request, exc: LimitExceeded) -> JSONResponse:
        return JSONResponse(
            {"detail": str(exc)}, status_code=429, headers={"Retry-After": str(exc.retry_after)}
        )

    @app.get("/healthz")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readiness() -> JSONResponse:
        checks = runtime_status(settings)
        alive = runner.task is not None and not runner.task.done()
        checks["worker"] = alive
        checks["maintenance"] = (
            runner.maintenance_task is not None and not runner.maintenance_task.done()
        )
        return JSONResponse(
            {"status": "ok" if all(checks.values()) else "unavailable", "checks": checks},
            status_code=200 if all(checks.values()) else 503,
        )

    @app.get("/api/session")
    async def session(request: Request, response: Response) -> dict[str, Any]:
        token = request.cookies.get(COOKIE, "")
        current = accounts.session(token)
        if not current:
            legacy = None
            try:
                value = signer.loads(token, max_age=SESSION_TTL)
                if isinstance(value, str) and re.fullmatch(r"[a-f0-9]{32}", value):
                    legacy = value
            except BadSignature:
                pass
            token = accounts.new_guest(client_key(request), legacy)
            current = accounts.session(token)
        else:
            accounts.refresh(token)
        assert current
        cookie(response, token)
        policy = policy_for(settings, bool(current["account_id"]))
        return {
            **asdict(policy),
            "account": {"name": current["name"], "provider": current["provider"]}
            if current["account_id"]
            else None,
            "login_providers": oauth.providers(),
            "login_required": settings.require_login,
            "plans": [asdict(policy_for(settings, value)) for value in (False, True)]
            if settings.public_mode
            else [asdict(policy)],
            "quota": store.budget(current["owner"], client_key(request), policy),
            "retention_seconds": settings.retention_seconds,
            "ready": runner.available() and all(runtime_status(settings).values()),
            "providers": ["youtube", "facebook", "instagram"],
            "server_time": time.time(),
        }

    @app.post("/api/auth/{provider}")
    async def start_login(provider: str, request: Request, response: Response) -> dict[str, str]:
        owner_of(request)
        if provider not in oauth.providers():
            raise HTTPException(503, "login_unavailable")
        if str(request.base_url).rstrip("/") != settings.public_origin:
            raise HTTPException(403, "login_origin_mismatch")
        if request.state.session["account_id"]:
            raise HTTPException(409, "already_signed_in")
        accounts.guard(client_key(request), "login")
        state, binding, verifier, nonce = accounts.begin(request.cookies[COOKIE], provider)
        try:
            async with asyncio.timeout(15):
                url = await oauth.authorize(provider, state, verifier, nonce)
        except Exception:
            # Never log callback codes, OAuth tokens or provider error bodies.
            raise HTTPException(503, "login_unavailable") from None
        response.set_cookie(
            "ytd_login",
            binding,
            httponly=True,
            samesite="lax",
            secure=settings.secure_cookies,
            max_age=FLOW_TTL,
            path="/auth",
        )
        return {"url": url}

    @app.get("/auth/{provider}/callback")
    async def login_callback(provider: str, request: Request) -> Response:
        status = "login_failed"
        token = None
        try:
            params = request.query_params
            if (
                provider not in oauth.providers()
                or len(params.get("state", "")) > 256
                or len(params.get("code", "")) > 4096
                or len(params.getlist("state")) != 1
                or len(params.getlist("code")) > 1
            ):
                raise LoginError("login_expired")
            flow = accounts.consume(
                provider, params.get("state", ""), request.cookies.get("ytd_login", "")
            )
            if params.get("error"):
                raise LoginError("login_cancelled")
            if not params.get("code"):
                raise LoginError("login_failed")
            async with asyncio.timeout(20):
                subject, name = await oauth.identity(provider, params["code"], flow)
            token = accounts.finish(flow, subject, name)
            status = "success"
        except LoginError as exc:
            status = str(exc)
        except Exception:
            pass  # Fixed public error only; provider payloads may contain credentials.
        response = RedirectResponse(f"/?auth={status}", status_code=303)
        response.delete_cookie(
            "ytd_login", path="/auth", secure=settings.secure_cookies, httponly=True, samesite="lax"
        )
        if token:
            cookie(response, token)
        return response

    @app.post("/api/logout", status_code=204)
    async def logout(request: Request, all_devices: bool = False) -> Response:
        owner_of(request)
        accounts.logout(request.cookies[COOKIE], all_devices)
        response = Response(status_code=204)
        response.delete_cookie(
            COOKIE, secure=settings.secure_cookies, httponly=True, samesite="strict"
        )
        return response

    @app.delete("/api/account", status_code=204)
    async def delete_account(request: Request) -> Response:
        owner_of(request)
        account_id = request.state.session["account_id"]
        if not account_id:
            raise HTTPException(403, "account_required")
        ids = accounts.delete(account_id)
        for job_id in ids:
            await runner.cancel(job_id)
        runner.cleanup()
        response = Response(status_code=204)
        response.delete_cookie(
            COOKIE, secure=settings.secure_cookies, httponly=True, samesite="strict"
        )
        return response

    @app.get("/api/jobs")
    async def list_jobs(request: Request) -> list[dict[str, Any]]:
        return [public_job(job) for job in store.list_jobs(owner_of(request))]

    @app.post("/api/jobs", status_code=202)
    async def create_job(payload: JobRequest, request: Request) -> dict[str, Any]:
        return admit(payload, request)

    def admit(payload: JobRequest, request: Request) -> dict[str, Any]:
        owner = owner_of(request)
        authenticated = bool(request.state.session["account_id"])
        if settings.require_login and not authenticated:
            raise HTTPException(403, "login_required")
        policy = policy_for(settings, authenticated)
        if payload.kind == "mp4" and payload.quality > policy.max_quality:
            raise HTTPException(403, "quality_limit")
        request_key = request.headers.get("idempotency-key")
        if request_key and not re.fullmatch(r"[A-Za-z0-9_-]{16,80}", request_key):
            raise HTTPException(422, "invalid_request")
        if request_key:
            try:
                previous = store.repeated(
                    owner, request_key, payload.url, payload.kind, payload.quality
                )
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from exc
            if previous:
                return public_job(previous)
        if not runner.available() or not all(runtime_status(settings).values()):
            raise HTTPException(503, "runtime_unavailable")
        if files.size() + settings.max_job_bytes > settings.max_storage_bytes:
            raise HTTPException(503, "storage_full")
        try:
            return public_job(
                store.create(
                    owner,
                    client_key(request),
                    payload.url,
                    payload.kind,
                    payload.quality,
                    policy=policy,
                    request_key=request_key,
                )
            )
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.post("/api/jobs/{job_id}/retry", status_code=202)
    async def retry_job(job_id: str, request: Request) -> dict[str, Any]:
        job = owned(job_id, request)
        if job["state"] not in {"failed", "cancelled"}:
            raise HTTPException(409, "retry_unavailable")
        return admit(JobRequest(url=job["url"], kind=job["kind"], quality=job["quality"]), request)

    @app.get("/api/jobs/{job_id}")
    async def get_job(job_id: str, request: Request) -> dict[str, Any]:
        return public_job(owned(job_id, request))

    @app.delete("/api/jobs/{job_id}")
    async def cancel_job(job_id: str, request: Request) -> Response:
        job = owned(job_id, request)
        if job["state"] in {"queued", "downloading", "processing"}:
            await runner.cancel(job_id)
            return JSONResponse(public_job(owned(job_id, request)))
        store.remove(job_id)
        runner.cleanup()
        return Response(status_code=204)

    @app.api_route("/api/jobs/{job_id}/file", methods=["GET", "HEAD"])
    async def download(job_id: str, request: Request) -> FileResponse:
        return media(job_id, request, inline=False)

    @app.api_route("/api/jobs/{job_id}/preview", methods=["GET", "HEAD"])
    async def preview(job_id: str, request: Request) -> FileResponse:
        return media(job_id, request, inline=True)

    def media(job_id: str, request: Request, inline: bool) -> FileResponse:
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
        return MediaResponse(files, job_id, job["kind"], f"{name}.{job['kind']}", inline)

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    if STATIC.exists():
        app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
