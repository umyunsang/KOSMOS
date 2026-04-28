#!/usr/bin/env bash
# Single-scenario citizen smoke — drives the live TUI through one prompt
# with the user-provided FriendliAI token, captures the session as text via
# script(1) which records the full pty stream including the TUI display.
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
WAIT_RESPONSE="${3:-60}"
OUT="${SPEC_DIR}/smoke-scenario-${SLUG}.txt"

echo "==== smoke scenario: ${SLUG} ====" >&2
echo "prompt: ${PROMPT}" >&2
echo "output: ${OUT}" >&2

# Build a tiny expect script as a temp file; macOS `script -q file cmd args`
# captures the pty session into `file`. The expect driver inside drives the
# TUI: boot wait → send prompt → settle wait → Ctrl-C exit.
EXPECT_FILE="$(mktemp -t kosmos-smoke.XXXXXX)"
trap 'rm -f "${EXPECT_FILE}"' EXIT

cat >"${EXPECT_FILE}" <<EXPECT_EOF
#!/usr/bin/env expect
set timeout [expr {${WAIT_RESPONSE} + 30}]
log_user 1
cd "${TUI_DIR}"
spawn -noecho bun run tui
sleep 6
send -- "${PROMPT}\r"
sleep ${WAIT_RESPONSE}
send -- "\x03"
sleep 1
send -- "\x03"
expect eof
EXPECT_EOF
chmod +x "${EXPECT_FILE}"

# macOS script(1):  script -q output.txt command args...
script -q "${OUT}" "${EXPECT_FILE}" >/dev/null 2>&1 || true

echo >&2
echo "==== capture summary ====" >&2
echo "size: $(wc -c < "${OUT}") bytes" >&2
TC=$(grep -c -E 'tool_use|tool_call' "${OUT}" || true)
DA=$(grep -c -E '기상청|HIRA|도로교통|응급|좌표|주소|행정동|광장구|강남|병원|복지' "${OUT}" || true)
LK=$(grep -c -E '/Users/|gitStatus|Current branch|claudeMd' "${OUT}" || true)
echo "tool_use|tool_call hits: ${TC:-0}" >&2
echo "data attribution / Korean place hits: ${DA:-0}" >&2
echo "cwd / dev-context leaks: ${LK:-0}" >&2
