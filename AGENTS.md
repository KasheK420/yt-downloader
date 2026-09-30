# Working on yt-downloader

This repository is owned by KasheK420. Keep code, documentation, commits, issues,
and pull requests in English. The UI supports Czech and English.

## Workflow

- Read README.md, docs/ARCHITECTURE.md, and docs/HANDOFF.md before changing behavior.
- Use focused branches and conventional commits after the initial repository bootstrap.
- Write behavioral tests for URL validation, job ownership, limits, lifecycle, and downloads.
- Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
  `uv run pytest`, and `npm test` before proposing a change.
- Stage explicit paths. Never commit secrets, media, cookies, personal history, or `.env` files.
- Do not add AI co-author trailers to commits.
- Keep dependencies locked with `uv.lock` and `package-lock.json`.
- Distinguish synthetic tests from live YouTube verification and deployed acceptance.

## Boundaries

- Single application process and one download worker. Do not increase Uvicorn workers.
- Accept only canonicalized single-video YouTube URLs; never accept arbitrary download URLs,
  shell arguments, yt-dlp options, cookie uploads, or filesystem paths from clients.
- Preserve anonymous session ownership, request-origin checks, quotas, timeouts, cleanup,
  and safe output path checks. Provider error messages are not public API responses.
- Deployment defaults to localhost. Public exposure is a separate operator action described
  in docs/DEPLOYMENT.md. Do not change production infrastructure without task authorization.
- Keep provider requests out of normal CI; live smoke testing is an explicit local command.
