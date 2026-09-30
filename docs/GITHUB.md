# GitHub setup

Repository: https://github.com/KasheK420/yt-downloader (public), default branch `main`.
The initial application bootstrap was committed directly to the new repository. Subsequent
contributions should use focused pull requests.

## Repository settings

- Issues and Projects capability enabled; wiki disabled because documentation is versioned.
- Squash merging enabled; merge commits and rebase merging disabled.
- Automatic head-branch deletion after merge; auto-merge is available after required checks.
- Main requires current successful Quality and tests, Dependency audit, Container smoke,
  and both CodeQL language checks. Pull requests and resolved conversations are required.
- Stale reviews are dismissed. Zero mandatory approvals supports a solo maintainer.
- Main disallows force pushes and deletion, and requires linear history.
- The owner retains the standard administrator bypass; rules are not enforced on administrators.
- Actions tokens default to read-only and cannot approve PRs. Release-specific permissions
  are scoped to its manual publication job.
- Secret scanning, secret push protection, Dependabot alerts/security fixes, and private
  vulnerability reporting are enabled. CodeQL is configured in the repository.
- CODEOWNERS names KasheK420. Issue forms and a PR template are included.

## Work tracking

[Public launch milestone](https://github.com/KasheK420/yt-downloader/milestone/1):

- [Hosting, HTTPS, and edge limits](https://github.com/KasheK420/yt-downloader/issues/7)
- [Provider and multi-user acceptance](https://github.com/KasheK420/yt-downloader/issues/8)
- [Monitoring and incident response](https://github.com/KasheK420/yt-downloader/issues/10)

A separate GitHub Projects board was not created: the local CLI token lacks the `read:project`
scope, and no authentication scope was changed during bootstrap. Issues/milestones are fully
usable without a board. Creating one later requires a token with the appropriate project scope.

Dependabot may immediately propose upgrades. These are review requests, not automatic merges.
Runtime major upgrades and lockfile changes still need review and full verification. The
manual Release workflow is ready, but its presence does not mean a release/image was published.
