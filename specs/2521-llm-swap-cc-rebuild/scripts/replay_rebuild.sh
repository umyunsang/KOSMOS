#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Phase 1 STUB — full implementation populated during /speckit-implement (T0xx).
#
# Spec FR-013: replay the rebuild procedure on a clean main branch.
# Step A: byte-copy CC sources for Procedure-A files (SHA-256 verified).
# Step B/C: cherry-pick swap commits in their original order.
#
# Output: working tree byte-equal to the rebuild branch.

set -euo pipefail

SPEC_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "Phase 1 stub. Run /speckit-implement to populate replay script."
echo "Reads: $SPEC_DIR/parity-matrix.md (file-level rows + swap commit log)"
echo "TODO (T030 in tasks.md):"
echo "  - byte-copy CC source per Procedure-A file"
echo "  - sha256-verify byte-copy commits"
echo "  - cherry-pick swap commits by category"
exit 1
