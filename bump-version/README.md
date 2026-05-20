# bump-version

Composite action that bumps a Python project's version with `uv version --bump`,
updates the CHANGELOG via towncrier, commits, tags, pushes, and (by default)
lands a follow-up commit that moves `main` onto a pre-release version so future commits don't share the tagged version.

## Prerequisites

The action assumes:

- `uv` is on PATH (use [`setup-uv`](../setup-uv) before this action).
- The checked-out repo has full history (`fetch-depth: 0`).
  The default  `GITHUB_TOKEN` is sufficient to push the bump commit and tag.
  Check out with a PAT only when branch protection blocks the `github-actions` bot,
  or when downstream workflows must fire from the tag push (a push made with `GITHUB_TOKEN` does not trigger other workflows).
- The project's `pyproject.toml` is managed by `uv` (i.e. `uv version --short` returns the current version).
- `towncrier` is available via `uv run` when `update-changelog: true` (the default).

## Inputs

| Input | Default | Description |
| --- | --- | --- |
| `bump-rule` | _required_ | Whitespace-separated list of segments passed to `uv version --bump`. Each segment becomes a separate `--bump`. Examples: `patch`, `minor`, `major`, `stable`, `minor alpha`, `patch rc`. From a stable version, prerelease segments (`alpha`, `beta`, `rc`, `dev`) must be combined with a release segment. |
| `pre-release-bump` | `dev` | Pre-release segment for the second commit (`dev`, `alpha`, `beta`, `rc`). Use `none` to skip the second commit. |
| `pre-release-base` | `patch` | Base bump applied before the pre-release segment in the second commit. Use `none` to add the pre-release marker without bumping the base. |
| `update-changelog` | `true` | Run `uv run towncrier build` for the new version. |
| `commit-email` | `ci-runner@climate-resource.invalid` | Author email for both commits. |
| `workspace-packages` | _empty_ | Newline-separated workspace package names to mirror the version onto. |
| `lock` | `true` | Run `uv lock` after each version change. |
| `pre-commit-command` | _empty_ | Shell command run after the changelog build and before each bump commit. Use it to regenerate version-derived files (e.g. an OpenAPI schema) so they stay in sync in the tagged commit. The command must succeed; a non-zero exit aborts the bump. |
| `pre-commit-skip` | `false` | Pass `-n` to `git commit` to bypass pre-commit hooks. |
| `push` | `true` | Push the bump commit, tag, and pre-release commit. |

## Outputs

| Output | Description |
| --- | --- |
| `base-version` | Version before the bump. |
| `new-version` | Tagged version (no `v` prefix). |
| `tag` | New git tag, with `v` prefix. |
| `dev-version` | Pre-release version landed on `main` after tagging (when applicable). |
| `is-prerelease` | `'true'` when the tagged version matches `(a\|b\|rc\|dev)`. Use to gate downstream release steps. |

## Behaviour

1. Reads the current version (`BASE_VERSION = uv version --short`).
2. `uv version --frozen --bump <bump-rule>` to obtain `NEW_VERSION`.
3. Mirrors `NEW_VERSION` to each `workspace-packages` entry.
4. If `update-changelog: true`, runs
   `uv run towncrier build --yes --version v$NEW_VERSION`.
5. Optionally `uv lock`.
6. If `pre-commit-command` is set, runs it (so version-derived files are
   regenerated before the commit).
7. `git commit -a -m "bump: version $BASE_VERSION -> $NEW_VERSION"`.
8. `git tag v$NEW_VERSION`.
9. Pushes the commit and tag.
10. If `pre-release-bump != none` and the tagged version is not already a
    pre-release, applies `pre-release-base` (default `patch`) then
    `pre-release-bump` (default `dev`), mirrors workspace packages, locks, runs
    `pre-commit-command` again, and creates a `bump(<pre-release-bump>): ...`
    commit which is pushed.

## Example

```yaml
- uses: climate-resource/github-actions/setup-uv@v1
- uses: climate-resource/github-actions/bump-version@v1
  with:
    bump-rule: ${{ inputs.bump_rule }}
    workspace-packages: |
      bookshelf
      bookshelf-producer
```
