#!/usr/bin/env bash
# diff-upstream.sh — FR-013 lift divergence gate
#
# Walks every .ts/.tsx file under tui/src/ink/ (and optionally
# tui/src/commands/, tui/src/theme/, tui/src/components/coordinator/,
# tui/src/components/conversation/) that carries an FR-011 attribution header.
# Diffs the lifted content (after the header line) against the upstream source
# at .references/claude-code-sourcemap/restored-src/.
#
# Exit codes:
#   0 — all lifted files match upstream (zero divergence)
#   1 — one or more files diverge
#
# Usage:
#   bash tui/scripts/diff-upstream.sh
#
# FR-011, FR-013, SC-9 — Spec 287, ADR-004

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REFERENCES_ROOT="$REPO_ROOT/.references/claude-code-sourcemap/restored-src"

# Directories to walk. Non-existent dirs are skipped gracefully.
LIFTED_DIRS=(
  "tui/src/ink"
  "tui/src/utils"
  "tui/src/commands"
  "tui/src/theme"
  "tui/src/components/coordinator"
  "tui/src/components/conversation"
  "tui/src/hooks"
)

TOTAL=0
PASS=0
DIVERGENT=0
MISSING_SOURCE=0
NO_HEADER=0

TMP_LIFTED=$(mktemp)
trap 'rm -f "$TMP_LIFTED"' EXIT

check_file() {
  local lifted_path="$1"   # absolute path to lifted file

  # Read first line
  local first_line
  first_line=$(head -1 "$lifted_path")

  # Skip files without FR-011 header (KOSMOS-original files)
  if ! echo "$first_line" | grep -q "Source: .references/claude-code-sourcemap/restored-src/"; then
    return 0
  fi

  TOTAL=$((TOTAL + 1))

  # Extract the source path embedded in the header
  # Format: // Source: .references/claude-code-sourcemap/restored-src/<path> (Claude Code 2.1.88, research-use)
  local source_rel
  source_rel=$(echo "$first_line" | sed 's|.*Source: .references/claude-code-sourcemap/restored-src/||;s| (Claude Code.*||')

  local upstream_file="$REFERENCES_ROOT/$source_rel"

  # Check upstream exists
  if [ ! -f "$upstream_file" ]; then
    echo "STALE-SOURCE: $lifted_path"
    echo "  -> upstream path not found: $upstream_file"
    MISSING_SOURCE=$((MISSING_SOURCE + 1))
    PASS=$((PASS + 1))  # stale-source is a warning, not a failure (per ADR-004 §5)
    return 0
  fi

  # Strip header line (line 1) from lifted file into temp file
  tail -n +2 "$lifted_path" > "$TMP_LIFTED"

  # Diff stripped content against upstream
  if diff -q "$TMP_LIFTED" "$upstream_file" > /dev/null 2>&1; then
    PASS=$((PASS + 1))
  else
    echo "DIVERGENT: $lifted_path"
    echo "  -> upstream: $upstream_file"
    diff --unified=3 "$upstream_file" "$TMP_LIFTED" | head -30 || true
    DIVERGENT=$((DIVERGENT + 1))
  fi
}

# Walk each directory
for dir in "${LIFTED_DIRS[@]}"; do
  abs_dir="$REPO_ROOT/$dir"
  if [ ! -d "$abs_dir" ]; then
    # Gracefully skip missing dirs (e.g., tui/src/commands/ not yet created)
    continue
  fi

  while IFS= read -r -d '' filepath; do
    check_file "$filepath"
  done < <(find "$abs_dir" \( -name "*.ts" -o -name "*.tsx" \) -print0)
done

# Summary
echo ""
echo "=== diff-upstream.sh summary ==="
echo "Files checked  : $TOTAL"
echo "Pass           : $PASS"
echo "Divergent      : $DIVERGENT"
echo "Stale-source   : $MISSING_SOURCE (warning only — upstream may have been updated)"

if [ "$DIVERGENT" -gt 0 ]; then
  echo ""
  echo "ERROR: $DIVERGENT file(s) diverge from upstream. Lift content must match restored-src byte-for-byte."
  exit 1
fi

echo ""
echo "OK: All lifted files match upstream."
exit 0
