# GitHub Actions

Reusable GitHub Actions and workflows for Climate Resource repositories.

## Actions

| Action                           | Description                                                          |
| -------------------------------- | -------------------------------------------------------------------- |
| [setup-uv](./setup-uv)           | Set up uv with optional CodeArtifact access                          |
| [bump-version](./bump-version)   | Bump version with `uv version`, towncrier changelog, tag, dev-commit |
| [draft-release](./draft-release) | Create a draft GitHub release with notes and artifacts               |

[notify-flux](./notify-flux) notifies Flux after an image is published. It is deprecated, because Flux polls for OCI deployment bundles.

## Reusable workflows

| Workflow                                                       | Trigger         | Description                                                              |
| -------------------------------------------------------------- | --------------- | ------------------------------------------------------------------------ |
| [`.github/workflows/bump.yaml`](./.github/workflows/bump.yaml) | `workflow_call` | Bump version, update changelog, tag, push, and draft the GitHub release. |

The reusable workflow runs the bump and the draft release in a single
`workflow_dispatch` so consumers only ever wire one workflow. The composite
actions remain available for repos that need to build their own flow.

## Usage

Reference actions and workflows using the full path:

```yaml
- uses: climate-resource/github-actions/setup-uv@v1
- uses: climate-resource/github-actions/bump-version@v1
- uses: climate-resource/github-actions/draft-release@v1
```

```yaml
jobs:
  bump:
    uses: climate-resource/github-actions/.github/workflows/bump.yaml@v1
```

## Consumer recipe

`.github/workflows/bump.yaml` in the consumer repo:

```yaml
name: Bump version

on:
  workflow_dispatch:
    inputs:
      bump_rule:
        type: choice
        description: How to bump the project's version
        required: true
        options:
          - stable
          - patch
          - minor
          - major
          - "patch alpha"
          - "patch beta"
          - "patch rc"
          - "minor alpha"
          - "minor beta"
          - "minor rc"
          - "major alpha"
          - "major beta"
          - "major rc"
      pre_release_bump:
        type: choice
        description: Pre-release segment for the post-tag commit on main
        required: false
        default: dev
        options:
          - dev
          - alpha
          - beta
          - rc
          - none
      pre_release_base:
        type: choice
        description: Base bump applied before the pre-release segment on main
        required: false
        default: patch
        options:
          - patch
          - minor
          - major
          - none
      update_changelog:
        type: boolean
        description: Run towncrier to update the CHANGELOG before tagging
        required: false
        default: true

jobs:
  bump:
    uses: climate-resource/github-actions/.github/workflows/bump.yaml@v1
    with:
      bump-rule: ${{ inputs.bump_rule }}
      pre-release-bump: ${{ inputs.pre_release_bump }}
      pre-release-base: ${{ inputs.pre_release_base }}
      update-changelog: ${{ inputs.update_changelog }}
      python-version: "3.13"
      create-release: true
      build-command: "uv build"
      release-files: |
        dist/*
```

### When do I need a PAT?

The reusable workflow uses the built-in `GITHUB_TOKEN` by default, so no secret needs to be wired up.
Pass `secrets: token: ${{ secrets.PERSONAL_ACCESS_TOKEN }}` only when:

- `main` has branch protection that blocks pushes from `github-actions[bot]`.
- The release is auto-published (not drafted) and downstream workflows listening on `release: published` must fire.
  Releases created with `GITHUB_TOKEN` do not trigger other workflows.
  A manually published draft fires downstream workflows under the publishing user's identity, so the default draft flow works without a PAT.
- A separate workflow listens for the bump tag-push and must fire from this run.
- A `pre-commit-command` regenerates a file under `.github/workflows/`.
  `GITHUB_TOKEN` may not push workflow-file changes, so the PAT must additionally
  carry the `workflow` scope (classic PAT) or the repository "Workflows" write
  permission (fine-grained PAT).

### uv workspace projects (multiple packages)

```yaml
jobs:
  bump:
    uses: climate-resource/github-actions/.github/workflows/bump.yaml@v1
    with:
      bump-rule: ${{ inputs.bump_rule }}
      workspace-packages: |
        bookshelf
        bookshelf-producer
      create-release: true
      build-command: |
        uv build --package bookshelf -o dist
        uv build --package bookshelf-producer -o dist
      release-files: |
        dist/*
```

### Dynamically versioned projects (hatch-vcs)

Projects whose version is derived from git tags hold no version to edit, so the tag is the release:

```yaml
jobs:
  bump:
    uses: climate-resource/github-actions/.github/workflows/bump.yaml@v1
    with:
      dynamic-versioning: true
      bump-rule: ${{ inputs.bump_rule }}
      create-release: true
      build-command: "uv build"
      release-files: |
        dist/*
```

The base version is the latest reachable `v*` tag,
and `bump-rule` is applied to it exactly as it would be to a version read from `pyproject.toml`.
Nothing is written to `pyproject.toml`, no lockfile is refreshed, and no post-tag commit is landed,
so `pre-release-bump`, `pre-release-base` and `workspace-packages` are ignored.
The changelog build and `pre-commit-command` still run, and their changes land in the tagged commit.



### Skipping the changelog or the pre-release dev commit

```yaml
with:
  bump-rule: ${{ inputs.bump_rule }}
  update-changelog: false
  pre-release-bump: none
```

## Versioning

This repository uses semantic versioning. Use a major version tag (e.g., `@v1`) for stability:

- `@v1` - Latest v1.x.x (recommended)
- `@v1.2.3` - Specific version
- `@main` - Latest (may include breaking changes)

The `bump.yaml` workflow pins its own first-party actions (`setup-uv`, `bump-version`, `draft-release`),
to the released version at tag time,
so a `@v1.2.3` pin of the workflow resolves to a fixed set of nested actions rather than letting them float independently.

## Development

Lint workflow changes locally with:

```bash
actionlint
```

## Migrating existing projects

This action only supports `uv version --bump`. Projects on `poetry version`
or `pdm bump` must first migrate to `uv` (recommended) or to
[`bump-my-version`](https://github.com/callowayproject/bump-my-version) (for
versioning schemes uv cannot express, e.g. calendar versioning or custom
serializers) before adopting this action.

Once the project is on `uv`:

1. Replace the body of `.github/workflows/bump.yaml` with a `uses:` call to
   `climate-resource/github-actions/.github/workflows/bump.yaml@v1`, keeping
   the local `workflow_dispatch` definition.
2. Delete `.github/workflows/release.yaml` — the reusable bump workflow drafts
   the release in the same run via `create-release: true`.
3. If the changelog lives somewhere other than `CHANGELOG.md` (e.g. towncrier writes to `docs/changelog.md`),
   set `release-changelog-path` — the action extracts the latest `<!-- towncrier release notes start -->` section itself.
   A `release-changelog-script` is only needed for project-specific changelog formatting beyond that extraction.
