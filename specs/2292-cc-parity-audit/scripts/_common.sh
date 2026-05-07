#!/usr/bin/env bash
# Shared helpers for Epic α (Initiative #2290) — CC parity audit scripts.
# Sourced by enumerate-files.sh, verify-import-diff.sh.

# Resolve repo root (works regardless of caller's cwd).
KOSAX_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [[ -z "$KOSAX_ROOT" ]]; then
  echo "ERROR: not inside a git repository" >&2
  exit 1
fi

# Canonical input directories (read-only).
KOSAX_DIR="$KOSAX_ROOT/tui/src"
CC_DIR="$KOSAX_ROOT/.references/claude-code-sourcemap/restored-src/src"

# Output base.
AUDIT_DIR="$KOSAX_ROOT/specs/2292-cc-parity-audit"
DATA_DIR="$AUDIT_DIR/data"

# Force deterministic byte-order sort across macOS BSD / Linux GNU coreutils.
export LC_ALL=C

# Sanity check inputs exist.
if [[ ! -d "$KOSAX_DIR" ]]; then
  echo "ERROR: KOSAX_DIR not found: $KOSAX_DIR" >&2
  exit 1
fi
if [[ ! -d "$CC_DIR" ]]; then
  echo "ERROR: CC_DIR not found: $CC_DIR" >&2
  exit 1
fi
if [[ ! -d "$DATA_DIR" ]]; then
  echo "ERROR: DATA_DIR not found: $DATA_DIR (run T001 first)" >&2
  exit 1
fi

export KOSAX_ROOT KOSAX_DIR CC_DIR AUDIT_DIR DATA_DIR
