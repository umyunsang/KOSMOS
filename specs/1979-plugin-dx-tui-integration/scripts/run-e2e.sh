#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Spec 1979 T035 — Master orchestrator for the 4-layer PTY ladder.
#
# Runs L1 unit + L2 stdio JSONL probe + L3 expect/script (happy + 3 negatives)
# in sequence. L4 vhs is manual-only because vhs requires a graphical terminal
# and is intended for human visual review (memory feedback_vhs_tui_smoke).
#
# Reports SC-1..SC-4 evidence map at the end.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEC_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(cd "$SPEC_DIR/../.." && pwd)"
cd "$REPO_ROOT"

echo "════════════════════════════════════════════════════════"
echo "Spec 1979 — 4-layer PTY ladder orchestrator"
echo "════════════════════════════════════════════════════════"

# L1 — pytest + bun test
echo ""
echo "[L1] Running pytest unit + integration tests..."
uv run pytest tests/ipc/test_plugin_op_dispatch.py tests/ipc/test_consent_bridge.py src/kosmos/plugins/tests/ -q --no-header --benchmark-disable
echo "[L1] pytest passed."

echo "[L1] Running bun test..."
(cd "$REPO_ROOT/tui" && bun test --timeout=15000 2>&1 | tail -3)
echo "[L1] bun test parity verified."

# L2 — stdio JSONL probe
echo ""
echo "[L2] Running stdio JSONL probe..."
bash "$SCRIPT_DIR/smoke-stdio.sh"
echo "[L2] JSONL output at: $SPEC_DIR/smoke-stdio.jsonl"

# L3 — expect/script PTY (happy path + 3 negatives)
echo ""
echo "[L3] Running PTY expect scenarios..."
if ! command -v expect &>/dev/null; then
  echo "[L3] WARN: expect(1) not installed; skipping PTY scenarios."
  echo "       Install via: brew install expect"
else
  for tape in smoke-1979.expect smoke-1979-deny.expect smoke-1979-bad-name.expect smoke-1979-revoke.expect; do
    echo "[L3] $tape..."
    if expect "$SCRIPT_DIR/$tape" 2>&1 | tail -5; then
      echo "[L3] $tape: PASS"
    else
      echo "[L3] $tape: FAIL (continuing)"
    fi
  done
fi

# Evidence map
echo ""
echo "════════════════════════════════════════════════════════"
echo "SC-1..SC-4 evidence map"
echo "════════════════════════════════════════════════════════"
echo "SC-001 (≤30s install)         : $SPEC_DIR/smoke-stdio.jsonl + smoke-1979.txt"
echo "SC-002 (≤3s tool propagation) : $SPEC_DIR/smoke-stdio.jsonl"
echo "SC-003 (gauntlet routing)     : $SPEC_DIR/smoke-1979.txt (Layer ⓵/⓶/⓷ markers)"
echo "SC-004 (4-layer artifacts)    : L1 + L2 + L3 + L4 (gif manual)"
echo "SC-008 (revocation)           : $SPEC_DIR/smoke-1979-revoke.txt"
echo "SC-010 (deny → no state)      : $SPEC_DIR/smoke-1979-deny.txt"
echo ""
echo "L4 visual gif: bun run vhs $SCRIPT_DIR/smoke-1979.tape"
echo "Done."
