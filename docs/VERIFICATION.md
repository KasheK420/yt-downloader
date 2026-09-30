# Verification evidence

## Local checks - 2026-09-30

Environment: Windows, Python 3.13.15, Node 24.21.0, yt-dlp 2026.8.19, FFmpeg 9.0.2.
All media produced during live checks was held in temporary directories and removed.

| Check                     | Result                                                    |
| ------------------------- | --------------------------------------------------------- |
| Python backend suite      | 52 passed; 1 symlink test skipped for Windows privilege   |
| Real synthetic conversion | MP4 and MP3 through yt-dlp/FFmpeg passed; codecs probed   |
| Browser suite             | 8 passed, desktop and mobile                              |
| Accessibility             | No serious/critical axe findings in the tested initial UI |
| Ruff lint/format          | Passed before repository publication                      |
| mypy                      | Passed for application modules                            |
| Python dependency audit   | No known vulnerabilities reported                         |
| npm dependency audit      | No vulnerabilities reported                               |
| Compose configuration     | Parsed successfully                                       |
| Local Docker runtime      | Not run: Docker Desktop engine was not running            |

The browser tests control API responses; they prove UI behavior, not provider availability.
Backend tests use real temporary SQLite databases and child processes. Media conversion tests
serve generated one-second media on a loopback HTTP fixture and use actual yt-dlp/FFmpeg.

## Live YouTube check - 2026-09-30

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
