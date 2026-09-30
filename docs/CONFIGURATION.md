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
| `YTD_RATE_WINDOW_SECONDS`    | `600`                               | Rate window and hashed-address retention              |
| `YTD_MAX_DURATION_SECONDS`   | `7200`                              | Maximum source duration                               |
| `YTD_MAX_FILE_BYTES`         | `524288000`                         | Final output limit (500 MiB)                          |
| `YTD_MAX_JOB_BYTES`          | `1073741824`                        | Working-directory limit (1 GiB)                       |
| `YTD_MAX_STORAGE_BYTES`      | `5368709120`                        | Total media limit (5 GiB)                             |
| `YTD_JOB_TIMEOUT_SECONDS`    | `1800`                              | Worker deadline                                       |
| `YTD_RETENTION_SECONDS`      | `3600`                              | Terminal job/media retention                          |

Configuration requires positive limits and `max_file_bytes <= max_job_bytes <= max_storage_bytes`.
The session cookie is renewed for 7 days; media expires much sooner. Keep localhost in allowed
hosts for container health checks when adding a public hostname. Never use a wildcard host on
a public instance. Job filenames/paths and raw yt-dlp options are not configurable by visitors.

Restart after changing settings. Do not use multiple workers or multiple instances sharing a
data directory. Session keys are generated automatically; do not put one in source control.
