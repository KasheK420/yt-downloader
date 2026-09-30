# Free access, limits and failure cases

There are no paid tiers or payment collection. `YTD_PUBLIC_MODE=false` retains the private
instance defaults: up to 1080p, 120 minutes, 500 MiB, two active jobs and five accepted
submissions per 10 minutes per peer address. The public proxy example enables public mode.

## Default public policy

| Budget | Guest | Free account |
| --- | --- | --- |
| Accepted attempts | 3 per rolling hour, shared by IP | 20 per rolling day, shared across devices/IPs |
| Active queued/running jobs | 1 per browser | 2 per account |
| MP4 quality ceiling | 720p | 1080p |
| Source duration | 30 minutes | 120 minutes |
| Final output | 250 MiB | 500 MiB |
| MP3 quality | 128 / 192 / 320 kbps | 128 / 192 / 320 kbps |
| Completed file retention | 60 minutes | 60 minutes |

All tiers also share the IP burst limit (5 per 10 minutes), the public IP daily cap (40),
global queue (12), one running worker, job deadline (30 minutes), queue-wait deadline
(30 minutes), working directory ceiling (1 GiB) and total media ceiling (5 GiB).
Global operator ceilings always cap the effective policy. The UI displays effective
duration, size, quality, remaining allowance and next quota slot from the server.

Budgets use rolling windows, not calendar-midnight resets. Rejected requests do not consume
download quota. Every accepted attempt does, including cancellation, a provider failure or a
retry. Removing history, clearing cookies or deleting/recreating an account does not refund it.
Guest usage transfers into the account's budget on login. The per-IP counters stay intact.
Configure values in [CONFIGURATION.md](CONFIGURATION.md); restart to apply settings.

An optional `Idempotency-Key` on creation/retry makes a network retry return the original
job rather than charge/create another one. Reusing the same key with different input fails.
The browser retains this key in memory after an ambiguous connection failure; it does not
automatically retry POST requests. Successful retries of a failed job use a new key.

## Failure behavior

| Case | Behavior |
| --- | --- |
| Invalid, foreign, collection or private-media URL | Controlled rejection; no arbitrary extractor or host access |
| Provider challenge, unavailable media or changed extraction | Actionable failure; retry consumes a new attempt |
| No audio track | `audio_unavailable`; choose MP4 for a silent video |
| Missing source duration | Final ffprobe duration check; byte/time ceilings remain active |
| Oversize, over-duration or timeout | Worker terminates; partial files are removed or cleanup is retried |
| Quality unavailable / portrait source | Use available source, keep orientation, downscale without upscaling |
| Source uses AV1, HEVC, unusual pixels or non-AAC audio | Convert affected streams to H.264/yuv420p and AAC; retain dimensions within the ceiling |
| Damaged compressed frames despite readable metadata | Full decode fails; report `processing_error` without publishing a completed file |
| Browser still cannot play normalized media | Inline-player explanation; attachment still available |
| Session expires or connectivity drops | Bounded requests, coalesced session recovery, poll backoff and manual reconnect |
| Anonymous cookie is lost | Guest history cannot be recovered; IP allowance remains. Accounts can sign in again |
| File expires between a click and response | Controlled 404/410; never navigate into raw provider errors |
| File expires during a transfer | Existing streaming lease finishes; new requests are denied |
| Locked file / failed removal | Hide expired history immediately; retain cleanup metadata and retry every 15 seconds |
| Long download in progress | Separate maintenance task still expires old files and waiting jobs |
| App restart | Queued/running jobs fail with `interrupted`; retained completed media survives |
| Two browser tabs / devices | Atomic SQL admission shares account/IP limits; polling reconciles changes |
| Account deleted while callback is outstanding | Callback cannot resurrect a revoked originating session |
| Repeated OAuth failures | Bounded state lifetime, one-use binding, callback timeout and login-start rate limit |

The security and behavior matrix is exercised by backend/protocol and desktop/mobile tests.
It is not a claim that every provider or browser failure is eliminated. Shared NAT users
share IP limits, while VPNs and multiple provider accounts cannot be perfectly tied to a
single person without additional controls. Public deployments need trusted client-IP handling,
edge abuse controls, disk quotas, monitoring and load/provider acceptance on their actual host.
No CAPTCHA or distributed quota store is included. The supported topology is one process.
