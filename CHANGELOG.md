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
