#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Spec 1979 T032 — L2 stdio JSONL probe.
#
# Pipes raw plugin_op_request frames into backend stdio mode + captures the
# JSONL response stream. Bypasses the TUI for backend baseline verification
# (per docs/testing.md § TUI verification methodology layer L2).
#
# Frames sent (in order):
# 1. plugin_op_request:list (before install — expect empty payload)
# 2. plugin_op_request:install seoul-subway --yes (skip consent prompt for L2)
# 3. plugin_op_request:list (after install — expect 1 entry)
#
# Output: specs/1979-plugin-dx-tui-integration/smoke-stdio.jsonl
#
# Usage:
#   bash specs/1979-plugin-dx-tui-integration/scripts/smoke-stdio.sh
#
# Pre-requisites: KOSMOS backend importable as `python -m kosmos.cli`,
# fixture catalog + bundle present under scripts/fixtures/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEC_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(cd "$SPEC_DIR/../.." && pwd)"
OUTPUT="$SPEC_DIR/smoke-stdio.jsonl"

# fixture URLs (file://)
CATALOG_URL="file://$SCRIPT_DIR/fixtures/catalog.json"

# Fail-soft env so the install path doesn't block on real SLSA verification.
export KOSMOS_PLUGIN_CATALOG_URL="$CATALOG_URL"
export KOSMOS_PLUGIN_SLSA_SKIP="true"
export KOSMOS_ENV="development"

# Use a tmp install root so we don't pollute the citizen's real memdir.
TMPROOT="$(mktemp -d /tmp/kosmos-1979-smoke.XXXXXX)"
export KOSMOS_PLUGIN_INSTALL_ROOT="$TMPROOT/plugins"
export KOSMOS_USER_MEMDIR_ROOT="$TMPROOT/memdir"
mkdir -p "$KOSMOS_PLUGIN_INSTALL_ROOT" "$KOSMOS_USER_MEMDIR_ROOT/consent"

cleanup() { rm -rf "$TMPROOT"; }
trap cleanup EXIT

cd "$REPO_ROOT"

SESSION_ID="smoke-1979-stdio"
TS="2026-04-28T00:00:00.000Z"

# Build the input frame stream
{
  # Frame 1 — list before install
  echo "{\"kind\":\"plugin_op\",\"version\":\"1.0\",\"session_id\":\"$SESSION_ID\",\"correlation_id\":\"smoke-list-1\",\"ts\":\"$TS\",\"role\":\"tui\",\"op\":\"request\",\"request_op\":\"list\"}"

  # Frame 2 — install seoul-subway (yes-flag bypasses consent prompt for L2)
  echo "{\"kind\":\"plugin_op\",\"version\":\"1.0\",\"session_id\":\"$SESSION_ID\",\"correlation_id\":\"smoke-install-1\",\"ts\":\"$TS\",\"role\":\"tui\",\"op\":\"request\",\"request_op\":\"install\",\"name\":\"seoul-subway\",\"dry_run\":false}"

  # Wait for install to settle (catalog + bundle + SLSA + manifest + register + receipt = ~3s)
  sleep 4

  # Frame 3 — list after install
  echo "{\"kind\":\"plugin_op\",\"version\":\"1.0\",\"session_id\":\"$SESSION_ID\",\"correlation_id\":\"smoke-list-2\",\"ts\":\"$TS\",\"role\":\"tui\",\"op\":\"request\",\"request_op\":\"list\"}"

  sleep 1

  # Trigger graceful shutdown so the loop exits cleanly
  echo "{\"kind\":\"session_event\",\"version\":\"1.0\",\"session_id\":\"$SESSION_ID\",\"correlation_id\":\"smoke-exit\",\"ts\":\"$TS\",\"role\":\"tui\",\"event\":\"exit\",\"payload\":{}}"

} | uv run python -m kosmos.cli --ipc stdio > "$OUTPUT" 2>/dev/null || true

echo "L2 stdio JSONL probe complete: $OUTPUT"
echo "==="
echo "plugin_op_complete frames observed:"
jq -c 'select(.kind == "plugin_op" and .op == "complete") | {correlation_id, result, exit_code, receipt_id}' "$OUTPUT" 2>/dev/null || echo "(jq unavailable; raw output in $OUTPUT)"
