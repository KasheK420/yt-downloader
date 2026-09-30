from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YTD_", env_file=".env", extra="ignore")

    data_dir: Path = Path(".data")
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "[::1]"]
    secure_cookies: bool = False
    max_active_per_session: int = Field(default=2, ge=1, le=20)
    max_queue: int = Field(default=12, ge=1, le=100)
    rate_limit: int = Field(default=5, ge=1, le=100)
    rate_window_seconds: int = Field(default=600, ge=1)
    max_duration_seconds: int = Field(default=7200, ge=1)
    max_file_bytes: int = Field(default=500 * 1024**2, ge=1)
    max_job_bytes: int = Field(default=1024**3, ge=1)
    max_storage_bytes: int = Field(default=5 * 1024**3, ge=1)
    job_timeout_seconds: int = Field(default=1800, ge=1)
    retention_seconds: int = Field(default=3600, ge=1)
    ffmpeg_location: str | None = None
    js_runtime: str = "node"

    @model_validator(mode="after")
    def check_limits(self) -> "Settings":
        if self.max_file_bytes > self.max_job_bytes:
            raise ValueError("max_file_bytes must not exceed max_job_bytes")
        if self.max_job_bytes > self.max_storage_bytes:
            raise ValueError("max_job_bytes must not exceed max_storage_bytes")
        if self.js_runtime not in {"node", "deno"}:
            raise ValueError("js_runtime must be node or deno")
        return self
