# Changelog

Changes follow Semantic Versioning. Release publication is explicit through the Release workflow.

## 0.3.0 - 2026-09-30

- Add optional Google/Facebook accounts with browser-bound code flows, revocable sessions,
  guest-library migration, all-device logout and account deletion. Provider setup is required.
- Add configurable public guest/free budgets, per-job resource snapshots, accurate rolling
  allowance reporting and idempotent job admission. Guest access remains the default.
- Add retry, early removal, owned Range-capable previews, library filters and preference storage.
- Recover expired sessions and network interruptions without recreating players or duplicate jobs.
- Run maintenance independently of downloads, preserve cleanup metadata on file-lock failures,
  protect accepted streams during removal, and expire jobs that wait too long in the queue.
- Isolate OAuth secrets from downloader child environments and expand protocol/lifecycle tests.
- Document OAuth activation, free access policies, privacy and hosted-acceptance boundaries.

## 0.2.0 - 2026-09-30

- Add Facebook video/Reel and Instagram Reel/single-video post downloads to MP4 and MP3.
- Add bounded share-link resolution with per-hop validation and explicit extractor selection.
- Reject collections before extraction traversal; preserve existing session isolation and limits.
- Preserve portrait orientation, downscale only when needed, and probe actual output duration.
- Add automatic source labels, Czech/English link help, and actionable share/collection errors.
- Include yt-dlp's curl-cffi transport extra for supported anonymous provider requests.
- Expand URL, redirect, API, real-media, desktop/mobile, and accessibility verification.

## 0.1.0 - 2026-09-30

- Add YouTube link to MP4/MP3 conversion with selectable quality.
- Add Czech/English responsive web interface, progress, cancellation, and downloads.
- Add anonymous session isolation, persistent jobs, expiry, and bounded processing.
- Add Docker packaging, deterministic media/browser tests, CI, CodeQL, and Dependabot.
- Add operator, developer, API, security, and public-launch documentation.
