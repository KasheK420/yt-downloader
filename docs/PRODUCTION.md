# Hosted instance

## Status — 2026-10-02

The guest instance is available at **https://ytdown.majorluk.cz** on the owner's
existing Contabo VPS. It runs application version **0.3.1**, source commit
`ee44569230d24da24fc5c84f1058a4d2a93deecf`. The exact commit passed
[CI](https://github.com/KasheK420/yt-downloader/actions/runs/36777482492) and
[CodeQL](https://github.com/KasheK420/yt-downloader/actions/runs/36777482469).

**Provider acceptance is incomplete.** The tested YouTube source returns
"Sign in to confirm you're not a bot" from the VPS. Facebook MP4/MP3 and
Instagram MP4 passed through the public HTTPS service. Do not describe YouTube
as working on this host, or mistake a green readiness check for provider availability.
No browser cookies, residential proxy, or account credentials were added to the downloader.

Guest access is enabled. Google/Facebook sign-in remains unconfigured and its buttons
are hidden. OAuth activation is tracked in [issue #15](https://github.com/KasheK420/yt-downloader/issues/15).
The operator has created the dedicated Google project `ytdown-majorluk-prod` and
a web OAuth client with the exact production callback. Provider-side setup alone
does not prove hosted login; runtime credentials and live acceptance remain pending.

The bounded media benchmark and public-growth constraints are recorded in
[CAPACITY.md](CAPACITY.md). Its synthetic timings must not be presented as a
multi-user or live-provider load test.

## Runtime and resource limits

Public requests pass through Cloudflare Tunnel, the existing Nginx Proxy Manager,
and the application container. There is no published application port. Only this
hostname was added; existing tunnel routes and proxy hosts were preserved.

| Control | Deployed value |
| --- | --- |
| CPU / memory / processes | 1 CPU, 1 GiB RAM, no additional swap, 128 PIDs |
| Processing / queue | One worker; six queued or running jobs maximum |
| Guest budget | Three submissions per hour, shared by source IP |
| Guest output | Up to 720p, 30 minutes, 250 MiB; one active job |
| Global output / job work directory | 500 MiB / 1 GiB |
| Retained media budget | 4 GiB, with admission reserving space for the next job |
| Persistent filesystem | Separate 6 GiB ext4 loop filesystem |
| Retention | One hour; cleanup every 15 seconds |
| Proxy limits | 4 KiB request bodies, 5 requests/second with burst 40 |
| Connections / media streams | Eight concurrent requests and three media streams per IP |
| Download bandwidth | 4 MiB/second per stream after the first MiB |

The container uses UID/GID 10001, a read-only root, dropped capabilities,
`no-new-privileges`, and bounded temporary storage and logs. Its dedicated Docker
network blocks new connections to private, link-local, and host administration
addresses. Only the existing reverse proxy can initiate the cross-network HTTP route.
Firewall rules also preserve the proxy's source IP so Uvicorn trusts exactly that peer.

The proxy accepts this virtual host only from the tunnel connector. It normalizes
the client IP from Cloudflare's header, replaces forwarded headers, redirects HTTP
to HTTPS, and sends HSTS. The application sends CSP and Secure/HttpOnly/SameSite=Strict
session cookies. Media responses are streamed without disk buffering or caching.
Access logging is disabled in the application's proxy locations.

## Hosted evidence

| Check | Result |
| --- | --- |
| Public HTTPS, homepage and readiness | Passed, certificate verification enabled |
| Facebook MP4 | 157,400 bytes, H.264/yuv420p + AAC, full decode passed |
| Facebook MP3 | 76,518 bytes, MP3, full decode passed |
| Instagram Reel MP4 | 416,629 bytes, H.264, full decode passed; source is silent |
| Owned preview | Byte range returned 206 and exactly the requested bytes |
| Separate guest sessions | Other session received 404 for job metadata and file |
| Foreign Origin / oversized body / arbitrary source URL | Rejected with 403 / 413 / 422 |
| Shared IP budget | Fourth submission rejected with 429, including spoofed forwarded IP headers |
| Spoofed Cloudflare client-IP header | Rejected by the edge with 403 |
| Bypassing the tunnel with forged headers | Rejected by the proxy with 403 |
| Container egress | Private administration and metadata destinations blocked; public HTTPS works |
| Service/firewall dependency restart | Readiness recovered; five complete files, metadata and session key preserved |
| SQLite backup | Integrity check passed; corresponding session key verified |
| Public browser UI | Desktop 1440 px and mobile 390 px; no script errors or horizontal overflow |
| Local regression suite | 201 backend tests passed; one Windows symlink test skipped; 36 browser tests passed |

Provider checks used the previously documented public fixtures. No provider media or
session credentials are committed. These checks do not prove every URL, sustained
concurrent load, live social sign-in, Instagram MP3 with an audio-bearing source,
host reboot, or a deliberate fill-to-capacity storage test. Provider access remains
tracked in [issue #8](https://github.com/KasheK420/yt-downloader/issues/8).

## Operator handoff

The private deployment directory is `/opt/docker/yt-downloader` on Contabo:

- `source/`: clean checkout pinned to the application commit above.
- `compose.yaml`: deployed resource/network configuration, without public ports.
- `data/`: mounted persistent filesystem; `storage/data.ext4` is its backing file.
- `firewall.py`: narrowly scoped, idempotent rules for this container and proxy route.
- `healthcheck.py`: readiness/storage checks; restarts a repeatedly unhealthy container.
- `backup.py`: consistent SQLite backup plus the matching session key and Compose file.
- `backups/`: private deployment/configuration snapshots and daily metadata backups.

The locally built image is `majorluk/yt-downloader:0.3.1-ee44569`, with image ID
`sha256:2e47d9668fca4d7686565b5f73e154a54db1df88e191d55c3fc8c0c7d142cf44`.
It is present on the VPS. Docker Hub rejected private repository creation with HTTP 403;
registry publication and automatic image delivery are **not configured**. Do not assume
that this tag can be pulled on a replacement host. Build the pinned source when recovering.
Watchtower is disabled for this service; updates are intentional operator actions.

```sh
systemctl status yt-downloader --no-pager
docker inspect --format '{{json .State.Health}}' yt-downloader
docker stats --no-stream yt-downloader
df -h /opt/docker/yt-downloader/data
journalctl -u yt-downloader -u yt-downloader-health --since '30 minutes ago'
systemctl list-timers 'yt-downloader-*'
```

Systemd starts the application only after Docker, the required data mount, and its
firewall. The application is restarted after a process exit. A one-minute health timer
checks readiness and storage; Docker's healthcheck must already report `unhealthy`
before the timer restarts it. Uptime Kuma was explicitly omitted at the owner's request;
external uptime notifications are not configured.

Daily metadata backups run around 02:45 Europe/Prague, retain seven copies, and are
root-readable only. Temporary media is not backed up. A backup restore must preserve
the database/session-key pair and expire jobs whose media is no longer available.
The initial backup was opened and checked independently after creation.

For an update: record the current image/configuration, create a metadata backup, build
and verify a reviewed source commit, update the image reference, and restart only
`yt-downloader.service`. Recheck the public API, proxy isolation, and provider downloads.
Do not restart the whole Docker infrastructure or enable unrelated stopped services.

For an application rollback, restore the previous image/configuration and compatible
database/key pair as documented in [DEPLOYMENT.md](DEPLOYMENT.md). For this first
deployment, emergency withdrawal is `systemctl stop yt-downloader.service`, followed by
removal of only this hostname's tunnel/DNS/proxy entries. Preserve the data filesystem
and private backups. Never replace the entire shared tunnel configuration with an old
snapshot without reconciling other applications' changes.
