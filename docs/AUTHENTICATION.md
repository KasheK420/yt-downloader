# Optional accounts and social sign-in

Guests can download without registering. The first successful Google or Facebook sign-in
creates a free account. Gmail and YouTube are Google identities, not additional login
providers. Sign-in grants access to this application's library; it does not authorize
downloading private media, reading Gmail, or accessing a YouTube channel.

The integration is implemented and tested with isolated protocol fixtures. **Real Google
and Facebook acceptance requires operator-owned OAuth applications and a callback origin.**
No production OAuth credentials, provider-console configuration, or live user login was
created or verified during this change. Unconfigured providers are hidden in the UI.

## Enable a provider

1. Choose the exact externally reachable origin, such as `https://downloads.example.com`.
   Add its hostname to `YTD_ALLOWED_HOSTS`, set `YTD_SECURE_COOKIES=true`, and configure
   trusted reverse-proxy headers as described in [deployment](DEPLOYMENT.md).
2. Set `YTD_PUBLIC_ORIGIN` to that origin, with no path, query or fragment. Login must start
   on this exact origin so the browser-bound callback cookie can return to the same host.
3. Create an application in the provider's console. Copy the credentials into the ignored
   operator `.env`, never an issue, PR, browser code or committed Compose file.
4. Configure the exact callback URL below. Use the public app homepage and
   `/static/privacy.html` for the privacy/data-deletion instructions. The operator must
   add their actual contact and infrastructure retention policy before public launch.
5. Complete the provider's current testing/review/publication requirements. Test accounts
   in a development app are not proof that arbitrary public accounts can sign in.

| Provider | Configuration | Registered callback |
| --- | --- | --- |
| Google | `YTD_GOOGLE_CLIENT_ID`, `YTD_GOOGLE_CLIENT_SECRET` | `/auth/google/callback` |
| Facebook | `YTD_FACEBOOK_CLIENT_ID`, `YTD_FACEBOOK_CLIENT_SECRET` | `/auth/facebook/callback` |

Example callback: `https://downloads.example.com/auth/google/callback`.
Google requires a **Web application** OAuth client and consent/branding configuration.
Facebook requires Facebook Login enabled in a Meta developer app, with the callback
allowlisted. `YTD_FACEBOOK_API_VERSION` pins Graph API calls; review its lifecycle when
upgrading. Follow the current Meta console for supported local development and app review.

For Google local testing, an explicitly registered origin such as `http://localhost:8080`
can be configured with Secure cookies disabled. Open that hostname consistently; mixing
`localhost` and `127.0.0.1` loses the callback binding. Arbitrary public HTTP origins are
rejected. `YTD_REQUIRE_LOGIN=true` is optional and fails startup without a configured provider.
The default remains guest access plus optional sign-in.

## Protocol and session boundaries

- Authorization-code flow. Authlib validates Google ID token signature, issuer, audience,
  timestamps and nonce; PKCE S256 binds the exchanged code. No implicit browser token flow.
- Facebook validates token type, app ID, user ID and expiration via `debug_token`, then
  requests only `id,name` with `appsecret_proof` and verifies the same subject.
- Scopes are `openid profile` for Google and `public_profile` for Facebook. No email scope,
  offline access, refresh tokens, media access, provider cookies or password registration.
- Random one-use state is bound to a separate HttpOnly, SameSite=Lax browser cookie with a
  10-minute expiry. State, verifier and nonce are server-side. Callback replay, provider
  mismatch, missing binding, cancelled consent, timeout and revoked sessions fail closed.
- Local session cookies are opaque random tokens, HttpOnly and SameSite=Strict. Only their
  hashes are stored. A session lasts a fixed 7 days from creation/sign-in and is revoked on
  logout. Reading session metadata does not reissue the cookie or extend its expiry.
- Login rotates the guest session and atomically transfers its jobs and quota usage to the
  account. Separate sign-ins from another device reach the same owned library.
- Identity is provider plus subject. Google and Facebook are separate accounts even if
  they use the same email address; account linking is deliberately not implemented.
- No provider token is saved or returned to the frontend. Provider responses are not logged.
  Downloader children receive a restricted environment without OAuth client secrets.

All mutating endpoints require the same-origin custom request header. Login starts are
limited to 10 per 10 minutes per hashed peer address; new sessions to 30 per 10 minutes.
These controls complement, rather than replace, edge connection/rate limits.

## Logout and deletion

The account dialog supports local logout, logout on all devices, and account deletion.
Deleting an account revokes every local session, removes identity data, cancels its work
and expires its media. Cleanup records persist only until files can be removed. An already
accepted media transfer may finish. Quota counters retain a pseudonymous stable identifier
until their time window expires, so deletion/re-registration cannot reset the allowance.

Removing provider consent in Google/Meta does not notify this app's existing local sessions;
use **Sign out all devices** or **Delete account** here as well. Provider revocation callbacks,
cross-provider linking and administrator account management are not implemented. Backups and
reverse-proxy logs remain the operator's responsibility. Keep access logging disabled or
redact `/auth/*/callback` query strings, cookies and authorization headers.

## Hosted acceptance

Verify each configured provider with a real allowed test account and then an ordinary public
account: accept and reject consent, open an expired callback, replay it, log out, sign in on
a second device, and delete the account. Confirm guest jobs transfer, foreign jobs remain
inaccessible, quotas persist, and no OAuth tokens appear in browser storage or logs.
Provider-console screenshots and credentials must remain private.

References: [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect),
[Authlib Starlette integration](https://docs.authlib.org/en/v1.6.9/client/starlette.html),
[Meta login flow](https://developers.facebook.com/docs/facebook-login/manually-build-a-login-flow/),
[Meta token debugging](https://developers.facebook.com/docs/graph-api/reference/debug_token/).
Meta documentation returned HTTP 429 during this local run; final console requirements and
public-app approval are explicitly part of hosted acceptance, not inferred as completed.
