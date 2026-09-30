# HTTP API

Same-origin, session-cookie API. No CORS and no account/login flow. All responses use `no-store`.
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
| DELETE     | `/api/jobs/{id}`      | Cancel an active job and return its state; terminal jobs are unchanged      |
| GET / HEAD | `/api/jobs/{id}/file` | Completed attachment or status                                              |

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
| 403  | `invalid_origin` or missing mutation header                                    |
| 404  | `job_not_found`; includes another visitor's jobs and expired jobs              |
| 409  | `file_not_ready`                                                               |
| 410  | `file_expired`; metadata exists but output is gone or unsafe                   |
| 413  | `request_too_large`                                                            |
| 422  | `invalid_request`                                                              |
| 429  | `rate_limit`, `session_limit`, `queue_full`; includes conservative Retry-After |
| 503  | `runtime_unavailable`, `storage_full`                                          |

Terminal job errors: `provider_error`, `processing_error`, `duration_limit`, `live_unsupported`,
`size_limit`, `timeout`, `interrupted`, `storage_full`, `playlist_unsupported`, `link_unresolved`,
`audio_unavailable` (the provider offers no audio track for an MP3 request).
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
