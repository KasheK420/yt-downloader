# Roadmap

## v0.1.0: private-first application

Delivered scope: MP4 and MP3 from single-video URLs, quality controls, bilingual responsive UI,
anonymous job isolation, queue/progress/cancellation, limits and retention, Docker, tests,
CI/security tooling, and operator/developer documentation.

## v0.2.0: social video

Facebook videos/Reels and Instagram Reels/single-video posts join YouTube. Shared links are
resolved within approved hosts. Provider labels, bilingual link help, collection rejection,
and actual duration/dimension checks cover the new workflows. No database migration is needed.

## v0.3.0: workflow and optional accounts

Job retry/deletion, owned media previews, independent cleanup, stable cards, filters, preference
storage and connection recovery. Configurable public guest/free budgets and optional Google/
Facebook accounts, with logout and account deletion. Protocol validation is covered offline;
real provider-console activation and hosted sign-in remain acceptance work.

## Public launch milestone

The future public service supports guests with optional free accounts. Before launch:

1. Select hostname/host and verify HTTPS, trusted client IP forwarding, and edge abuse limits.
2. Verify real provider downloads from the chosen host, concurrent visitors, lifecycle/expiry,
   filesystem quota behavior, and operational alerts.
3. Record a rollback and incident procedure for provider breakage or abusive traffic.
4. Register operator-owned Google/Meta applications, set exact callback/consent/privacy details,
   and prove login/logout/deletion with real accounts if optional sign-in is enabled.

These are deployment acceptance tasks, not missing basic downloader functionality. They are
tracked as GitHub issues under the Public launch milestone; no production deployment is implied.

## Candidate improvements

- Per-video format preview and more metadata after bounded inspection.
- WebM and additional output formats if requested.
- Distributed queue/shared object storage only when measured usage requires it.

Playlists, password accounts, paid plans, uploaded cookies, arbitrary download sites, DRM workarounds, and
unrestricted command/configuration endpoints are outside this release.
