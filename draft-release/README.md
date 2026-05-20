# draft-release

Composite action that creates a draft GitHub release for a Python project.
Reads the project version from the triggering tag (or an explicit input),
generates release notes from the CHANGELOG and `git log`, and uploads any artifacts provided.

## Inputs

| Input              | Default                       | Description                                                                                     |
| ------------------ | ----------------------------- | ----------------------------------------------------------------------------------------------- |
| `token`            | _required_                    | Token used to create the release. PAT recommended so the release can fire downstream workflows. |
| `tag`              | `$GITHUB_REF_NAME`            | Tag to release. Defaults to the tag that triggered the workflow.                                |
| `files`            | _empty_                       | Newline-separated globs of artifact files to attach.                                            |
| `changelog-script` | _empty_                       | Optional Python script invoked via `uv run` whose stdout is used as the changelog section.      |
| `changelog-path`   | `CHANGELOG.md`                | CHANGELOG to extract the latest section from when no script is set.                             |
| `release-template` | `.github/release_template.md` | Where to write the assembled release notes.                                                     |
| `draft`            | `true`                        | Create the release as a draft.                                                                  |
| `prerelease`       | `false`                       | Mark the release as a pre-release.                                                              |

## Outputs

| Output    | Description              |
| --------- | ------------------------ |
| `version` | Version (no `v` prefix). |
| `tag`     | Git tag released.        |

## Behaviour

1. Resolves the target tag and exports `PROJECT_VERSION`/`PROJECT_TAG` for the
   rest of the job.
2. Writes release notes to `release-template` with sections **Changelog** (from
   `changelog-script` if provided, else the latest section of the CHANGELOG) and **Commits** (from `git log <previous-tag>..<tag>`).
3. Calls `softprops/action-gh-release@v2` to create the release.

## Example (tag-triggered release)

```yaml
on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
      - uses: climate-resource/github-actions/setup-uv@v1
      - run: uv build
      - uses: climate-resource/github-actions/draft-release@v1
        with:
          token: ${{ secrets.PERSONAL_ACCESS_TOKEN }}
          files: dist/*
```
