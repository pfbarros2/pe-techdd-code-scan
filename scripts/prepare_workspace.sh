#!/usr/bin/env bash
# Copy ONLY the fictional fixture into an isolated git repo for scanning,
# so the scanner's agent cannot see ground_truth/ or results/.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${SCAN_WORKDIR:-/tmp/pe-techdd-scan-work}/quillmoor-ledger"
rm -rf "$WORK"
mkdir -p "$(dirname "$WORK")"
cp -r "$REPO_ROOT/fixture/quillmoor-ledger" "$WORK"
cd "$WORK"
git init -q -b main
git -c user.name=fixture -c user.email=fixture@example.invalid add -A
git -c user.name=fixture -c user.email=fixture@example.invalid commit -q -m "fixture snapshot"
echo "$WORK"
