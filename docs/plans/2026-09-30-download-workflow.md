# Download workflow and optional free accounts

## Scope

Keep anonymous downloads available. Add optional Google and Facebook sign-in;
Gmail and YouTube use the same Google identity. First sign-in creates a free
account. No passwords, paid tiers, provider cookies, or private-media access.
Provider credentials and an exact callback origin are operator configuration.
Unconfigured providers must not present working login buttons.

Improve the complete job lifecycle: retry, early removal, owned inline preview,
expiry, connection recovery, and cleanup that survives locked files. Preserve
ownership and quotas during retries, login, logout, and account deletion.

## Product decisions

- Local personal mode preserves existing media limits; public mode enables guest
  and free-account budgets. All ceilings remain operator-configurable.
- Public defaults: guests 3 submissions per rolling hour, 1 active job, 720p,
  30 minutes and 250 MiB; free accounts 20 per rolling day, 2 active jobs,
  1080p, 2 hours and 500 MiB. Global/IP burst and storage limits apply to both.
- Rejected requests do not consume quota. Accepted attempts, including retries,
  cancellations and provider failures, do consume it. Removing history does not
  refund quota. Surface the remaining budget and reset time before submission.
- Authentication uses server-side revocable sessions, one-use state bound to a
  short-lived browser cookie, Google OIDC validation with nonce and PKCE, and
  Facebook token validation. Provider tokens are never persisted or sent to UI.
- Identity is provider + subject, never email matching. No automatic cross-provider
  linking. Guest jobs move once to the account on successful login.
- Account deletion revokes all sessions, cancels owned jobs, expires media and
  removes identity data. Short-lived pseudonymous abuse counters retain their TTL.
- Progress polling never recreates an open media player or moves keyboard focus.
- Transient cleanup failures keep database metadata until physical deletion works;
  periodic maintenance runs independently from long downloads.

## Visual direction

Preserve the light blue identity: background #f3f6fa, ink #142b49, blue #315fea,
muted #586b81 and border #dae2ed. System fonts, compact header and hero, two-column
composer/library on desktop and a single column on mobile. Add a concise account
and budget panel, stable library cards, filters, and native media controls.
Use accessible dialogs for destructive actions. No autoplay or third-party embeds.

## Implementation and evidence

1. Regression tests for file leases, failed cleanup, periodic expiry and retry.
2. Shared media lifecycle, atomic budget admission and per-job limit snapshots.
3. Optional social login, session/account lifecycle, isolated OAuth protocol tests.
4. Browser UX, quota display, preferences, retry/remove/preview and recovery.
5. Keyboard/mobile/accessibility tests, full backend/static checks and dependency
   audit. Review synthetic screenshots. Document verified and unverified boundaries.
6. Publish a focused PR, wait for CI, merge and refresh the local preview.

Public deployment and real provider-console acceptance remain separate from local
proof. No claim that every possible external-provider edge case can be eliminated.
