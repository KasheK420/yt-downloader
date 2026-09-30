"""Effective free-tier limits, always capped by operator resource ceilings."""

from dataclasses import dataclass

from app.config import Settings


@dataclass(frozen=True)
class Policy:
    tier: str
    account: bool
    downloads: int
    window_seconds: int
    max_active: int
    max_quality: int
    max_duration_seconds: int
    max_file_bytes: int


def policy_for(settings: Settings, authenticated: bool) -> Policy:
    guest = settings.public_mode and not authenticated
    return Policy(
        tier=("free" if authenticated else "guest") if settings.public_mode else "personal",
        account=authenticated,
        downloads=(settings.free_downloads if authenticated else settings.guest_downloads)
        if settings.public_mode
        else settings.rate_limit,
        window_seconds=(
            settings.free_window_seconds if authenticated else settings.guest_window_seconds
        )
        if settings.public_mode
        else settings.rate_window_seconds,
        max_active=min(1 if guest else 2, settings.max_active_per_session)
        if settings.public_mode
        else settings.max_active_per_session,
        max_quality=settings.guest_max_quality if guest else 1080,
        max_duration_seconds=min(settings.guest_max_duration_seconds, settings.max_duration_seconds)
        if guest
        else settings.max_duration_seconds,
        max_file_bytes=min(settings.guest_max_file_bytes, settings.max_file_bytes)
        if guest
        else settings.max_file_bytes,
    )
