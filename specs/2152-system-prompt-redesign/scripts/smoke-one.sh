#!/usr/bin/env bash
# Single-scenario citizen smoke — drives the live TUI through one prompt
# with the user-provided FriendliAI token, captures the session as text.
set -euo pipefail

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)"
SPEC_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
TUI_DIR="${REPO_ROOT}/tui"

set -a
# shellcheck disable=SC1091
source "${REPO_ROOT}/.env"
set +a

if [[ -z "${KOSMOS_FRIENDLI_TOKEN:-}" ]]; then
  echo "ERROR: KOSMOS_FRIENDLI_TOKEN not set after sourcing .env" >&2
  exit 2
fi

PROMPT="${1:-강남역 어디야?}"
SLUG="${2:-location}"
TIMEOUT="${3:-120}"
OUT="${SPEC_DIR}/smoke-scenario-${SLUG}.txt"

echo "==== smoke scenario: ${SLUG} ===="
echo "prompt: ${PROMPT}"
echo "output: ${OUT}"
echo

# expect script — change directory before spawn so `bun run tui` resolves
# correctly against tui/package.json. log_file appends the full pty stream.
expect <<EOF >"${OUT}" 2>&1
log_file -a "${OUT}.raw"
log_user 1
set timeout ${TIMEOUT}
cd "${TUI_DIR}"
spawn -noecho bun run tui
expect {
  -re {>\\s*\$|어떻게 도와|시민과 대화|공공 서비스|✻|⏵} { send -- "${PROMPT}\\r" }
  timeout { puts "ERROR: TUI did not reach REPL prompt"; exit 3 }
}
# Wait for assistant turn to complete or for tool/data signature
expect {
  -re {tool_use|tool_call|기상청|HIRA|도로교통|응급|좌표|주소|경기도|서울시|행정동} { sleep 5 }
  timeout { puts "WARN: scenario did not surface a tool/data signature in ${TIMEOUT}s" }
}
sleep 3
# Send Ctrl-C to exit the TUI
send -- "\\003"
expect eof
EOF

echo
echo "==== capture summary ===="
echo "size: $(wc -c < "${OUT}") bytes"
echo "tool_use|tool_call hits: $(grep -c -E 'tool_use|tool_call' "${OUT}" || echo 0)"
echo "data attribution hits: $(grep -c -E '기상청|HIRA|도로교통|응급|좌표' "${OUT}" || echo 0)"
echo "cwd / path leaks: $(grep -c -E '/Users/|gitStatus|Current branch' "${OUT}" || echo 0)"
