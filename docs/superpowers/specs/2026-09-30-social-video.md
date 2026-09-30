# Social video support

Extend the existing private-first, anonymous downloader to YouTube, Facebook, and
Instagram without changing ownership or deployment. Keep the repository name.

## Behavior

- One input accepts direct video and Reel links from the three providers.
- Canonicalize exact approved hosts and video paths; discard tracking parameters.
- Resolve Facebook `fb.watch` and `/share/v/`, `/share/r/` links and Instagram
  `/share/` links with a bounded redirect chain inside the isolated worker.
  Validate each destination before requesting it; never follow a foreign host,
  login page, profile, or generic redirect endpoint.
- Reject playlists, carousels, and multi-video extraction before downloading media.
- Produce MP4 or MP3 using the existing queue, ownership, quotas, and cleanup.
  Fit portrait video quality to its shorter edge without upscaling.
- Identify the provider in job responses and cards. Explain supported link forms
  and failures in Czech and English. Do not accept account credentials or cookies.

## Verification

Start with URL, redirect, collection rejection, and API regression tests. Exercise
real yt-dlp/FFmpeg against synthetic landscape and portrait media. Run desktop and
mobile browser flows and accessibility checks. Keep live-provider outcomes separate
from local evidence; successful extraction is dependent on anonymous provider access.

## Implementation sequence

1. URL/source boundary and redirect tests, then implementation.
2. Single-video extraction and portrait output, with actual media tests.
3. Provider-aware UI, browser tests, and updated operator documentation.
4. Review, full checks, focused pull request, required GitHub checks, local preview.
