# Capacity and product decisions

Measured on 2026-10-02. This is a planning baseline, not a multi-user load-test
result or an availability guarantee. See [PRODUCTION.md](PRODUCTION.md) for the
deployed controls and provider acceptance.

## Current capacity

The shared Contabo host has four CPUs and about 8 GiB RAM. At inspection it had
about 4.3 GiB available RAM, 92 GiB available host disk, and load averages below
0.6. The downloader is deliberately limited to one CPU and 1 GiB RAM. Host spare
capacity is shared with other applications and is not dedicated downloader capacity.

One worker processes a job at a time; the deployed queue admits at most six
queued/running jobs. Web visitors and transfers of already prepared files do not
each require a processing worker. Simultaneous web/API capacity has not been
load-tested. Do not translate a visitor count directly into download capacity.

A bounded, network-disabled benchmark used the deployed image
`sha256:2e47d9668fca4d7686565b5f73e154a54db1df88e191d55c3fc8c0c7d142cf44`,
one CPU, 1 GiB RAM, and a disposable 256 MiB temporary filesystem. It ran in a
separate container, called the production `fit_video` implementation, and left
the production container healthy. The source was a locally generated 30-second
1080p30 `testsrc2` clip with synthetic audio. No provider was contacted.

| Operation | Measured wall time |
| --- | --- |
| Fixture generation, excluded from service estimates | 28.366 s |
| 1080p to H.264 720p, including full output decode | 32.758 s |
| Compatible 720p remux, including full output decode | 5.017 s |
| MP3 192 kbps conversion and metadata probe | 0.669 s |

For this workload, linear extrapolation to a ten-minute clip gives roughly
11 minutes for conversion, 100 seconds for compatible MP4, or 13 seconds for
MP3 processing. These are estimates, not measurements of ten-minute media.
Provider metadata requests, source transfers, contention and retries add time.
Codec, frame rate, resolution and image complexity change the results.

For one worker, theoretical jobs/hour is `3600 / mean processing-job seconds`.
Plan below saturation: at 60% utilization, a 60-second mean permits about 36
jobs/hour, 180 seconds about 12, and 660 seconds about 3.3. Use a measured
whole-job mean for the actual traffic mix, including provider failures. A small
beta of tens of daily users is a sensible starting cohort; it is not a tested
maximum, particularly if everyone requests long videos at once.

Storage can bind earlier. Admission requires current media plus a 1 GiB working
reservation to fit within 4 GiB. Roughly 3 GiB of retained outputs therefore
leaves room for the next job: about 30 files at 100 MiB, or 12 at 250 MiB.
Exact admission depends on current temporary files and active transfers. Files
normally expire after one hour. The six-job queue is a burst buffer, not extra
processing capacity.

## Before expanding public traffic

Measure complete jobs and success rates separately for each provider/format;
record queue wait and service time percentiles, stored bytes and egress. Avoid
recording source links or personal identifiers in aggregate capacity metrics.
The hosted YouTube probe currently fails a provider bot challenge. Google login
to this app does not resolve that challenge.

Public traffic currently passes through Cloudflare. Its
[video delivery policy](https://developers.cloudflare.com/fundamentals/reference/policies-compliances/delivering-videos-with-cloudflare/)
restricts video/large-file delivery through the general CDN without an appropriate
service. Do not assume this tunnel/proxy setup provides unrestricted free media
delivery or that `no-store` provides an exemption. Before a substantial public
rollout, confirm the applicable service terms and select an appropriate media
delivery path. No paid service was activated for this assessment.

Scale worker throughput separately from the web application. Increasing Uvicorn
workers is unsupported. Multiple media workers require an explicit queue/storage
design and shared admission, ownership and quota controls. Raising guest/account
limits alone does not add capacity.

## Login, payments and extension

Google/Facebook authenticate individual visitors. The operator's provider account
owns the OAuth application; it is not the account used by every visitor. First
sign-in creates the visitor's local account. Google covers Gmail and YouTube
identities without a separate YouTube login. Guest use remains available.

Paid credits are a possible later feature, not currently implemented. Keep paid
credit accounting separate from abuse attempt counters. Reserve credits at
admission, settle only a successfully prepared file, release reservations on
failure/cancellation, and reconcile interruption cases. A transaction ledger and
idempotent verified payment webhooks are required. Show the price before a job;
base it on measured service cost rather than promising unlimited downloads.
Provider reliability and payment-provider acceptance must precede sales. For
example, [Stripe prohibits services facilitating intellectual-property infringement](https://stripe.com/legal/restricted-businesses).

AdSense is not a sound default for this product: Google's
[Publisher Policies](https://support.google.com/adsense/answer/10502938?hl=en)
exclude pages enabling streaming-video downloads prohibited by the content
provider. No AdSense acceptance or revenue is assumed.

A browser companion could forward a user-selected supported page/link to the web
app, prefill the form, and reuse its account/limits. Use narrow permissions such
as [activeTab](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab),
an explicit user action and no provider-cookie collection. Processing would still
use VPS capacity. Chrome Web Store rules prohibit
[unauthorized access/download of copyrighted media](https://developer.chrome.com/docs/webstore/program-policies/malicious-and-prohibited);
store approval is separate from technical feasibility. No extension or payment
integration has been implemented as part of this assessment.
