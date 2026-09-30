# Configuration

Native runs read `.env` and environment variables. Compose explicitly maps the values below;
it always uses `/data` inside the container and the bundled FFmpeg/Node executables.

| Variable                     | Default                             | Purpose                                               |
| ---------------------------- | ----------------------------------- | ----------------------------------------------------- |
| `BIND_ADDRESS`               | `127.0.0.1`                         | Compose host binding                                  |
| `PORT`                       | `8080`                              | Compose host port                                     |
| `YTD_DATA_DIR`               | `.data`                             | Native data directory; Compose uses `/data`           |
| `YTD_ALLOWED_HOSTS`          | `["localhost","127.0.0.1","[::1]"]` | JSON array of accepted HTTP hosts                     |
| `YTD_SECURE_COOKIES`         | `false`                             | Set true for HTTPS deployments                        |
| `YTD_FFMPEG_LOCATION`        | unset                               | Native FFmpeg/ffprobe directory, optional             |
| `YTD_JS_RUNTIME`             | `node`                              | Native runtime: `node` or `deno`; Docker bundles Node |
| `YTD_MAX_ACTIVE_PER_SESSION` | `2`                                 | Concurrent queued/running jobs per browser            |
| `YTD_MAX_QUEUE`              | `12`                                | Global queued/running jobs                            |
| `YTD_RATE_LIMIT`             | `5`                                 | Accepted submissions per peer address/window          |
| `YTD_RATE_WINDOW_SECONDS`    | `600`                               | Shared peer-address burst window |
| `YTD_MAX_DURATION_SECONDS`   | `7200`                              | Maximum source duration                               |
| `YTD_MAX_FILE_BYTES`         | `524288000`                         | Final output limit (500 MiB)                          |
| `YTD_MAX_JOB_BYTES`          | `1073741824`                        | Working-directory limit (1 GiB)                       |
| `YTD_MAX_STORAGE_BYTES`      | `5368709120`                        | Total media limit (5 GiB)                             |
| `YTD_JOB_TIMEOUT_SECONDS`    | `1800`                              | Worker deadline                                       |
| `YTD_RETENTION_SECONDS`      | `3600`                              | Terminal job/media retention                          |
| `YTD_CLEANUP_INTERVAL_SECONDS` | `15` | Independent cleanup/retry interval (0.05-300 seconds) |
| `YTD_MAX_QUEUE_WAIT_SECONDS` | `1800` | Deadline for jobs still waiting in the queue |
| `YTD_PUBLIC_MODE` | `false` | Enable separate guest/free budgets; public proxy example sets true |
| `YTD_REQUIRE_LOGIN` | `false` | Require an account for new jobs; needs a configured OAuth provider |
| `YTD_PUBLIC_ORIGIN` | unset | Exact callback origin; HTTPS except explicitly configured localhost |
| `YTD_GOOGLE_CLIENT_ID` | unset | Web application OAuth client ID |
| `YTD_GOOGLE_CLIENT_SECRET` | unset | Server-only Google client secret |
| `YTD_FACEBOOK_CLIENT_ID` | unset | Meta developer app ID |
| `YTD_FACEBOOK_CLIENT_SECRET` | unset | Server-only Meta app secret |
| `YTD_FACEBOOK_API_VERSION` | `v26.0` | Pinned Graph API version |
| `YTD_GUEST_DOWNLOADS` | `3` | Guest attempts per window, shared by peer address |
| `YTD_GUEST_WINDOW_SECONDS` | `3600` | Guest rolling budget window |
| `YTD_FREE_DOWNLOADS` | `20` | Account attempts per window, shared across devices |
| `YTD_FREE_WINDOW_SECONDS` | `86400` | Account rolling budget window |
| `YTD_GUEST_MAX_DURATION_SECONDS` | `1800` | Guest duration ceiling, capped by global ceiling |
| `YTD_GUEST_MAX_FILE_BYTES` | `262144000` | Guest final-output ceiling (250 MiB), capped globally |
| `YTD_GUEST_MAX_QUALITY` | `720` | Guest MP4 quality ceiling; choices remain 360/720/1080 |
| `YTD_PUBLIC_IP_DAILY_LIMIT` | `40` | All public-tier attempts per peer address over 24 hours |

Public guests get at most one active job, free accounts at most two, both capped by
`YTD_MAX_ACTIVE_PER_SESSION`. Guest/free windows are configurable up to 7 days. Pseudonymous
quota/idempotency records are retained for the longest configured window, at least 24 hours,
then pruned by maintenance. Session hashes last up to 7 days after renewal; login state lasts
10 minutes. Empty optional OAuth environment values are treated as unset. Supplying only
part of a provider configuration fails startup. HTTPS origins require Secure cookies.
See [AUTHENTICATION.md](AUTHENTICATION.md) for callback setup and [LIMITS.md](LIMITS.md) for policy.

Configuration requires positive limits and `max_file_bytes <= max_job_bytes <= max_storage_bytes`.
The session cookie is renewed for 7 days; media expires much sooner. Keep localhost in allowed
hosts for container health checks when adding a public hostname. Never use a wildcard host on
a public instance. Job filenames/paths and raw yt-dlp options are not configurable by visitors.

Restart after changing settings. Do not use multiple workers or multiple instances sharing a
data directory. Session keys are generated automatically; do not put one in source control.
