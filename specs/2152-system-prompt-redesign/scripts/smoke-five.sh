#!/usr/bin/env bash
# Five-scenario citizen smoke — drives the live TUI through the canonical
# spec.md user-stories, captures each as text, aggregates into smoke.txt.
set -euo pipefail

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)"
SPEC_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
ONE="${SPEC_DIR}/scripts/smoke-one.sh"
AGG="${SPEC_DIR}/smoke.txt"

set -a
# shellcheck disable=SC1091
source "${REPO_ROOT}/.env"
set +a

if [[ -z "${KOSMOS_FRIENDLI_TOKEN:-}" ]]; then
  echo "ERROR: KOSMOS_FRIENDLI_TOKEN not set after sourcing .env" >&2
  exit 2
fi

# (slug, prompt, wait_seconds) per scenario.
declare -a SCENARIOS=(
  "location|강남역 어디야?|75"
  "weather|오늘 서울 날씨 알려줘|75"
  "emergency|근처 응급실 알려줘|75"
  "koroad|어린이 보호구역 사고 다발|75"
  "greeting|안녕|45"
)

: > "${AGG}"
echo "==== KOSMOS Epic #2152 P5 citizen smoke run ====" | tee -a "${AGG}"
echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "${AGG}"
echo "branch: $(git rev-parse --abbrev-ref HEAD)" | tee -a "${AGG}"
echo "commit: $(git rev-parse --short HEAD)" | tee -a "${AGG}"
echo | tee -a "${AGG}"

for entry in "${SCENARIOS[@]}"; do
  IFS='|' read -r slug prompt wait_s <<<"${entry}"
  echo "==== begin scenario: ${slug} ====" | tee -a "${AGG}"
  echo "prompt: ${prompt}" | tee -a "${AGG}"
  "${ONE}" "${prompt}" "${slug}" "${wait_s}" 2>&1 | tee -a "${AGG}"
  echo "" | tee -a "${AGG}"
  echo "---- transcript: ${slug} ----" | tee -a "${AGG}"
  cat "${SPEC_DIR}/smoke-scenario-${slug}.txt" >> "${AGG}"
  echo "==== end scenario: ${slug} ====" | tee -a "${AGG}"
  echo | tee -a "${AGG}"
done

echo "==== aggregate audit ====" | tee -a "${AGG}"
TC=$(grep -c -E 'tool_use|tool_call' "${AGG}" || true)
DA=$(grep -c -E '기상청|HIRA|도로교통|응급|좌표|주소|행정동' "${AGG}" || true)
LK=$(grep -c -E '/Users/|gitStatus|Current branch|claudeMd' "${AGG}" || true)
echo "SC-1 tool_use|tool_call hits: ${TC:-0}" | tee -a "${AGG}"
echo "  data attribution / Korean place: ${DA:-0}" | tee -a "${AGG}"
echo "SC-4 dev-context leaks: ${LK:-0}" | tee -a "${AGG}"
