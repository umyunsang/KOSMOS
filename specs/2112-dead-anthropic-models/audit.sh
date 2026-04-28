#!/usr/bin/env bash
# KOSMOS Epic #2112 — P1 Dead Anthropic Model Matrix Removal · Audit Script
# Implements C1-C11 contracts from contracts/audit-contract.md.
# Usage: bash specs/2112-dead-anthropic-models/audit.sh [Cn ...]
#        (no args = run all C1-C11)
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

PASS=0
FAIL=0
declare -a results=()

emit() {
  local id="$1" status="$2" detail="$3"
  results+=("$(printf '%-4s %-4s %s' "$id" "$status" "$detail")")
  if [[ "$status" == "PASS" ]]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi
}

c1() {
  local hits
  hits=$(rg -n -i 'claude-3|claude-opus|claude-sonnet|claude-haiku|"sonnet"|"opus"|"haiku"|anthropic' \
        tui/src/utils/model/ tui/src/services/mockRateLimits.ts tui/src/services/rateLimitMocking.ts 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$hits" == "0" ]]; then
    emit C1 PASS "regex 0 hits in SC-1 perimeter"
  else
    emit C1 FAIL "$hits regex hits found (expected 0)"
  fi
}

c2() {
  local missing=0
  if [[ -f tui/src/services/mockRateLimits.ts ]]; then missing=$((missing+1)); fi
  if [[ -f tui/src/services/rateLimitMocking.ts ]]; then missing=$((missing+1)); fi
  if [[ "$missing" == "0" ]]; then
    emit C2 PASS "both target services files absent"
  else
    emit C2 FAIL "$missing target file(s) still present"
  fi
}

c3() {
  # FR-012: "MUST NOT INTRODUCE A NEW K-EXAONE literal at any other location."
  # Prod sites (excluding tests/ which legitimately hardcode wire fixtures):
  #   src/kosmos/llm/config.py:37          (FR-012 anchor)
  #   tui/src/utils/model/model.ts:179,187 (FR-012 anchor)
  #   tui/src/ipc/llmClient.ts:31          (pre-existing — Spec 1633 query engine)
  #   tui/src/tools/TranslateTool/TranslateTool.ts:64 (pre-existing — Spec 022 main-tool)
  # Baseline = 5 prod literals. Any addition by P1 = FR-012 violation.
  local lines
  lines=$(rg -n 'K-EXAONE-236B-A23B' --type ts --type py --glob '!tests/**' 2>/dev/null | sort -u | wc -l | tr -d ' ')
  if [[ "$lines" -le "5" ]]; then
    emit C3 PASS "$lines prod K-EXAONE literal(s) (≤5 baseline; tests/ excluded)"
  else
    emit C3 FAIL "$lines prod K-EXAONE literals (>5 baseline, FR-012 violated)"
  fi
}

c4() {
  local hits
  hits=$(rg -n 'temperature: float = 1\.0|top_p: float = 0\.95|presence_penalty: float = 0\.0|max_tokens: int = 1024' src/kosmos/llm/client.py 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$hits" -ge "8" ]]; then
    emit C4 PASS "$hits sampling-default matches (≥8 expected)"
  else
    emit C4 FAIL "$hits sampling-default matches (<8, FR-013 violated)"
  fi
}

c5() {
  local hits
  hits=$(rg -n 'class RetryPolicy|_compute_rate_limit_delay|_is_rate_limit_envelope|_complete_with_retry|_stream_with_retry' src/kosmos/llm/client.py 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$hits" -ge "5" ]]; then
    emit C5 PASS "$hits retry-machinery declarations (≥5 expected)"
  else
    emit C5 FAIL "$hits retry-machinery declarations (<5, FR-014 violated)"
  fi
}

c6() {
  local hits
  hits=$(rg -n 'KOSMOS_K_EXAONE_THINKING|chat_template_kwargs' src/kosmos/llm/client.py 2>/dev/null | wc -l | tr -d ' ')
  if [[ "$hits" -ge "2" ]]; then
    emit C6 PASS "$hits enable_thinking ref(s) (≥2 expected)"
  else
    emit C6 FAIL "$hits enable_thinking refs (<2, FR-015 violated)"
  fi
}

c7() {
  local added
  added=$(git diff main...HEAD -- tui/package.json pyproject.toml 2>/dev/null | rg -E '^\+\s*"[^"]+"\s*:' | wc -l | tr -d ' ')
  if [[ "$added" == "0" ]]; then
    emit C7 PASS "0 added dependency lines"
  else
    emit C7 FAIL "$added added dependency line(s) (FR-009 violated)"
  fi
}

c8() {
  emit C8 SKIP "run \`cd tui && bun test\` and \`uv run pytest\` manually; expect ≥984 / ≥437"
}

c9() {
  emit C9 SKIP "run \`bun run tui\` smoke per quickstart.md §3"
}

c10() {
  local total=0 actual
  for f in tui/src/utils/model/modelOptions.ts tui/src/utils/model/model.ts; do
    if [[ -f "$f" ]]; then
      actual=$(wc -l <"$f" | tr -d ' ')
      total=$((total + actual))
    fi
  done
  if [[ "$total" -le "1211" ]]; then
    emit C10 PASS "$total LOC across modelOptions.ts + model.ts (≤1211 = ≥40% drop)"
  else
    emit C10 FAIL "$total LOC across modelOptions.ts + model.ts (>1211, SC-006 violated)"
  fi
}

c11() {
  # NOTE: regex 0-hit invariant (FR-001) means we cannot use the literal
  # "Anthropic" / "Sonnet" / "Opus" / "Haiku" tokens to grep helper names.
  # Match by the function-prefix `getDefault` followed by the legacy family.
  local helpers=("getDefaultSonnetModel" "getDefaultOpusModel" "getDefaultHaikuModel")
  local missing=()
  for h in "${helpers[@]}"; do
    if rg -q "function $h" tui/src/utils/model/model.ts 2>/dev/null; then
      # helper exists — search a 6-line window before the function definition
      # for the [Deferred to P2] annotation (matches the leading JSDoc/comment).
      if rg -B6 "function $h" tui/src/utils/model/model.ts 2>/dev/null | rg -q "\[Deferred to P2"; then
        :
      else
        missing+=("$h")
      fi
    fi
    # If the helper is absent (removed), no annotation is required — pass.
  done
  if [[ "${#missing[@]}" == "0" ]]; then
    emit C11 PASS "all 3 helpers either removed or [Deferred to P2] annotated"
  else
    emit C11 FAIL "missing [Deferred to P2] annotation: ${missing[*]}"
  fi
}

# Dispatch
ALL=(c1 c2 c3 c4 c5 c6 c7 c8 c9 c10 c11)
if [[ $# -eq 0 ]]; then
  for fn in "${ALL[@]}"; do "$fn"; done
else
  for arg in "$@"; do
    fn=$(echo "$arg" | tr 'A-Z' 'a-z')
    if declare -F "$fn" >/dev/null; then "$fn"; else echo "Unknown contract: $arg" >&2; fi
  done
fi

echo "===== KOSMOS #2112 Audit Results ====="
printf '%s\n' "${results[@]}"
echo "----- Summary: $PASS pass / $FAIL fail -----"
[[ "$FAIL" == "0" ]] && exit 0 || exit 1
