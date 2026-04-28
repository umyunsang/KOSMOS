#!/usr/bin/env bash
# Epic #2152 P5 smoke harness — drive the citizen TUI through five canonical
# scenarios and capture each session as a text log so SC-1 / SC-3 audits can
# grep against deterministic artefacts (memory `feedback_vhs_tui_smoke`).
#
# Requires:
#   - KOSMOS_FRIENDLI_API_KEY set in the environment.
#   - Backend reachable (the TUI auto-starts the Python stdio server).
#   - `expect` available (macOS: `brew install expect`).
#
# Usage:
#   specs/2152-system-prompt-redesign/scripts/run_smoke.sh
#
# Outputs:
#   specs/2152-system-prompt-redesign/smoke-scenario-{1..5}-*.txt
#   specs/2152-system-prompt-redesign/smoke.txt   (aggregated transcript)
set -euo pipefail

SPEC_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
TUI_DIR="$(CDPATH= cd -- "${SPEC_DIR}/../.." && pwd)/tui"
OUT_AGG="${SPEC_DIR}/smoke.txt"

if ! command -v expect >/dev/null 2>&1; then
  echo "ERROR: expect is required (macOS: brew install expect)" >&2
  exit 2
fi

if [[ -z "${KOSMOS_FRIENDLI_API_KEY:-}" ]]; then
  echo "ERROR: KOSMOS_FRIENDLI_API_KEY must be set in the environment" >&2
  exit 2
fi

# Each scenario is { id, slug, prompt, expected_tool_pattern }.
# SC-1 — at least 3 of these 5 must contain a tool_use/tool_call IPC frame.
declare -a SCENARIOS=(
  "1|location|강남역 어디야?|resolve_location"
  "2|weather|오늘 서울 날씨 알려줘|kma_forecast"
  "3|emergency|근처 응급실 알려줘|nmc_emergency_search"
  "4|koroad|어린이 보호구역 사고 다발|koroad"
  "5|greeting|안녕|"
)

: > "${OUT_AGG}"

for scenario in "${SCENARIOS[@]}"; do
  IFS='|' read -r id slug prompt expected <<<"${scenario}"
  out="${SPEC_DIR}/smoke-scenario-${id}-${slug}.txt"
  echo "==== scenario ${id} (${slug}) ====" | tee -a "${OUT_AGG}"
  echo "prompt: ${prompt}" | tee -a "${OUT_AGG}"

  # `expect` automation — launches the TUI, sends the citizen prompt, waits
  # for the assistant turn to settle, then sends Ctrl-C to exit cleanly.
  expect <<EOF | tee "${out}" >>"${OUT_AGG}"
log_file -a "${out}"
set timeout 90
spawn -noecho bun --cwd "${TUI_DIR}" run tui
expect {
  -re "ready|REPL|>" { send -- "${prompt}\r" }
  timeout { puts "ERROR: TUI never reached prompt"; exit 3 }
}
expect {
  -re "tool_use|tool_call|기상청|HIRA|도로교통|응급" { sleep 2 }
  timeout { puts "WARN: scenario ${id} did not visibly trigger a tool"; }
}
sleep 3
send -- ""
expect eof
EOF
  echo "==== end scenario ${id} ====" | tee -a "${OUT_AGG}"
  echo | tee -a "${OUT_AGG}"
done

echo "Aggregated transcript: ${OUT_AGG}"
