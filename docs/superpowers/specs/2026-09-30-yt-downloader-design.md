# YouTube downloader design

## Intent and acceptance

The owner requested a new web application, local repository, public GitHub repository,
complete repository setup, and documentation. It accepts a YouTube link and produces
video or MP3 audio. Initially it is used privately; later it may be public without login.
Ownership is KasheK420 and the repository name is yt-downloader.

The delivery includes a working application, tests, Docker packaging, CI, security and
contribution documentation, issue/PR templates, releases, and a concrete public-launch
roadmap. Creating the public source repository is authorized. Publishing a live public
service or changing existing infrastructure is outside this bootstrap.

## Architecture and alternatives

Use one FastAPI application, a static HTML/CSS/JavaScript frontend, SQLite job metadata,
and one asynchronous queue runner. Each media job executes a separate Python process
using yt-dlp and FFmpeg. Node.js supplies the supported yt-dlp JavaScript runtime.

A React frontend would add a build pipeline without improving this small workflow.
A Redis/Celery deployment could scale workers later but adds operational dependencies
without helping the initial single-user installation. A browser-only implementation
cannot reliably fetch and convert YouTube media under browser network constraints.

## User flow

Paste a standard YouTube, youtu.be, Shorts, or live-video URL. Choose MP4 (up to 360p,
720p, or 1080p) or MP3 (128, 192, or 320 kbps). Submit, see queue/processing progress,
cancel an active request, and download the result. Actual available quality depends on
the source. Show useful provider-failure and expiry messages. No playlists or ongoing
live streams in this release. One-click Czech/English language switch.

The visual direction is a quiet recording-desk interface: deep blue ink #142B49,
cool paper #F3F6FA, white #FFFFFF, blue #315FEA, steel #64758B, and amber #B8751F.
Use system sans type with a large left-aligned title, one prominent link entry, and
a segmented media selector. The active queue is a functional list below the form.
No remote fonts, analytics, remote thumbnails, or external UI assets.

## Isolation and lifecycle

A random anonymous browser session uses a signed HttpOnly SameSite cookie. Every job
read, cancellation, list, and file download checks ownership; unknown and foreign IDs
both return 404. A persistent local signing secret lives outside git in the data directory.
Mutating API requests require a custom header and reject foreign Origin headers.
Only configured Host headers are accepted. No CORS is enabled.

Canonicalize accepted URLs to `https://www.youtube.com/watch?v=<11-character-id>`.
Reject credentials, nonstandard ports, extra paths, unsupported hosts, duplicate IDs,
and playlist-only links. Never pass the original input to a shell or downloader.

Default limits: 2 active jobs per browser, 12 globally, 5 submissions per IP per
10 minutes, 2-hour source duration, 500 MiB final file, 1 GiB job workspace, 5 GiB
aggregate media storage, 30-minute job deadline, and 1-hour terminal retention.
Use one worker and check workspace growth while downloading/converting. Enforce queue
and rate limits atomically in SQLite. Hash client addresses before retaining rate entries.
Expired metadata and files are removed. Interrupted jobs become failed on restart;
unclaimed files are removed. Cancellation, timeouts, and shutdown terminate the process
tree and remove partial files. A data-directory lock prevents multiple schedulers.

## Operations and evidence

Docker runs as an unprivileged user, drops capabilities, uses a read-only root filesystem,
and exposes localhost by default. The writable data volume contains the database, secret,
and temporary media. Health endpoints separate process liveness from runtime readiness.
Public launch requires HTTPS, correct allowed hosts, Secure cookies, trusted proxy/IP
configuration, edge request limits, and verification on the eventual host.

Unit/integration tests cover URL normalization, ID isolation, CSRF, queue/rate/storage
limits, expiry, restart recovery, cancellation, and safe file delivery. Real FFmpeg
conversion uses locally generated synthetic audio/video. Browser tests cover the main
flow and responsive UI. A separate optional live YouTube smoke reports provider results
honestly; deterministic tests never establish live provider or hosting acceptance.
