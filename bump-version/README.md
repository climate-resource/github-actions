# bump-version

Composite action that bumps a project's version, updates the CHANGELOG via
towncrier, commits, tags, pushes, and (by default) lands a follow-up commit that
moves the branch onto a pre-release version so future commits don't share the
tagged version.

`project-type` selects the backend, and is named after the package manager that
owns the lockfile:

| `project-type` | Version lives in | Bumped with | `lock: true` runs |
| --- | --- | --- | --- |
| `uv` (default) | `pyproject.toml` | `uv version --bump` | `uv lock` |
| `yarn` | `package.json` | `npm version` | `yarn install --mode=update-lockfile` |
| `npm` | `package.json` | `npm version` | `npm install --package-lock-only` |
| `pnpm` | `package.json` | `npm version` | `pnpm install --lockfile-only` |

The three Node types behave identically apart from that last column. `npm
version` is used purely as a version-bumping CLI — it ships with Node, and the
package manager you named stays in charge of the lockfile.

Projects that derive their version from git tags (e.g. hatch-vcs) set `dynamic-versioning: true` instead.
The tag is then the only thing that carries the version, so no manifest is touched.
See [Dynamic versioning](#dynamic-versioning) below.

The logic lives in [`bump.py`](bump.py), which `action.yml` invokes with
`uv run --script`. Its unit tests are in [`../tests/test_bump.py`](../tests/test_bump.py).

## Prerequisites

- **`uv` is on PATH for all project types** (use [`setup-uv`](../setup-uv)
  before this action). It runs the script itself, so it is required even for
  the Node project types, where it also provides towncrier via `uvx`.
- For the Node project types, `node` and `npm` must be on PATH, plus `yarn` or
  `pnpm` if `lock: true` (use `actions/setup-node`, and `corepack enable` for
  yarn/pnpm).
- The checked-out repo has full history (`fetch-depth: 0`).
  The default `GITHUB_TOKEN` is sufficient to push the bump commit and tag.
  Check out with a PAT only when branch protection blocks the `github-actions` bot,
  or when downstream workflows must fire from the tag push (a push made with `GITHUB_TOKEN` does not trigger other workflows).

## Inputs

| Input | Default | Description |
| --- | --- | --- |
| `project-type` | `uv` | `uv` for a Python project; `yarn`, `npm` or `pnpm` for a Node project. See the table above. |
| `dynamic-versioning` | `false` | Take the base version from the latest reachable `v*` tag rather than from a manifest. `uv` projects only. See [Dynamic versioning](#dynamic-versioning). |
| `bump-rule` | _required_ | Whitespace-separated arguments describing the bump. For `uv`, each segment becomes a separate `--bump`: `patch`, `minor`, `major`, `stable`, `minor alpha`, `patch rc`. From a stable version, prerelease segments (`alpha`, `beta`, `rc`, `dev`) must be combined with a release segment. For the Node types, passed verbatim to `npm version`: `patch`, `preminor --preid alpha`, `prerelease --preid rc`. |
| `pre-release-bump` | `dev` | Pre-release segment for the second commit. For `uv`: `dev`, `alpha`, `beta`, `rc`. For the Node types: verbatim `npm version` arguments, e.g. `--preid dev`. Use `none` to skip the second commit. |
| `pre-release-base` | `patch` | Base bump applied before the pre-release segment in the second commit. For `uv`: a bump rule (`patch`, `minor`, `major`, …). For the Node types: an `npm version` strategy word, e.g. `prepatch`. Use `none` to add the pre-release marker without bumping the base. |
| `update-changelog` | `true` | Build the CHANGELOG with towncrier for the new version. |
| `commit-email` | `ci-runner@climate-resource.invalid` | Author email for both commits. |
| `workspace-packages` | _empty_ | Newline-separated workspace packages to mirror the version onto. For `uv`: package names. For the Node types: directory paths relative to the repo root, e.g. `apps/analysis-portal`. |
| `lock` | `true` | Refresh the lockfile after each version change, using the command for the project type (see the table above). |
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
that is the `pre-release-bump` word itself (`bump(dev)`); for Node it is read
back off the version `npm version` produced, so `--preid dev` landing on
`1.2.5-dev.0` gives `bump(dev)` rather than `bump(--preid dev)`.

Pre-release detection is version-scheme aware: PEP 440 for `uv` (via
`packaging`), semver for the Node types.

## Dynamic versioning

With `dynamic-versioning: true` the version is not stored anywhere in the repo,
so the base is the highest `v*` tag reachable from `HEAD`, with the leading `v` stripped.
A repo with no such tag starts from `0.0.0`.

Tags are ranked by PEP 440.
A tag that is not a valid version, such as `vendor-3`, is ignored rather than treated as one.

`bump-rule` means exactly what it means in static mode (`uv version --bump` is still used to calculate the tag).
So `patch`, `minor`, `major`, `stable` and the pre-release segments (`alpha`, `beta`, `rc`, `dev`)
all behave as they usually do, and an unsupported combination fails with uv's own message.

What changes:

- `pyproject.toml` or the lockfile is not edited as it isn't needed,
  so `workspace-packages` and `lock` do not apply.
- There is no post-tag commit, `pre-release-bump` and `pre-release-base` are ignored,
  and `dev-version` is empty.
- The commit is made only if something is left to commit,
  which in practice means the changelog build or `pre-commit-command` changed a tracked file.
  With nothing to commit the tag lands on `HEAD` rather than on an empty commit.

`update-changelog` and `pre-commit-command` work as they do in static mode.

```yaml
- uses: climate-resource/github-actions/setup-uv@v1
- uses: climate-resource/github-actions/bump-version@v1
  with:
    dynamic-versioning: true
    bump-rule: ${{ inputs.bump_rule }}
```

### Gotchas

The tag is the only record of the version, so anything that muddies the tags muddies the release.

- Releasing twice from one commit is refused, because hatch-vcs would read the lower tag.
  A commit carrying `v1.3.0` and `v1.4.0` builds `1.3.0` whichever tag was added last,
  so the action fails rather than tagging on top of an existing release.
  Dynamic mode makes this easy to reach, because it tags `HEAD` without landing a commit.
  Moving aliases such as `v1` or `v1.3` trip the same guard, so a repo that publishes them
  cannot use `dynamic-versioning`.
- Every package in the repo shares one version, because they all read the same tag.
  A release moves them together and no single member can be released on its own.
- Build a workspace with `uv build --all-packages`.
  Plain `uv build` against a virtual workspace root produces `unknown-0.0.0` artifacts,
  which `release-files: dist/*` will happily attach to the release.
- A member in a subdirectory needs `raw-options = { search_parent_directories = true }`
  under `[tool.hatch.version]`, or hatch-vcs fails to find the repository at all.

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
