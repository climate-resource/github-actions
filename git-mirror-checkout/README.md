# Check out from a git mirror

Checks out the commit under test, borrowing objects from a bare mirror of the repository on the runner.
The fetch sends only commits newer than the mirror, so a large repository checks out in seconds.
Without a usable mirror it runs `actions/checkout` instead.

```yaml
steps:
  - uses: climate-resource/github-actions/git-mirror-checkout@v1
    with:
      mirror: /path/to/mirrors/${{ github.repository }}.git
```

| Input         | Default               | Description                                                            |
| ------------- | --------------------- | ---------------------------------------------------------------------- |
| `mirror`      | empty                 | Path to a bare mirror of this repository. Empty uses the fallback.     |
| `fetch-depth` | `1`                   | History for the `actions/checkout` fallback.                           |
| `token`       | `${{ github.token }}` | Token used to fetch, and kept in the local git config for later steps. |

The `source` output is `mirror` or `checkout`.

## Limits

- A mirror checkout has full history, whatever `fetch-depth` says.
- The workspace keeps reading objects from the mirror through `objects/info/alternates`,
  so the mirror must stay mounted for the rest of the job.
- It checks out `GITHUB_SHA` only, with no submodules, LFS or `path` input.
- The mirror must be readable by the runner user, and something else keeps it fresh.
