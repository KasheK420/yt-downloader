# Deployment and operations

## Private installation

Use the default `compose.yaml`. It exposes only `127.0.0.1:8080`, runs as UID/GID 10001,
has a read-only root filesystem, drops capabilities, and mounts one named data volume.
CPU is capped at 1.5 cores, RAM at 1 GiB, and processes at 128. FFmpeg and Node are bundled.

```sh
docker compose up --build -d --wait
curl --fail http://127.0.0.1:8080/readyz
```

For remote private access, keep the listener private and use an SSH tunnel or an authenticated
private reverse proxy/VPN. There is no application login screen. Do not expose the raw port
on the internet. The bootstrap has not modified any server, DNS record, or public tunnel.

## Public reverse proxy without login

The application can serve anonymous visitors, but public deployment is a separate operator
change. Use a host with enough temporary disk, an explicit data-volume quota, and monitoring.

1. Choose the hostname and place HTTPS in front of the service. Preserve Host and forward
   X-Forwarded-Proto accurately. The application needs the correct external scheme for Origin checks.
2. Set `PUBLIC_HOST` and `TRUSTED_PROXY_IP` in the operator's `.env`. The latter must be the actual
   immediate reverse proxy IP, never `*` and never arbitrary client-provided forwarded addresses.
3. Adapt `deploy/compose.proxy.example.yaml` to the actual Docker network. It removes the host
   port mapping and serves only on the existing `proxy-net`. It enables Secure cookies and a
   specific forwarded-header trust source. Recent Compose v2 supporting `!reset` is required.
4. Configure the proxy to forward to `downloader:8000`. If using an outbound tunnel, route the
   tunnel through that proxy; do not open an additional public application port.
5. Normalize the real client IP at the trusted edge. Verify that a visitor cannot spoof
   X-Forwarded-For to evade quotas. Otherwise all users share the proxy's rate limit.
6. Add edge request-rate limits, connection/download limits, and a small upload body limit.
   Apply host firewall/container egress rules that prevent reaching private/link-local networks
   if running untrusted public traffic. Application URLs are restricted to approved YouTube,
   Facebook, and Instagram video/share paths.
7. Verify the public-host checks below before announcing availability.

```sh
docker compose -f compose.yaml -f deploy/compose.proxy.example.yaml config --quiet
docker compose -f compose.yaml -f deploy/compose.proxy.example.yaml up --build -d --wait
```

Example `.env` additions (replace with real deployment values):

```dotenv
PUBLIC_HOST=downloads.example.com
TRUSTED_PROXY_IP=172.30.0.10
```

Keep `localhost` and `127.0.0.1` in allowed hosts for the container health check.
The application has one worker per data directory. Do not add replicas or Uvicorn workers.

## Public-host acceptance

- HTTPS, correct host allowlist, Secure/HttpOnly/SameSite cookies, and CSP are present.
- A normal same-origin job is accepted; a foreign Origin is rejected.
- Two separate browser profiles cannot read, cancel, or download each other's jobs.
- Directly spoofed forwarded headers do not change the rate-limit identity.
- A real video and MP3 download from each enabled provider succeed from the deployment host
  and pass ffprobe. Use a source with an audio track when checking MP3.
- Cancellation, timeout, restart, expiry, and volume limits behave correctly under load.
- The raw application port is unreachable externally and file responses are never cached.
- Monitor process readiness, disk usage, memory, job failures, and abuse. Confirm rollback.

Datacenter IPs may be rate-limited or challenged by providers. Local success does not establish
provider availability from a future server. This app has no cookie-upload, account-bypass,
or arbitrary provider configuration endpoint.

## Updates and rollback

Review dependency updates and rebuild:

```sh
git pull --ff-only
docker compose build --pull
docker compose up -d --wait
```

Record the old source commit/image ID first. To roll back, check out the prior release in a
separate clean deployment checkout and recreate using its image and Compose configuration.
Back up the data volume before a future database-schema migration. Schema version 0.1.0 is
created on first run and has no destructive upgrade step. Version 0.2.0 reuses that schema;
existing YouTube jobs and signing keys remain compatible.

The manual Release workflow accepts a version matching `pyproject.toml`, checks successful CI
for that exact commit, publishes `ghcr.io/kashek420/yt-downloader:<version>`, and creates a GitHub
release. Running it is an explicit maintainer action. It does not deploy or restart a server.
Image visibility is a separate GHCR package setting; verify it after the first publication.

## Data and troubleshooting

- `/data/jobs.sqlite3`: job metadata and short-lived hashed-IP rate records.
- `/data/session.key`: signing secret. Preserve it to retain browser access across restarts.
- `/data/media/<random-id>/`: temporary download and completed output.
- `/healthz`: liveness; `/readyz`: worker and runtime availability.

`provider_error` can indicate unavailable/private media or upstream extraction changes. First
try a known public video and check the installed yt-dlp version. Upgrade the pinned dependency
with `uv lock --upgrade-package yt-dlp --upgrade-package yt-dlp-ejs`, rerun all tests, then run
an authorized live smoke. Do not silently install unreviewed nightly builds or disable limits.

`runtime_unavailable` means FFmpeg, ffprobe, or the JS runtime is missing in a native install.
`storage_full` means retained media prevents reserving another job; wait for expiry or lower
usage. A startup lock error means another process owns this data directory. Stop that process
before restarting; do not remove an active lock and run two workers.

Native verification writes no production data. Public-provider smoke uses a temporary directory
and deletes its media. Normal CI uses generated synthetic fixtures and never contacts providers.
