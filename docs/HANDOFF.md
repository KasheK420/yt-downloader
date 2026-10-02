# Handoff

## State

- Public source repository: `KasheK420/yt-downloader`.
- Current source version: 0.3.1. Python/FastAPI service with static bilingual UI.
- MP4 outputs normalize to H.264/yuv420p and AAC with faststart, then pass a full decode check.
- Supports YouTube, Facebook, and Instagram single-video links; see [SOURCES.md](SOURCES.md).
- Scope: private use first; later public guest access plus optional Google/Facebook free accounts.
- Retries, deletion, owned media previews, independent cleanup, quotas and session recovery are implemented.
- OAuth protocol fixtures pass; live Google/Meta console setup and real login are still pending.
  See [AUTHENTICATION.md](AUTHENTICATION.md) and [LIMITS.md](LIMITS.md).
- Live YouTube/Facebook MP4 and MP3 and Instagram MP4 passed ffprobe checks. Tested Instagram
  sources supplied no audio; live Instagram MP3 with audio remains unverified.
- [VERIFICATION.md](VERIFICATION.md) records test scope and unavailable checks.
- Guest hosting is deployed at https://ytdown.majorluk.cz on Contabo. See [PRODUCTION.md](PRODUCTION.md).
- Hosted Facebook MP4/MP3 and Instagram MP4 passed. YouTube requests from the VPS require
  bot verification; provider acceptance remains incomplete. Optional OAuth is still disabled.
- The image is built locally on the VPS; registry publishing is not configured. Uptime Kuma
  was omitted at the owner's request; systemd health checks and daily metadata backups are active.

## Continue

1. Read [AGENTS.md](../AGENTS.md), [ARCHITECTURE.md](ARCHITECTURE.md), and
   [DEPLOYMENT.md](DEPLOYMENT.md).
2. Verify current branch, worktree cleanliness, dependency versions, and remote CI before edits.
3. Use a focused branch and preserve anonymous owner isolation and bounded processing.
4. Run the documented tests; update evidence without equating synthetic and provider checks.
5. Public deployment requires the target hostname and host-specific acceptance in the roadmap.

The initial design and implementation plan are under `docs/superpowers/`. The source repository
is public; local configuration, provider outputs, media, and session keys must stay excluded.
Do not assume an image has been published merely because the manual Release workflow exists.
