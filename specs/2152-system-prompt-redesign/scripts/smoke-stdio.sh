#!/usr/bin/env bash
# Backend stdio JSONL smoke — sends 5 citizen scenarios sequentially through
# the KOSMOS backend stdio bridge, captures the response frames as .jsonl
# per scenario plus an aggregated smoke.txt with the SC-1 grep audit at the
# end. Memory `feedback_vhs_tui_smoke` Layer 2.
set -euo pipefail

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)"
SPEC_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

set -a
# shellcheck disable=SC1091
source "${REPO_ROOT}/.env"
set +a

if [[ -z "${KOSMOS_FRIENDLI_TOKEN:-}" ]]; then
  echo "ERROR: KOSMOS_FRIENDLI_TOKEN not set after sourcing .env" >&2
  exit 2
fi

SESSION="$(uuidgen | tr '[:upper:]' '[:lower:]')"
TS="$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"

declare -a SCENARIOS=(
  "location|강남역 어디야?"
  "weather|오늘 서울 날씨 알려줘"
  "emergency|근처 응급실 알려줘"
  "koroad|어린이 보호구역 사고 다발"
  "greeting|안녕"
)

AGG="${SPEC_DIR}/smoke.txt"
: > "${AGG}"
{
  echo "==== KOSMOS Epic #2152 P5 stdio smoke ===="
  echo "date:    ${TS}"
  echo "branch:  $(git rev-parse --abbrev-ref HEAD)"
  echo "commit:  $(git rev-parse --short HEAD)"
  echo "session: ${SESSION}"
  echo
} >>"${AGG}"

run_scenario() {
  local slug="$1"
  local prompt="$2"
  local out="${SPEC_DIR}/smoke-stdio-${slug}.jsonl"
  local cid
  cid="$(uuidgen | tr '[:upper:]' '[:lower:]')"

  # JSONL frame — note version="1.0" string, role="tui", schema-strict.
  local frame
  frame=$(python3 -c "
import json, sys
print(json.dumps({
    'version': '1.0',
    'kind': 'chat_request',
    'role': 'tui',
    'session_id': '${SESSION}',
    'correlation_id': '${cid}',
    'frame_seq': 0,
    'ts': '${TS}',
    'messages': [{'role': 'user', 'content': '''${prompt}'''}],
    'tools': [],
    'system': '',
}, ensure_ascii=False))
")

  {
    echo "# scenario=${slug} prompt=${prompt}"
    echo "# session=${SESSION} cid=${cid}"
  } >"${out}"

  # Pipe the frame to backend, capture stdout for ~30s, then close stdin.
  # Backend streams assistant_chunk frames; tool_call frames appear when
  # K-EXAONE invokes a Korean public-data tool.
  (
    printf '%s\n' "${frame}"
    sleep 30
  ) | uv run kosmos --ipc stdio 2>/dev/null >>"${out}" || true

  # Per-scenario summary.
  local total tool_n done_n
  total=$(grep -c '^{' "${out}" || echo 0)
  tool_n=$(grep -c '"kind":"tool_call"' "${out}" || echo 0)
  done_n=$(grep -c '"done":true' "${out}" || echo 0)
  {
    echo "==== scenario: ${slug} ===="
    echo "prompt: ${prompt}"
    echo "frames: ${total}  tool_calls: ${tool_n}  done: ${done_n}"
    # Extract assistant text deltas concatenated as a readable transcript.
    python3 - "${out}" <<'PY'
import json, sys
try:
    text = []
    for line in open(sys.argv[1], encoding="utf-8"):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            f = json.loads(line)
        except json.JSONDecodeError:
            continue
        if f.get("kind") == "assistant_chunk" and f.get("delta"):
            text.append(f["delta"])
        elif f.get("kind") == "tool_call":
            print(f"  [tool_call] {f.get('name', '?')}({f.get('arguments', '')[:80]})")
    if text:
        print("  reply:", "".join(text)[:500])
except Exception as e:
    print(f"  parse-error: {e}")
PY
    echo
  } >>"${AGG}"
}

for entry in "${SCENARIOS[@]}"; do
  IFS='|' read -r slug prompt <<<"${entry}"
  echo ">>> ${slug}: ${prompt}"
  run_scenario "${slug}" "${prompt}"
done

# Aggregate audit
{
  echo "==== aggregate ===="
  T=$(grep -c '"kind":"tool_call"' "${SPEC_DIR}"/smoke-stdio-*.jsonl | awk -F: '{s+=$2} END {print s+0}')
  S=$(for f in "${SPEC_DIR}"/smoke-stdio-*.jsonl; do
    if grep -q '"kind":"tool_call"' "$f"; then echo 1; else echo 0; fi
  done | awk '{s+=$1} END {print s+0}')
  echo "total tool_call frames: ${T}"
  echo "scenarios with ≥1 tool_call: ${S}/5"
  if [[ "${S}" -ge 3 ]]; then
    echo "SC-1 verdict: PASS (≥3 of 5)"
  else
    echo "SC-1 verdict: FAIL (${S} < 3 of 5)"
  fi
} >>"${AGG}"

echo "smoke complete: ${AGG}"
