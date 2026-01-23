# setup-uv

Set up [uv](https://docs.astral.sh/uv/) with optional AWS CodeArtifact private registry access.

## Usage

### Basic (no private registry)

```yaml
steps:
  - uses: actions/checkout@v4
  - uses: climate-resource/github-actions/setup-uv@v1
    with:
      python-version: "3.12"
  - run: uv sync
```

### With CodeArtifact (read access)

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # Required for OIDC
      contents: read

    steps:
      - uses: actions/checkout@v4
      - uses: climate-resource/github-actions/setup-uv@v1
        with:
          python-version: "3.12"
          codeartifact: read
          codeartifact-domain: ${{ secrets.CODEARTIFACT_DOMAIN }}
          codeartifact-domain-owner: ${{ secrets.CODEARTIFACT_DOMAIN_OWNER }}
          codeartifact-role-read: ${{ secrets.CODEARTIFACT_ROLE_READ }}
      - run: uv sync
```

### With CodeArtifact (publish access)

```yaml
jobs:
  publish:
    runs-on: ubuntu-latest
    environment: release  # Typically required for publish roles
    permissions:
      id-token: write
      contents: read

    steps:
      - uses: actions/checkout@v4
      - uses: climate-resource/github-actions/setup-uv@v1
        with:
          python-version: "3.12"
          codeartifact: publish
          codeartifact-domain: ${{ secrets.CODEARTIFACT_DOMAIN }}
          codeartifact-domain-owner: ${{ secrets.CODEARTIFACT_DOMAIN_OWNER }}
          codeartifact-role-publish: ${{ secrets.CODEARTIFACT_ROLE_PUBLISH }}
      - run: |
          uv build
          uv publish --index private-registry
```

## Inputs

| Input                       | Description                                        | Required | Default         |
| --------------------------- | -------------------------------------------------- | -------- | --------------- |
| `python-version`            | Python version to install                          | No       | Project default |
| `uv-version`                | Version of uv to install                           | No       | Latest          |
| `working-directory`         | Working directory for uv commands                  | No       | `.`             |
| `enable-cache`              | Enable caching of the uv cache                     | No       | `true`          |
| `cache-dependency-glob`     | Glob pattern for cache dependency files            | No       | `**/uv.lock`    |
| `cache-suffix`              | Suffix for the cache key                           | No       | -               |
| `cache-local-path`          | Path to a local cache directory                    | No       | -               |
| `codeartifact`              | Enable CodeArtifact: `read`, `publish`, or `false` | No       | `false`         |
| `codeartifact-domain`       | CodeArtifact domain name                           | No       | -               |
| `codeartifact-domain-owner` | CodeArtifact domain owner (AWS account ID)         | No       | -               |
| `codeartifact-role-read`    | IAM role ARN for read access                       | No       | -               |
| `codeartifact-role-publish` | IAM role ARN for publish access                    | No       | -               |
| `aws-region`                | AWS region for CodeArtifact                        | No       | `us-west-2`     |

## pyproject.toml Configuration

For CodeArtifact to work, your `pyproject.toml` must define the private registry:

```toml
[[tool.uv.index]]
name = "private-registry"
url = "https://{domain}-{domain-owner}.d.codeartifact.{region}.amazonaws.com/pypi/pypi/simple/"
publish-url = "https://{domain}-{domain-owner}.d.codeartifact.{region}.amazonaws.com/pypi/pypi/"
explicit=true

[tool.uv.sources]
my-private-package = { index = "private-registry" }
```

## Org Secrets

Set these as GitHub organization secrets:

| Secret                      | Description                                        |
| --------------------------- | -------------------------------------------------- |
| `CODEARTIFACT_DOMAIN`       | CodeArtifact domain name                           |
| `CODEARTIFACT_DOMAIN_OWNER` | AWS account ID that owns the domain                |
| `CODEARTIFACT_ROLE_READ`    | IAM role ARN for read access (all repos)           |
| `CODEARTIFACT_ROLE_PUBLISH` | IAM role ARN for publish access (restricted repos) |
