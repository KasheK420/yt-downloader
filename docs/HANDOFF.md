# Handoff

## State

- Public source repository: `KasheK420/yt-downloader`.
- Initial version: 0.1.0. Python/FastAPI service with static bilingual UI.
- Scope: private use first, later public use without login.
- MP4/MP3 paths were exercised with a real YouTube video and verified with ffprobe.
- [VERIFICATION.md](VERIFICATION.md) records test scope and unavailable checks.
- Production infrastructure has not been changed. Public launch is tracked separately.

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
