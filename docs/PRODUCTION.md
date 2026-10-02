# Hosted instance

## Status — 2026-10-02

The instance is available at **https://ytdown.majorluk.cz** on the owner's
existing Contabo VPS. It runs application version **0.3.1**, source commit
`7c90d17c3086fd21dfe13ce2705d81bf1b6b2b9c`. The exact commit passed
[CI](https://github.com/KasheK420/yt-downloader/actions/runs/37042288416) and
[CodeQL](https://github.com/KasheK420/yt-downloader/actions/runs/37042288687).

**Provider acceptance is incomplete.** The tested YouTube source returns
"Sign in to confirm you're not a bot" from the VPS. Facebook MP4/MP3 and
Instagram MP4 passed through the public HTTPS service. Do not describe YouTube
as working on this host, or mistake a green readiness check for provider availability.
No browser cookies, residential proxy, or account credentials were added to the downloader.

Guest access and optional **Google sign-in are enabled**. The dedicated Google project
`ytdown-majorluk-prod` uses an External / In production audience and a web client whose
only callback is `https://ytdown.majorluk.cz/auth/google/callback`. It requests only
`openid profile`; the operator owns the project and visitors use their own accounts.
Real consent, successful login, logout and repeat login passed with one operator-owned
Google account. The account library and consumed allowance persisted across logout/login.
The Google consent page displayed the domain `majorluk.cz`; no custom-brand verification
or broader permission review is claimed.

Facebook sign-in remains unconfigured and hidden. A second ordinary Google account,
second device, live consent rejection, callback replay/expiry and account deletion were
not exercised in this hosted session. The corresponding offline protocol/session tests
remain separate evidence. [Issue #15](https://github.com/KasheK420/yt-downloader/issues/15)
stays open for the remaining provider setup and acceptance.

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
| Free Google account | 20 submissions per rolling 24 hours; two active jobs; 1080p, 120 minutes, 500 MiB |
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
| Google sign-in | Real consent, login, logout and repeat login passed; account history and allowance preserved |
| Google audience | External / In production; only non-sensitive identity/profile scopes configured |
| OAuth recovery | Root-only environment file included in verified metadata backups; no credentials committed |
| Public browser UI | Desktop 1440 px and mobile 390 px; no script errors or horizontal overflow |
| Local regression suite | 201 backend tests passed; one Windows symlink test skipped; 36 browser tests passed |

Media-provider checks used the previously documented public fixtures on image `ee44569`;
the Google/privacy update does not change media processing. No provider media or
session credentials are committed. These checks do not prove every URL, sustained
concurrent load, Facebook sign-in, the remaining Google cases above, Instagram MP3 with an audio-bearing source,
host reboot, or a deliberate fill-to-capacity storage test. Provider access remains
tracked in [issue #8](https://github.com/KasheK420/yt-downloader/issues/8).

## Operator handoff

The private deployment directory is `/opt/docker/yt-downloader` on Contabo:

- `source/`: clean checkout pinned to the application commit above.
- `compose.yaml`: deployed resource/network configuration, without public ports.
- `oauth.env`: root-owned mode 0600 Google client configuration, referenced by Compose.
- `data/`: mounted persistent filesystem; `storage/data.ext4` is its backing file.
- `firewall.py`: narrowly scoped, idempotent rules for this container and proxy route.
- `healthcheck.py`: readiness/storage checks; restarts a repeatedly unhealthy container.
- `backup.py`: consistent SQLite backup plus the matching session key, Compose file and OAuth environment.
- `backups/`: private deployment/configuration snapshots and daily metadata backups.

The locally built image is `majorluk/yt-downloader:0.3.1-7c90d17`, with image ID
`sha256:5d189c827d1bed3ff4df1e1b8a677821e0978d8e1b502229865b9ea8c404e398`.
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
the database/session-key pair, restore `oauth.env` with mode 0600, and expire jobs whose
media is no longer available. Backups created before Google activation do not include
OAuth configuration. The latest activation backup was independently checked for SQLite
integrity, matching session key and OAuth configuration, and private file permissions.
The backups are on the same VPS and do not replace an off-host disaster-recovery copy.

For an update: record the current image/configuration, create a metadata backup, build
and verify a reviewed source commit, update the image reference, and restart only
`yt-downloader.service`. Recheck the public API, proxy isolation, and provider downloads.
Do not restart the whole Docker infrastructure or enable unrelated stopped services.
Probe readiness inside the container at `http://127.0.0.1:8000/readyz` or through the
public HTTPS endpoint with a normal operator User-Agent. A direct host request to the
container IP is outside the allowed route and is not a valid deployment health probe.
The first Google activation attempt used that incorrect probe and rolled back; the
corrected probe and subsequent activation passed without relaxing the firewall.

For an application rollback, restore the previous image/configuration and compatible
database/key pair as documented in [DEPLOYMENT.md](DEPLOYMENT.md). For this first
deployment, emergency withdrawal is `systemctl stop yt-downloader.service`, followed by
removal of only this hostname's tunnel/DNS/proxy entries. Preserve the data filesystem
and private backups. Never replace the entire shared tunnel configuration with an old
snapshot without reconciling other applications' changes.
