# Contributing

Read [AGENTS.md](AGENTS.md) and [the architecture](docs/ARCHITECTURE.md) first.
Open an issue for changes that add a new provider, distributed workers, accounts, or a
new public API. Small fixes can go directly into a pull request.

1. Create a focused branch from `main`.
2. Reproduce a bug with a behavioral test before fixing it.
3. Make the smallest complete change and update relevant documentation.
4. Run all commands in README's verification section. State any unavailable checks.
5. Open a PR with the problem, resulting behavior, and relevant evidence.

Use conventional commit subjects such as `feat: add ...`, `fix: handle ...`, or `docs: explain ...`.
Keep source, docs, commits, and GitHub discussions in English. User-facing text lives in both
language dictionaries. Do not commit generated media, secrets, browser cookies, or local logs.
Do not add AI co-author trailers.

Python packages are managed with uv and `uv.lock`; JavaScript packages are development-only
browser/format tooling managed with npm and `package-lock.json`. Do not add a frontend framework
or an additional service without an agreed need.

CI runs deterministic tests, formatting, type checking, dependency audits, and a container smoke.
Report live YouTube checks separately; a provider outage is not a successful integration test.
Security issues belong in [private vulnerability reporting](SECURITY.md).
