# Changelog

This directory contains "news fragments", i.e. short files with a small
markdown-formatted bit of text that will be added to `CHANGELOG.md` when it is
next compiled by [towncrier](https://towncrier.readthedocs.io/) at release time.

The `CHANGELOG.md` is read by consumers of these actions, so entries should
describe the user-facing change, not internal developer details. The pull
request and git history cover the developer-centric story.

Use the past tense and punctuation, e.g.:

```
Added a `release-changelog-path` input to the reusable bump workflow.
```

Each file is named `<PR>.<TYPE>.md`, where `<PR>` is the pull request number
and `<TYPE>` is one of:

* `breaking`: a change that may break existing uses, such as removing an action
  input or changing default behaviour.
* `deprecation`: marking an action, input, or workflow for future removal.
* `feature`: new user-facing capability, like a new action or workflow input.
* `improvement`: improvement of existing functionality, usually without
  requiring consumer intervention.
* `fix`: fixes a bug.
* `docs`: documentation improvement.
* `trivial`: a small typo or internal change that might be noteworthy.

For example: `10.feature.md`, `12.fix.md`. A single PR may add multiple
fragments; disambiguate with a counter, e.g. `10.feature.1.md`,
`10.feature.2.md`.

Since the filename needs the PR number, open the PR first, then add the
fragment in a follow-up commit.

Preview the changelog that will be appended to `CHANGELOG.md` on the next
release with:

```
uv run towncrier build --draft --version <next-version>
```

The `--version` is required because this repo ships GitHub Actions, not an
importable Python package, so towncrier cannot detect the version itself. At
release time the `bump-version` action supplies it automatically.
