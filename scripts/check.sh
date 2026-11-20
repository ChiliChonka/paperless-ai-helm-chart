#!/usr/bin/env bash
# Checks the chart without a cluster: lint, render with defaults and with the made-up CI values,
# render tests. Identical locally and in CI.
set -euo pipefail
cd "$(dirname "$0")/.."

chart=paperless-ai
helm lint "$chart" --strict --quiet
helm template "$chart" "$chart" >/dev/null
helm lint "$chart" --strict --quiet -f "$chart/ci/test-values.yaml"
helm template "$chart" "$chart" -f "$chart/ci/test-values.yaml" >/dev/null
python3 tests/test-chart.py
# Every chart version needs its CHANGELOG.md section (the release text is built from it).
version=$(sed -n 's/^version: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' "$chart/Chart.yaml")
./scripts/release-notes.sh "$version" >/dev/null
echo "OK: $chart"
