#!/usr/bin/env bash
# Pin bump.yaml's first-party action refs to the current version.
#
# This script runs as bump-version's `pre-commit-command`: after the version bump, before `git commit -a`,
# so `bump.yaml@vX.Y.Z` ships nested actions also at vX.Y.Z.

set -euo pipefail

workflow=".github/workflows/bump.yaml"
version="$(uv version --short)"

# Rewrite via a temp file so the script is portable across GNU and BSD sed
# (`sed -i` takes an argument on BSD/macOS but not on GNU).
tmp="$(mktemp)"
sed -E \
  "s|(climate-resource/github-actions/[a-z-]+)@v[0-9][0-9A-Za-z.-]*|\1@v${version}|g" \
  "${workflow}" >"${tmp}"
mv "${tmp}" "${workflow}"

# Fail loudly if any first-party `uses:` ref did not land on the release
# version (e.g. an action was renamed and the regex no longer matches it).
if grep -nE '^[[:space:]]*uses:[[:space:]]*climate-resource/github-actions/[a-z-]+@v' "${workflow}" \
     | grep -vF "@v${version}"; then
  echo "pin-bump-refs: unpinned first-party ref remains in ${workflow}" >&2
  exit 1
fi

echo "pin-bump-refs: pinned first-party refs in ${workflow} to v${version}"
