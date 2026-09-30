# Supported sources

One link produces one MP4 video or MP3 audio file. Content must be accessible to the server
without a provider account. No credentials, browser cookies, or private-account sessions are
accepted. MP3 requires an audio track; silent videos remain downloadable as MP4.

## Accepted link forms

| Provider | Direct links | Share links |
| --- | --- | --- |
| YouTube | `youtube.com/watch?v=VIDEO_ID`, `/shorts/VIDEO_ID`, `/live/VIDEO_ID`, `/embed/VIDEO_ID`, `youtu.be/VIDEO_ID` | The same forms with tracking parameters |
| Facebook | `facebook.com/watch/?v=ID`, `/video.php?v=ID`, `/PAGE/videos/ID/`, `/PAGE/videos/TITLE/ID/`, `/reel/ID/` | `fb.watch/TOKEN/`, `facebook.com/share/v/TOKEN/`, `/share/r/TOKEN/` |
| Instagram | `instagram.com/reel/CODE/`, `/reels/CODE/`, `/p/CODE/`, `/tv/CODE/`, and username-prefixed equivalents | `instagram.com/share/TOKEN/`, `/share/reel/TOKEN/` |

The exact host allowlist is in `app/urls.py`. Mobile YouTube and Facebook hosts are normalized
to the canonical host. HTTP input is upgraded to HTTPS; tracking queries/fragments are removed.
Facebook numeric IDs and Instagram shortcodes are validated before invoking provider code.

Share links use at most five redirects in the isolated worker. Each destination is validated
before requesting it, must stay within the original provider, and must resolve to a recognized
video path. Login pages, generic redirectors, foreign hosts, loops, and share pages that require
JavaScript navigation are rejected. If a share link fails, open it in a browser and copy the
direct video/Reel URL. No arbitrary page scraping fallback is enabled.

## Single-video boundary

Profiles, playlists, Stories, feeds, photo-only posts, and multi-item albums/carousels are not
supported. Instagram `/p/` can refer to either a video or a carousel; the extractor result is
checked before entries can be traversed. A carousel returns `playlist_unsupported`, even if it
contains only one video among several photos. Download individual videos with direct links.

Only the explicit YouTube, Facebook, FacebookReel, and Instagram extractors may be selected.
Extractor URL delegation is revalidated; a provider-supplied extractor key cannot opt into
generic extraction. No new API endpoints or authentication flows are needed.

## Quality and resource limits

The requested MP4 resolution is a maximum on the shorter edge. A 9:16 Reel at 720p is up to
720 x 1280; landscape 16:9 is up to 1280 x 720. Prefer source renditions near that limit and
downscale only when necessary. Never upscale. The original aspect ratio remains intact.

Known excessive source duration is rejected before transfer. Some Instagram responses omit
duration: transfer remains bounded by the existing job deadline and byte/disk caps, then
ffprobe validates actual MP4/MP3 duration before the job can complete. Unknown or excessive
final duration fails closed. Transcoding consumes the same per-job workspace and time budget.

## Provider availability

Anonymous access varies by video, provider, region, rate limits, and hosting IP. Supporting a
URL does not guarantee that the provider will deliver its media. Use the dated evidence in
[VERIFICATION.md](VERIFICATION.md) to distinguish URL/UI tests, real conversions, live-provider
checks, and deployment acceptance. Repeat live checks from the eventual hosting environment.

The locked yt-dlp version includes its `curl-cffi` transport extra for supported anonymous
requests. Upstream implementation references:
[Facebook](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/extractor/facebook.py) and
[Instagram](https://github.com/yt-dlp/yt-dlp/blob/2026.08.19/yt_dlp/extractor/instagram.py).

```sh
uv run python -m scripts.live_smoke 'https://www.facebook.com/reel/VIDEO_ID/'
uv run python -m scripts.live_smoke 'https://www.instagram.com/reel/CODE/' --kind mp4
```

Normal CI never contacts providers. Live checks use temporary storage and remove media afterward.
