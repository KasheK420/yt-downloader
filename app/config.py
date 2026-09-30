from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="YTD_", env_file=".env", extra="ignore", env_ignore_empty=True
    )

    data_dir: Path = Path(".data")
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "[::1]"]
    secure_cookies: bool = False
    public_mode: bool = False
    require_login: bool = False
    public_origin: str | None = None
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    facebook_client_id: str | None = None
    facebook_client_secret: SecretStr | None = None
    facebook_api_version: str = Field(default="v26.0", pattern=r"^v\d+\.0$")
    guest_downloads: int = Field(default=3, ge=1, le=1000)
    guest_window_seconds: int = Field(default=3600, ge=60, le=604800)
    free_downloads: int = Field(default=20, ge=1, le=10000)
    free_window_seconds: int = Field(default=86400, ge=60, le=604800)
    guest_max_duration_seconds: int = Field(default=1800, ge=1)
    guest_max_file_bytes: int = Field(default=250 * 1024**2, ge=1)
    guest_max_quality: int = Field(default=720, ge=360, le=1080)
    public_ip_daily_limit: int = Field(default=40, ge=1, le=10000)
    max_active_per_session: int = Field(default=2, ge=1, le=20)
    max_queue: int = Field(default=12, ge=1, le=100)
    max_queue_wait_seconds: int = Field(default=1800, ge=1)
    rate_limit: int = Field(default=5, ge=1, le=100)
    rate_window_seconds: int = Field(default=600, ge=1)
    max_duration_seconds: int = Field(default=7200, ge=1)
    max_file_bytes: int = Field(default=500 * 1024**2, ge=1)
    max_job_bytes: int = Field(default=1024**3, ge=1)
    max_storage_bytes: int = Field(default=5 * 1024**3, ge=1)
    job_timeout_seconds: int = Field(default=1800, ge=1)
    retention_seconds: int = Field(default=3600, ge=1)
    cleanup_interval_seconds: float = Field(default=15, ge=0.05, le=300)
    ffmpeg_location: str | None = None
    js_runtime: str = "node"

    @model_validator(mode="after")
    def check_limits(self) -> "Settings":
        if self.public_origin:
            origin = urlsplit(self.public_origin)
            if (
                not origin.hostname
                or origin.username
                or origin.password
                or origin.path not in {"", "/"}
                or origin.query
                or origin.fragment
                or origin.scheme not in {"https", "http"}
                or (origin.scheme == "http" and origin.hostname not in {"localhost", "127.0.0.1"})
            ):
                raise ValueError("public_origin must be an HTTPS origin or a localhost HTTP origin")
            if origin.scheme == "https" and not self.secure_cookies:
                raise ValueError("HTTPS authentication requires secure_cookies=true")
            if origin.hostname not in self.allowed_hosts:
                raise ValueError("public_origin must be present in allowed_hosts")
            self.public_origin = self.public_origin.rstrip("/")
        for provider in ("google", "facebook"):
            configured = (
                getattr(self, f"{provider}_client_id"),
                getattr(self, f"{provider}_client_secret"),
            )
            if any(configured) and (not all(configured) or not self.public_origin):
                raise ValueError(f"{provider} requires client ID, secret and public_origin")
        if self.require_login and not (self.google_client_id or self.facebook_client_id):
            raise ValueError("require_login needs at least one configured provider")
        if self.max_file_bytes > self.max_job_bytes:
            raise ValueError("max_file_bytes must not exceed max_job_bytes")
        if self.max_job_bytes > self.max_storage_bytes:
            raise ValueError("max_job_bytes must not exceed max_storage_bytes")
        if self.js_runtime not in {"node", "deno"}:
            raise ValueError("js_runtime must be node or deno")
        return self
