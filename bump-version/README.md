# bump-version

Composite action that bumps a project's version, updates the CHANGELOG via
towncrier, commits, tags, pushes, and (by default) lands a follow-up commit that
moves the branch onto a pre-release version so future commits don't share the
tagged version.

Two project types are supported, selected with `project-type`:

| `project-type` | Version lives in | Bumped with |
| --- | --- | --- |
| `uv` (default) | `pyproject.toml` | `uv version --bump` |
| `yarn` | `package.json` | `npm version` |

For `yarn`, `npm version` is used purely as a version-bumping CLI — yarn remains
the package manager and owns the lockfile.

The logic lives in [`bump.py`](bump.py), which `action.yml` invokes with
`uv run --script`. Its unit tests are in [`../tests/test_bump.py`](../tests/test_bump.py).

## Prerequisites

- **`uv` is on PATH for both project types** (use [`setup-uv`](../setup-uv)
  before this action). It runs the script itself, so it is required even for
  `project-type: yarn`, where it also provides towncrier via `uvx`.
- For `project-type: yarn`, `node`, `npm` and `yarn` must be on PATH (use
  `actions/setup-node` and `corepack enable`).
- The checked-out repo has full history (`fetch-depth: 0`).
  The default `GITHUB_TOKEN` is sufficient to push the bump commit and tag.
  Check out with a PAT only when branch protection blocks the `github-actions` bot,
  or when downstream workflows must fire from the tag push (a push made with `GITHUB_TOKEN` does not trigger other workflows).

## Inputs

| Input | Default | Description |
| --- | --- | --- |
| `project-type` | `uv` | `uv` for a Python project, `yarn` for a Node project. |
| `bump-rule` | _required_ | Whitespace-separated arguments describing the bump. For `uv`, each segment becomes a separate `--bump`: `patch`, `minor`, `major`, `stable`, `minor alpha`, `patch rc`. From a stable version, prerelease segments (`alpha`, `beta`, `rc`, `dev`) must be combined with a release segment. For `yarn`, passed verbatim to `npm version`: `patch`, `preminor --preid alpha`, `prerelease --preid rc`. |
| `pre-release-bump` | `dev` | Pre-release segment for the second commit. For `uv`: `dev`, `alpha`, `beta`, `rc`. For `yarn`: verbatim `npm version` arguments, e.g. `--preid dev`. Use `none` to skip the second commit. |
| `pre-release-base` | `patch` | Base bump applied before the pre-release segment in the second commit. For `uv`: a bump rule (`patch`, `minor`, `major`, …). For `yarn`: an `npm version` strategy word, e.g. `prepatch`. Use `none` to add the pre-release marker without bumping the base. |
| `update-changelog` | `true` | Build the CHANGELOG with towncrier for the new version. |
| `commit-email` | `ci-runner@climate-resource.invalid` | Author email for both commits. |
| `workspace-packages` | _empty_ | Newline-separated workspace packages to mirror the version onto. For `uv`: package names. For `yarn`: directory paths relative to the repo root, e.g. `apps/analysis-portal`. |
| `lock` | `true` | Refresh the lockfile after each version change (`uv lock`, or `yarn install --mode=update-lockfile`). |
| `pre-commit-command` | _empty_ | Shell command run after the changelog build and before each bump commit. Use it to regenerate version-derived files (e.g. an OpenAPI schema) so they stay in sync in the tagged commit. The command must succeed; a non-zero exit aborts the bump. |
| `pre-commit-skip` | `false` | Pass `-n` to `git commit` to bypass pre-commit hooks. |
| `push` | `true` | Push the bump commit, tag, and pre-release commit. |

## Outputs

| Output | Description |
| --- | --- |
| `base-version` | Version before the bump. |
| `new-version` | Tagged version (no `v` prefix). |
| `tag` | New git tag, with `v` prefix. |
| `dev-version` | Pre-release version landed on the branch after tagging (when applicable). |
| `is-prerelease` | `'true'` when the tagged version is a pre-release. Use to gate downstream release steps. |

`base-version`, `new-version`, `tag` and `is-prerelease` are written as soon as
the release is tagged, so they remain available to later steps even if the
pre-release commit fails.

## Behaviour

**Phase 1 — tag the release**

1. Read the current version (`base-version`).
2. Apply `bump-rule` to the root project to obtain `new-version`.
3. Mirror `new-version` onto each `workspace-packages` entry.
4. Refresh the lockfile, if `lock: true`.
5. Build the CHANGELOG with towncrier, if `update-changelog: true`.
6. Run `pre-commit-command`, if set.
7. `git commit -a -m "bump: version <base-version> -> <new-version>"`.
8. `git tag v<new-version>`, then push the commit and tag if `push: true`.

**Phase 2 — land the pre-release**

Skipped entirely when `pre-release-bump: none`, or when the tagged version is
already a pre-release. Otherwise it applies `pre-release-base` then
`pre-release-bump`, repeats the mirror / lock / `pre-commit-command` steps, and
creates a `bump(<label>): ...` commit which is pushed.

The `<label>` scope is the pre-release identifier, not the raw input. For `uv`
that is the `pre-release-bump` word itself (`bump(dev)`); for `yarn` it is read
back off the version `npm version` produced, so `--preid dev` landing on
`1.2.5-dev.0` gives `bump(dev)` rather than `bump(--preid dev)`.

Pre-release detection is version-scheme aware: PEP 440 for `uv` (via
`packaging`), semver for `yarn`.

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

A Node project needs Node on PATH as well as uv:

```yaml
- uses: climate-resource/github-actions/setup-uv@v1
- uses: actions/setup-node@v7.0.0
  with:
    node-version: "22"
- run: corepack enable
  shell: bash
- uses: climate-resource/github-actions/bump-version@v1
  with:
    project-type: yarn
    bump-rule: patch
    pre-release-base: prepatch
    pre-release-bump: --preid dev
    workspace-packages: |
      apps/analysis-portal
```

## Developing

The script is a self-contained [PEP 723](https://peps.python.org/pep-0723/)
script, so it can be run directly against a scratch repository:

```bash
cd /path/to/a/throwaway/clone
PROJECT_TYPE=uv BUMP_RULE=patch UPDATE_CHANGELOG=false DO_PUSH=false \
  uv run --script /path/to/github-actions/bump-version/bump.py
```

Unit tests cover argument assembly, pre-release detection and input parsing:

```bash
uv run --group dev pytest
```
