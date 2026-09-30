# Verification evidence

## v0.3.0 workflow and accounts - 2026-09-30

Local Windows checks: **188 backend tests passed**, one Windows symlink-privilege skip;
**36 desktop/mobile browser tests passed**. Application coverage: 91% with the same worker
exclusion described below. Ruff lint/format, mypy, Prettier and Compose configuration passed.
Python and npm dependency audits reported no known vulnerabilities. Screenshots of the
populated library and account dialog were inspected; they contain synthetic examples only.

New evidence covers atomic guest/account budgets, concurrent admissions, cookie reset,
history removal, account deletion/re-registration, job limit snapshots, idempotent requests,
legacy guest-session migration, unavailable worker rejection, owned Range/HEAD previews,
live response leases during cleanup, locked-file retry and cleanup during a busy worker.
Child-process tests prove OAuth and unrelated credentials are excluded from their environment.

Account tests cover session rotation, guest-job/usage migration, all-device logout, deletion,
callback replay, missing browser binding, provider mismatch, expired state, cancelled consent,
timeouts and sanitized errors. Google protocol fixtures exchange a code with PKCE and verify
real RSA-signed JWTs, including invalid signature/algorithm/issuer/audience/nonce/expiry/azp.
Facebook fixtures verify app, subject, token type and both expirations. These are **offline
protocol fixtures, not real Google/Facebook account acceptance**.

Browser cases cover retries, early-deletion confirmation, preview-node/focus preservation,
expired-session recovery, lost POST responses, preferences without saved source URLs, account
logout and displayed limits. Initial, failure/help, populated and account-dialog states had no
serious/critical axe findings. Provider OAuth credentials and a public callback hostname are
not configured. No public deployment or live social sign-in is claimed.

The v0.2 provider evidence below remains dated evidence. Extraction was not upgraded in v0.3.
An additional v0.3 live check through the actual API/session/runner/worker/file path succeeded
for Facebook `watch/?v=106560053808006`: MP4 95,280 bytes (H.264/AAC, 224 x 400) and MP3
79,973 bytes. ffprobe verified both and all temporary media was removed. An initial incomplete
`/videos/{id}/` input was rejected as invalid; the supported watch URL above was used.
The full Linux suite and actual Docker build/start are checked in GitHub CI; consult the PR
and main workflow runs for their exact commit rather than treating local tests as hosted proof.

## v0.2.0 local checks - 2026-09-30

Environment: Windows, Python 3.13.15, Node 24.21.0, yt-dlp 2026.8.19 with curl-cffi 0.16.3,
FFmpeg 9.0.2.
All media produced during live checks was held in temporary directories and removed.

| Check                     | Result                                                    |
| ------------------------- | --------------------------------------------------------- |
| Python backend suite      | 138 passed; 1 symlink test skipped for Windows privilege  |
| Real synthetic conversion | Landscape/portrait MP4 and MP3 passed; dimensions/codecs/duration probed |
| Browser suite             | 16 passed, desktop and mobile                             |
| Accessibility             | No serious/critical axe findings in initial UI and expanded help/failure state |
| Ruff lint/format          | Passed                                                    |
| mypy                      | Passed for application modules                            |
| Python dependency audit   | No known vulnerabilities reported                         |
| npm dependency audit      | No vulnerabilities reported                               |
| Compose configuration     | Parsed successfully                                       |
| Local Docker runtime      | Not run: Docker Desktop engine was not running            |

The browser tests control API responses; they prove UI behavior, not provider availability.
Backend tests use real temporary SQLite databases and child processes. Media conversion tests
serve generated one-second media on a loopback HTTP fixture and use actual yt-dlp/FFmpeg.
Additional cases cover exact social URL boundaries, per-hop redirect validation, collection
rejection before entry traversal, explicit extractor routing, provider ownership isolation,
silent-source MP3 rejection, missing/invalid/over-limit duration, and preserved orientation.
Application coverage was 89%; the isolated worker is exercised by real-media tests but excluded
from that numeric coverage setting. Screenshots were inspected at desktop and mobile sizes.

## Live YouTube check - 2026-09-30 (repeated for v0.2.0)

Command: `uv run python -m scripts.live_smoke https://www.youtube.com/watch?v=aqz-KE-bpKQ`

Source: official Blender Foundation **Big Buck Bunny 60fps 4K** upload. This was a live request
through the actual HTTP application, queue, worker, and attachment endpoint. ffprobe inspected
the bytes delivered by that endpoint.

| Output          | Size             | Verified streams      | Outcome  |
| --------------- | ---------------- | --------------------- | -------- |
| MP4, up to 360p | 25,787,748 bytes | AV1 video + AAC audio | Complete |
| MP3, 192 kbps   | 15,232,111 bytes | MP3 audio             | Complete |

An earlier attempt against the old yt-dlp test video `BaW_jenozKc` failed because YouTube reports
that video unavailable. The application reported a controlled provider error. The successful
check above used an available source; availability of arbitrary videos is not guaranteed.

## Live Facebook and Instagram checks - 2026-09-30

The same HTTP/queue/worker/attachment smoke and ffprobe verification used public URLs from
the locked upstream extractor's test fixtures. No account cookies were supplied. All media
was temporary and removed after the check.

| Source | Output | Verified result |
| --- | --- | --- |
| Facebook video `106560053808006` | MP4, up to 360p | 95,280 bytes; H.264 + AAC; 224 x 400, no upscaling |
| Same Facebook video | MP3, 192 kbps | 79,973 bytes; MP3 audio |
| Facebook `/reel/106560053808006/` | MP4 | Complete through real Reel-to-video delegation |
| Instagram Reel `Chunk8-jurw` | MP4, up to 360p | 416,385 bytes; H.264; 360 x 640 |
| Instagram post `aye83DjauH` | MP4, up to 360p | 411,980 bytes; H.264; 360 x 360 |
| Tested Instagram sources | MP3 | No audio rendition supplied; controlled `audio_unavailable`, no completed file |

Instagram did not supply duration for the tested Reel. The final media-duration check passed
without weakening deadline or byte limits. The older Instagram TV fixture `BkfuX9UB-eK` returned
a controlled provider error for both formats; it is not recorded as a success.

**Live Instagram MP3 with an audio-bearing source remains unverified.** The shared MP3 worker
path passes real synthetic tests and live YouTube/Facebook checks. Share-link resolution passes
deterministic redirect tests; arbitrary live share URLs and hosted provider access are not
claimed as verified.

## CI and hosting

The initial bootstrap commit `d937115` passed [CI run 36750311046](https://github.com/KasheK420/yt-downloader/actions/runs/36750311046):
the full Linux suite including symlink verification, dependency audits, browser tests,
and a real Docker build/start/readiness smoke. Both languages passed
[CodeQL run 36750311047](https://github.com/KasheK420/yt-downloader/actions/runs/36750311047).
Commit `52d85de` passed [CI run 36751095078](https://github.com/KasheK420/yt-downloader/actions/runs/36751095078)
with **53 backend tests and 8 browser tests**, including three worker-policy regression cases for
excessive/missing duration and live media. Its
[CodeQL run](https://github.com/KasheK420/yt-downloader/actions/runs/36751095306) also passed.
Consult [the latest workflow runs](https://github.com/KasheK420/yt-downloader/actions) for the
actual commit's results. A workflow definition alone is not evidence of a passing run.

No production instance, public domain, tunnel route, multi-user load acceptance, or host-specific
YouTube access was deployed or verified during the repository bootstrap. Those checks belong to
the Public launch milestone.
