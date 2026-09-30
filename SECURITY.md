# Security policy

## Reporting

Use [GitHub private vulnerability reporting](https://github.com/KasheK420/yt-downloader/security/advisories/new)
or email majoros.lukas@pm.me. Include reproduction steps, affected versions, and impact. Do not
post vulnerabilities, credentials, cookies, private links, or sensitive logs in public issues.
The latest `main` and latest release receive fixes. No response-time SLA is promised.

## Application boundaries

- Only explicit YouTube, Facebook, and Instagram video hosts/paths are accepted and canonicalized.
- Share-link redirects are bounded and validated before each request. Extractor delegation stays
  within the same approved provider. Generic extraction and collection traversal are disabled.
- Client input never becomes shell commands, yt-dlp options, cookie files, or output paths.
- Every job endpoint checks a signed anonymous owner cookie. A job ID alone grants no access.
- Mutation requests require a custom same-origin header; foreign Origin values are rejected.
- Host allowlisting, CSP, attachment responses, request size limits, and no CORS reduce browser exposure.
- One child process per job is bounded by deadline and monitored storage usage; cancellation and
  shutdown terminate its process tree. Docker additionally bounds RAM, CPU, PIDs, and root writes.
- API failures contain stable error codes, not provider tracebacks or signed media URLs.
- Session keys, SQLite data, and media stay in the ignored data directory or Docker volume.

## Limits of these controls

Anonymous per-session limits can be reset by clearing cookies. IP limits are secondary controls,
not a complete abuse defense: shared addresses group legitimate visitors, and distributed clients
can evade them. Public deployment needs edge controls and realistic load verification.
Application storage checks run periodically and are not filesystem quotas; bound the data volume
at the host when running a hostile public workload. Container isolation is not a VM boundary.

Files expire from the application's storage. This is ordinary deletion, not guaranteed secure
erasure from snapshots, underlying storage, browser downloads, or administrator backups.
Use HTTPS and Secure cookies when accessing the service beyond localhost. Browser cookies are
bearer credentials; someone with a valid session cookie can access that session's files.

## Data and retention

Stored data consists of canonical video URL, format, quality, title, job state/timestamps,
temporary media, an anonymous owner identifier, and a short-lived keyed hash of the peer address.
Terminal jobs and files expire after one hour by default; rate records expire after ten minutes.
No analytics, remote fonts, thumbnails, user accounts, or third-party frontend scripts are used.
Outgoing media requests go to the selected provider (YouTube, Facebook, or Instagram) and its
media infrastructure. No browser credentials or account cookies are imported. Unknown source
duration is checked with ffprobe before completion; size/time limits still bound the download.

See [deployment guidance](docs/DEPLOYMENT.md) before making an instance public.
