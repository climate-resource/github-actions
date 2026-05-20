# GitHub Actions

Reusable GitHub Actions and workflows for Climate Resource repositories.

## Actions

| Action                           | Description                                                          |
| -------------------------------- | -------------------------------------------------------------------- |
| [setup-uv](./setup-uv)           | Set up uv with optional CodeArtifact access                          |
| [bump-version](./bump-version)   | Bump version with `uv version`, towncrier changelog, tag, dev-commit |
| [draft-release](./draft-release) | Create a draft GitHub release with notes and artifacts               |

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
        options:
          - patch
          - minor
          - major
          - stable
          - "minor alpha"
          - "minor beta"
          - "minor rc"
        required: true

jobs:
  bump:
    uses: climate-resource/github-actions/.github/workflows/bump.yaml@v1
    with:
      bump-rule: ${{ inputs.bump_rule }}
      python-version: "3.13"
      create-release: true
      build-command: "uv build"
      release-files: |
        dist/*
```

### When do I need a PAT?

The reusable workflow uses the built-in `GITHUB_TOKEN` by default,
so no secret needs to be wired up.
Pass `secrets: token: ${{ secrets.PERSONAL_ACCESS_TOKEN }}` only when:

- `main` has branch protection that blocks pushes from `github-actions[bot]`.
- The release is auto-published (not drafted)
  and downstream workflows listening on `release: published` must fire.
  Releases created with `GITHUB_TOKEN` do not trigger other workflows.
  A manually published draft fires downstream workflows
  under the publishing user's identity,
  so the default draft flow works without a PAT.
- A separate workflow listens for the bump tag-push
  and must fire from this run.

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
3. Keep `scripts/changelog-to-release-template.py` if you need
   project-specific changelog formatting and pass it via
   `release-changelog-script`.
