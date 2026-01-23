# GitHub Actions

Reusable GitHub Actions and workflows for Climate Resource repositories.

## Actions

| Action | Description |
|--------|-------------|
| [setup-uv](./setup-uv) | Set up uv with optional CodeArtifact access |

## Usage

Reference actions using the full path:

```yaml
- uses: climate-resource/github-actions/setup-uv@v1
```

## Versioning

This repository uses semantic versioning. Use a major version tag (e.g., `@v1`) for stability:

- `@v1` - Latest v1.x.x (recommended)
- `@v1.2.3` - Specific version
- `@main` - Latest (may include breaking changes)
