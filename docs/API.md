# HTTP API

Same-origin, session-cookie API with optional social accounts. No CORS. Responses use `no-store`.
Call `GET /api/session` and preserve the `ytd_session` HttpOnly cookie before using job routes.
POST and DELETE require `X-Requested-With: yt-downloader`. JSON request bodies are capped at 4 KiB.

| Method     | Path                  | Result                                                                      |
| ---------- | --------------------- | --------------------------------------------------------------------------- |
| GET        | `/healthz`            | Process liveness                                                            |
| GET        | `/readyz`             | 200 if worker, FFmpeg, ffprobe, and JS runtime are available; otherwise 503 |
| GET        | `/api/session`        | Cookie plus duration/file/retention limits and readiness                    |
| GET        | `/api/jobs`           | Up to 50 unexpired jobs for this browser, newest first                      |
| POST       | `/api/jobs`           | 202 and a queued job                                                        |
| GET        | `/api/jobs/{id}`      | Owned job status                                                            |
| DELETE     | `/api/jobs/{id}`      | Active: cancel and return job (200). Terminal: expire/remove it (204) |
| POST       | `/api/jobs/{id}/retry` | Failed/cancelled job: create another attempt under the same admission rules (202) |
| GET / HEAD | `/api/jobs/{id}/file` | Completed attachment or status                                              |
| GET / HEAD | `/api/jobs/{id}/preview` | Owned inline media; supports byte ranges (206) |
| POST       | `/api/auth/{provider}` | Google/Facebook authorization URL and short-lived binding cookie |
| GET        | `/auth/{provider}/callback` | Consume bound state and validate identity; redirect to fixed local result page |
| POST       | `/api/logout` | Revoke current session, clear cookie (204); `?all_devices=true` revokes all account sessions |
| DELETE     | `/api/account` | Delete signed-in account, revoke sessions, cancel work and remove media (204) |

## Create job

```json
{
  "url": "https://www.youtube.com/watch?v=abcdefghijk",
  "kind": "mp4",
  "quality": 720
}
```

`kind` is `mp4` with quality 360/720/1080, or `mp3` with quality 128/192/320. Unknown fields
are rejected. A playlist query alongside a video ID is discarded: only the video is processed.
The URL may point to YouTube, Facebook, or Instagram; see [SOURCES.md](SOURCES.md).
The session response includes `providers: ["youtube", "facebook", "instagram"]`.
It also includes `tier`, `account` (name/provider or null), `login_providers` (only configured
providers), `login_required`, `plans`, `max_active`, `max_quality`, `quota` and `server_time`.
Quota contains `limit`, `remaining`, `window_seconds` and `resets_at` (Unix seconds or null).
Read the effective quality ceiling before submitting; public guest defaults stop at 720p.

Creation and retry accept an optional `Idempotency-Key` header (16-80 ASCII letters, digits,
underscore or hyphen). Repeating the same key/input for the same owner returns its original
unexpired job without charging again. Reusing it for different input returns
`idempotency_conflict`; a removed/expired original returns `request_expired`. Keys and quota
records expire after the maximum configured quota window, at least 24 hours.

Job fields: `id`, `provider`, `kind`, `quality`, `state`, `title`, `progress`, `error`, `file_bytes`,
`created_at`, `expires_at`. Timestamps are Unix seconds. Progress is a provider estimate and
may reset between separate audio/video streams. Conversion is indeterminate. No API response
contains the source URL, anonymous owner, peer address, or filesystem path.

## Errors

```json
{ "detail": "session_limit" }
```

| HTTP | Codes / meaning                                                                |
| ---- | ------------------------------------------------------------------------------ |
| 400  | Unrecognized Host header                                                       |
| 401  | `session_required`                                                             |
| 403  | `invalid_origin`, `quality_limit`, `login_required`, `account_required`, `login_origin_mismatch` |
| 404  | `job_not_found`; includes another visitor's jobs and expired jobs              |
| 409  | `file_not_ready`, `retry_unavailable`, `idempotency_conflict`, `request_expired`, `already_signed_in` |
| 410  | `file_expired`; metadata exists but output is gone or unsafe                   |
| 413  | `request_too_large`                                                            |
| 422  | `invalid_request`                                                              |
| 429  | `rate_limit`, `quota_exhausted`, `ip_daily_limit`, `auth_rate_limit`, `session_limit`, `queue_full`; includes Retry-After |
| 503  | `runtime_unavailable`, `storage_full`, `login_unavailable` |

Terminal job errors: `provider_error`, `processing_error`, `duration_limit`, `live_unsupported`,
`size_limit`, `timeout`, `interrupted`, `storage_full`, `playlist_unsupported`, `link_unresolved`,
`audio_unavailable` (the provider offers no audio track for an MP3 request), `queue_timeout`.
The collection and share-link codes mean a collection was returned or a share link did not
resolve to an approved direct video. Provider errors can mean unavailable, private, restricted, rate-limited, or
changed provider behavior; raw provider details are withheld.

## Local curl example

```sh
curl -c session.txt http://localhost:8080/api/session
curl -b session.txt -H 'Content-Type: application/json' \
  -H 'X-Requested-With: yt-downloader' \
  -d '{"url":"https://www.youtube.com/watch?v=abcdefghijk","kind":"mp3","quality":192}' \
  http://localhost:8080/api/jobs
```

Replace the example ID with your video. Treat `session.txt` as a credential and delete it
when done; never add it to a commit or issue.
