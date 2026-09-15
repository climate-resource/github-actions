# Changelog

Versions follow [Semantic Versioning](https://semver.org/) (`<major>.<minor>.<patch>`).

Backward incompatible (breaking) changes will only be introduced in major versions
with advance notice in the **Breaking Changes** section of releases.

While a release of `vX.Y.Z` tag is immutable.
Each release also updates the corresponding `vX` and `vX.Y` tags to make it easier to follow the latest changes.

<!--
You should *NOT* be adding new changelog entries to this file,
this file is managed by towncrier. See changelog/README.md.

You *may* edit previous changelogs to fix problems like typo corrections or such.
-->

<!-- towncrier release notes start -->

## github-actions v1.7.1 (2026-09-15)

### Trivial/Internal Changes

- [#32](https://github.com/climate-resource/github-actions/pull/32)


## github-actions v1.7.0 (2026-09-08)

### Features

- Adds a shared action to notify Flux after publishing a service image. ([#31](https://github.com/climate-resource/github-actions/pull/31))


## github-actions v1.6.1 (2026-08-31)

No significant changes.


## github-actions v1.6.0 (2026-08-24)

### Features

- Added a `dynamic-versioning` input to the `bump-version` action and the `bump.yaml` reusable workflow.
  Projects whose version is derived from git tags (e.g. hatch-vcs) can now be released by the tag alone,
  with no version edit in `pyproject.toml` and no post-tag pre-release commit. ([#30](https://github.com/climate-resource/github-actions/pull/30))


## github-actions v1.5.1 (2026-08-21)

No significant changes.


## github-actions v1.5.0 (2026-08-21)

### Features

- Added support for `yarn`, `npm` and `pnpm` projects for the bump action using the new `project-type` input parameter. All three Node types read and bump `package.json` through the `npm version` CLI and differ only in the lockfile `lock: true` refreshes: `yarn install --mode=update-lockfile`, `npm install --package-lock-only`, or `pnpm install --lockfile-only`. ([#27](https://github.com/climate-resource/github-actions/pull/27))

### Improvements

- Moved `bump-version`'s logic out of `action.yml` and into a self-contained `bump-version/bump.py`, run via `uv run --script`. ([#27](https://github.com/climate-resource/github-actions/pull/27))

### Bug Fixes

- Fixed pre-release detection in `bump-version`, which matched a bare `a`, `b`, `rc` or `dev` anywhere in the version string. A version carrying a local segment such as `1.2.3+abc` was misread as a pre-release, silently skipping both the follow-up dev bump and the draft GitHub release. Detection is now version-scheme aware: PEP 440 for `project-type: uv`, semver for `project-type: yarn`. ([#27](https://github.com/climate-resource/github-actions/pull/27))

### Trivial/Internal Changes

- [#26](https://github.com/climate-resource/github-actions/pull/26)


## github-actions v1.4.3 (2026-06-30)

No significant changes.


## github-actions v1.4.1 (2026-06-30)

No significant changes.


## github-actions v1.4.0 (2026-06-19)

No significant changes.


## github-actions v1.3.1 (2026-05-21)

### Features

- The release workflow now pins `bump.yaml`'s first-party action refs (`setup-uv`, `bump-version`, `draft-release`) to the exact released version before tagging.
  Consumers who pin `bump.yaml@vX.Y.Z` now get a reproducible set of nested actions instead of refs floating at `@v1`. ([#16](https://github.com/climate-resource/github-actions/pull/16))

### Trivial/Internal Changes

- [#17](https://github.com/climate-resource/github-actions/pull/17), [#18](https://github.com/climate-resource/github-actions/pull/18)


## github-actions v1.3.0 (2026-05-20)

### Features

- Added a `pre-commit-command` input to the `bump-version` action and the reusable bump workflow.
  The command runs before each bump commit, so projects can regenerate version-derived files (e.g. an OpenAPI schema) and keep them in sync in the tagged commit. ([#15](https://github.com/climate-resource/github-actions/pull/15))


## github-actions v1.2.0 (2026-05-20)

### Breaking Changes

- Removed the `actions-ref` input from the reusable bump workflow.
  The shared composite actions are now pinned to the `v1` tag, matching the workflow's own major version. ([#12](https://github.com/climate-resource/github-actions/pull/12))

### Improvements

- The reusable bump workflow now references its composite actions directly instead of checking out `climate-resource/github-actions` with `github.token`.
  Private consumer repositories no longer need a PAT to fetch the shared actions. ([#12](https://github.com/climate-resource/github-actions/pull/12))


## github-actions v1.1.1 (2026-05-20)

### Trivial/Internal Changes

- [#11](https://github.com/climate-resource/github-actions/pull/11)
