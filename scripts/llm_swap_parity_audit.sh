#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Spec 2521 — LLM Swap-Surface CC Parity Audit
#
# Verifies the rebuild branch maintains strict CC byte-copy + bounded swap
# methodology. Exits 0 on PASS, 1 on DRIFT, 2 on TOOL ERROR, 78 on CONFIG ERROR.
#
# Contract: specs/2521-llm-swap-cc-rebuild/contracts/parity-audit-cli.md
# Scaffold per task T003 (full implementation in T026-T034).

set -euo pipefail

JSON_OUTPUT=0
STRICT=0
VERBOSE=0
PRINT_HELP=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json) JSON_OUTPUT=1; shift ;;
    --strict) STRICT=1; shift ;;
    --verbose) VERBOSE=1; shift ;;
    -h|--help) PRINT_HELP=1; shift ;;
    *)
      echo "Unknown flag: $1" >&2
      echo "Usage: $0 [--json] [--strict] [--verbose] [-h|--help]" >&2
      exit 78
      ;;
  esac
done

if [[ $PRINT_HELP -eq 1 ]]; then
  cat <<'HELP'
LLM Swap-Surface CC Parity Audit (Spec 2521)

Usage: scripts/llm_swap_parity_audit.sh [--json] [--strict] [--verbose]

Flags:
  --json      Emit ParityAuditOutcome as JSON to stdout.
  --strict    Treat warnings as failures (exit 1 on any warning).
  --verbose   Print classification details for every commit + channel.
  -h, --help  Show this help.

Exit codes:
  0  PASS — no drift detected
  1  DRIFT — unjustified hunk OR byte-copy SHA mismatch OR missing citation
  2  TOOL ERROR — required binary missing (sha256sum, git, awk)
  78 CONFIG ERROR — invoked from wrong dir or branch malformed

Spec: specs/2521-llm-swap-cc-rebuild/spec.md FR-004 + FR-005 + FR-009
Contract: specs/2521-llm-swap-cc-rebuild/contracts/parity-audit-cli.md
HELP
  exit 0
fi

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git not found in PATH" >&2
  exit 2
fi

if command -v sha256sum >/dev/null 2>&1; then
  SHA256_CMD="sha256sum"
elif command -v shasum >/dev/null 2>&1; then
  SHA256_CMD="shasum -a 256"
else
  echo "ERROR: neither sha256sum nor shasum found" >&2
  exit 2
fi

if ! command -v awk >/dev/null 2>&1; then
  echo "ERROR: awk not found in PATH" >&2
  exit 2
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "ERROR: not in a git repository" >&2
  exit 78
}
cd "$REPO_ROOT"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
PARITY_MATRIX="$REPO_ROOT/specs/2521-llm-swap-cc-rebuild/parity-matrix.md"

if [[ ! -f "$PARITY_MATRIX" ]]; then
  echo "ERROR: parity-matrix.md not found at $PARITY_MATRIX" >&2
  exit 78
fi

if [[ $JSON_OUTPUT -eq 1 ]]; then
  cat <<JSON
{
  "run_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "branch": "$CURRENT_BRANCH",
  "status": "scaffold",
  "message": "scripts/llm_swap_parity_audit.sh scaffold per T003 — full audit logic populated in T026-T034",
  "per_file": [],
  "unjustified_hunks": [],
  "missing_cc_citations": [],
  "stream_channel_coverage": [],
  "exit_code": 0
}
JSON
else
  cat <<MD
## LLM Swap-Surface Parity Audit (Spec 2521)

**Branch**: $CURRENT_BRANCH
**Run**: $(date -u +%Y-%m-%dT%H:%M:%SZ)
**Status**: SCAFFOLD (T003 — full audit in T026-T034)

This is the scaffold from task T003. Full audit logic is populated incrementally
during the rebuild (T026-T034). Run again on the rebuild branch after T034 for
the real PASS/DRIFT verdict.

For now this scaffold exits 0 to unblock CI smoke; replace exit 0 with the
real audit's exit code once T026-T034 finalise the implementation.
MD
fi

if [[ $STRICT -eq 1 && $VERBOSE -eq 1 ]]; then
  echo "[verbose] STRICT mode + VERBOSE mode acknowledged; full implementation in T026-T034." >&2
fi

exit 0
