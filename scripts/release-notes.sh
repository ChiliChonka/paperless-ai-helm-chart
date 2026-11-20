#!/usr/bin/env bash
# Prints the GitHub release text for a chart version: versions, the CHANGELOG.md section, install
# commands, backup note and the compare link to the previous release.
# Usage: scripts/release-notes.sh <version> [<previous tag>]
# Fails when CHANGELOG.md has no section for <version> or <version> is not the one in Chart.yaml.
set -euo pipefail
cd "$(dirname "$0")/.."

version=${1:?usage: release-notes.sh <version> [<previous tag>]}
previous=${2:-}
repo=https://github.com/ChiliChonka/paperless-ai-helm-chart
chart=oci://ghcr.io/chilichonka/charts/paperless-ai

# Section "## <version>" up to the next "## " heading, without leading/trailing blank lines.
changes=$(awk -v v="## ${version}" '
  $0 == v {found = 1; next}
  found && /^## / {exit}
  found {print}
' CHANGELOG.md | sed -e '/./,$!d' | sed -e ':a' -e '/^\n*$/{$d;N;ba' -e '}')
if [ -z "$changes" ]; then
  echo "CHANGELOG.md has no section '## ${version}'" >&2
  exit 1
fi

# The app version comes from Chart.yaml: only valid for the version that file describes.
chart_version=$(sed -n 's/^version: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' paperless-ai/Chart.yaml)
if [ "$version" != "$chart_version" ]; then
  echo "version ${version} does not match paperless-ai/Chart.yaml (${chart_version}) – run it on the tagged commit" >&2
  exit 1
fi
app_version=$(sed -n 's/^appVersion: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' paperless-ai/Chart.yaml)

cat <<EOF
## Versions

helm chart version **${version}**
paperless-ai app version: **${app_version}**

## Changes

${changes}

## Install

Use the following command to see the values.

    helm show values ${chart} --version ${version} > paperless-ai-values.yaml

Update the values file and install with

    helm upgrade --install paperless-ai ${chart} --version ${version} -f paperless-ai-values.yaml

Handle with care.

Please always back up your [paperless-ngx](https://github.com/paperless-ngx/paperless-ngx) and your [paperless-ai](https://github.com/clusterzx/paperless-ai) data before deploying or upgrading.
EOF

if [ -n "$previous" ]; then
  cat <<EOF

## Full Changelog

${repo}/compare/${previous}...chart-${version}
EOF
fi
