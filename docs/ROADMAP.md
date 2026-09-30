# Roadmap

## v0.1.0: private-first application

Delivered scope: MP4 and MP3 from single-video URLs, quality controls, bilingual responsive UI,
anonymous job isolation, queue/progress/cancellation, limits and retention, Docker, tests,
CI/security tooling, and operator/developer documentation.

## v0.2.0: social video

Facebook videos/Reels and Instagram Reels/single-video posts join YouTube. Shared links are
resolved within approved hosts. Provider labels, bilingual link help, collection rejection,
and actual duration/dimension checks cover the new workflows. No database migration is needed.

## Public launch milestone

The future public service has no login. Before launch:

1. Select hostname/host and verify HTTPS, trusted client IP forwarding, and edge abuse limits.
2. Verify real provider downloads from the chosen host, concurrent visitors, lifecycle/expiry,
   filesystem quota behavior, and operational alerts.
3. Record a rollback and incident procedure for provider breakage or abusive traffic.

These are deployment acceptance tasks, not missing basic downloader functionality. They are
tracked as GitHub issues under the Public launch milestone; no production deployment is implied.

## Candidate improvements

- Per-video format preview and more metadata after bounded inspection.
- WebM and additional output formats if requested.
- Browser download-expiry countdown and optional early file removal.
- Distributed queue/shared object storage only when measured usage requires it.

Playlists, user accounts, uploaded cookies, arbitrary download sites, DRM workarounds, and
unrestricted command/configuration endpoints are outside this release.
