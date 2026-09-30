# YouTube downloader implementation plan

**Goal:** Deliver a complete public repository and runnable private-first downloader.
**Architecture:** One FastAPI service serves a static UI and owns a SQLite-backed job
queue. A child process performs each download and conversion. Docker packages runtimes.
**Tech stack:** Python 3.13, FastAPI, SQLite, yt-dlp, FFmpeg, Node.js, native browser JS.
**Spec:** ../specs/2026-09-30-yt-downloader-design.md
**Execution:** Implement in this session. The user's request authorizes the repository
bootstrap and implementation; future production exposure remains a separate action.

## Global constraints

Keep the repository public and free of local credentials/media. Single application
process, one worker, anonymous owner isolation, localhost deployment by default.
Source changes and verification results belong in the handoff documentation.

## Review focus

1. Deceptive hosts and ambiguous video IDs must never reach the provider (task 1).
2. A second visitor must not read, cancel, or download another visitor's job (task 2).
3. Cancellation/restart/expiry must not leave a running child or retained media (task 3).
4. Unknown media sizes and long conversion stages must stay within limits (task 3).
5. Failed requests and expired downloads must recover clearly in the UI (task 4).

## Task 1: Input boundary and reproducible environment

Files: pyproject.toml, uv.lock, app/config.py, app/urls.py, tests/test_urls.py.
Interface: `normalize_url(value: str) -> str`; `Settings` supplies validated limits.

- [ ] Write URL acceptance/rejection tests, run and observe failure.
- [ ] Implement canonicalization and validated environment settings.
- [ ] Run focused tests, lock dependencies, commit the input boundary.

## Task 2: Owned persistent jobs and HTTP contract

Files: app/store.py, app/main.py, tests/test_api.py, tests/test_store.py.
Interfaces: `Store.create(owner, client_key, url, kind, quality) -> dict`,
`Store.get(job_id, owner) -> dict | None`, `create_app(settings) -> FastAPI`.

- [ ] Write failing API/store tests for CSRF, isolation, rate limits, and expiry.
- [ ] Implement SQLite transactions and safe owned-file serving.
- [ ] Verify quota concurrency and restart behavior with real temporary databases.

## Task 3: Worker, cleanup, and bounded conversion

Files: app/runner.py, app/worker.py, tests/test_runner.py, tests/test_media.py.
Interfaces: `Runner.start()`, `Runner.stop()`, `Runner.cancel(job_id)`;
child process emits JSON metadata/progress/result events on stdout.

- [ ] Write process-lifecycle and directory-limit tests before implementation.
- [ ] Implement killable yt-dlp process, conversion, bounded logs, quotas, and cleanup.
- [ ] Verify with local process fixtures and synthetic FFmpeg media.
- [ ] Run an optional live provider smoke and record actual result separately.

## Task 4: Responsive browser workflow

Files: app/static/index.html, app/static/app.js, app/static/styles.css,
tests/browser.spec.mjs, package.json, playwright.config.mjs.

- [ ] Define browser tests for submit, failure, cancellation, language, and mobile layout.
- [ ] Implement accessible form, status polling, progress, expiry, and downloads.
- [ ] Run browser tests and inspect desktop/mobile screenshots.

## Task 5: Operations, docs, and GitHub

Files: Dockerfile, compose.yaml, .env.example, .github/, README.md, docs/,
LICENSE, SECURITY.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md, CHANGELOG.md.

- [ ] Document configuration, API, deployment, architecture, maintenance, and evidence.
- [ ] Add lint/types/test/audit/build CI and a manually triggered release workflow.
- [ ] Run complete checks and audit staged content for secrets/artifacts.
- [ ] Create public repository, push, configure metadata/security/main protection,
      labels and public-launch milestone/issues, and verify remote state and CI.
