#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Codex/operator helper for driving the README demo from outside the t-rec child
# process. t-rec still launches the real ummaya CLI; this script only types into
# the visible macOS Terminal window and waits for visible completion markers.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RAW_DIR="${ROOT_DIR}/package-evidence/readme-demo"
STATUS_FILE="${RAW_DIR}/gui-driver.status"
LOG_FILE="${RAW_DIR}/gui-driver.log"
RUNNER_FILE="${RAW_DIR}/gui-record-runner.sh"
PANE_ID_FILE="${RAW_DIR}/gui-driver.paneid"
SESSION_DIR="${HOME}/.ummaya/memdir/user/sessions/-Users-um-yunsang-UMMAYA"
FPS="${UMMAYA_DEMO_FPS:-10}"
BOOT_TIMEOUT="${UMMAYA_DEMO_BOOT_TIMEOUT:-45}"
ANSWER_TIMEOUT="${UMMAYA_DEMO_ANSWER_TIMEOUT:-180}"
CLEAR_TIMEOUT="${UMMAYA_DEMO_CLEAR_TIMEOUT:-20}"
DEFAULT_PROMPTS="$(cat <<'PROMPTS'
퇴근하고 다대포해수욕장 산책 가도 괜찮을까? 지금 기온이랑 비 오는지만 빠르게 확인해줘.
동아대 승학캠퍼스에서 친구가 갑자기 아프면 지금 바로 연락할 응급실 어디가 가까워? 찾아진 곳만 이름, 주소, 전화번호로 알려줘.
부산 사하구 다대1동에서 오늘 전화해볼 만한 내과나 이비인후과 가까운 3곳만 주소와 전화번호로 알려줘.
정부24에서 주민등록등본 온라인 발급 신청을 진행해줘. 간편인증으로 본인확인하고 접수번호가 나오면 알려줘.
PROMPTS
)"
PROMPTS="${UMMAYA_DEMO_PROMPTS:-$DEFAULT_PROMPTS}"

require_cmd() {
  local cmd="${1:?}"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "missing required command: $cmd" >&2
    exit 127
  fi
}

log_line() {
  printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "$LOG_FILE"
}

terminal_contents() {
  wezterm cli get-text --pane-id "$TARGET_PANE_ID" --start-line 0 --end-line -1 2>/dev/null || true
}

pane_is_ummaya() {
  wezterm cli list --format json 2>/dev/null | grep -Fq '"title": "✳ UMMAYA"'
}

latest_session_file() {
  [[ -d "$SESSION_DIR" ]] || return 1
  local newest_line=""
  local file mtime
  while IFS= read -r file; do
    [[ -f "$file" ]] || continue
    mtime="$(stat -f '%m' "$file" 2>/dev/null || printf '0')"
    if [[ "$mtime" =~ ^[0-9]+$ ]] && (( mtime >= RUN_START_EPOCH )); then
      newest_line+="${mtime}"$'\t'"${file}"$'\n'
    fi
  done < <(find "$SESSION_DIR" -type f -name '*.jsonl' -print 2>/dev/null)
  [[ -n "$newest_line" ]] || return 1
  printf '%s' "$newest_line" | sort -nr | head -n 1 | cut -f2-
}

done_count() {
  local file
  file="$(latest_session_file 2>/dev/null || true)"
  if [[ -z "$file" ]]; then
    printf '0\n'
    return
  fi
  rg -c '"subtype":"turn_duration"' "$file" 2>/dev/null || printf '0\n'
}

assistant_answer_count() {
  local file
  file="$(latest_session_file 2>/dev/null || true)"
  if [[ -z "$file" ]]; then
    printf '0\n'
    return
  fi
  rg -c '"type":"assistant"' "$file" 2>/dev/null || printf '0\n'
}

busy_count() {
  terminal_contents | rg -c '· (Searching|Cooking|Thinking)|✻' || printf '0\n'
}

wait_for_text() {
  local needle="${1:?}"
  local timeout="${2:?}"
  local start
  start="$(date +%s)"
  while true; do
    if terminal_contents | grep -Fq "$needle"; then
      return 0
    fi
    if (( $(date +%s) - start >= timeout )); then
      return 1
    fi
    sleep 1
  done
}

send_line() {
  local text="${1:?}"
  printf '%s\r' "$text" | wezterm cli send-text --pane-id "$TARGET_PANE_ID" --no-paste
}

send_enter() {
  printf '\r' | wezterm cli send-text --pane-id "$TARGET_PANE_ID" --no-paste
}

prompt_may_need_permission() {
  local prompt="${1:?}"
  case "$prompt" in
    *정부24*|*등본*|*발급*|*신청*|*납부*|*인증*|*마이데이터*|*홈택스*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

wait_for_answer() {
  local baseline="${1:?}"
  local baseline_answer="${2:?}"
  local prompt="${3:?}"
  local timeout="${4:?}"
  local start current current_answer approvals next_approval_at elapsed
  start="$(date +%s)"
  approvals=0
  next_approval_at=10
  sleep 5
  while true; do
    elapsed=$(( $(date +%s) - start ))
    current="$(done_count)"
    if [[ "$current" =~ ^[0-9]+$ ]] && (( current > baseline )); then
      sleep 2
      return 0
    fi
    current_answer="$(assistant_answer_count)"
    if [[ "$current_answer" =~ ^[0-9]+$ ]] && (( current_answer > baseline_answer )); then
      sleep 4
      return 0
    fi
    if prompt_may_need_permission "$prompt" && (( approvals < 3 && elapsed >= next_approval_at )); then
      log_line "PERMISSION_APPROVE[$((approvals + 1))] enter"
      send_enter
      approvals=$((approvals + 1))
      next_approval_at=$((next_approval_at + 16))
    fi
    if (( elapsed >= timeout )); then
      return 1
    fi
    sleep 2
  done
}

start_recording_terminal() {
  cat > "$RUNNER_FILE" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT_DIR"
export TERM_PROGRAM=WezTerm
export UMMAYA_TUI_LOCALE=en
export UMMAYA_DEMO_FPS="$FPS"
printf 'running\n' > "$STATUS_FILE"
set +e
npm run demo:readme
status=\$?
set -e
printf 'done:%s\n' "\$status" > "$STATUS_FILE"
exit "\$status"
EOF
  chmod +x "$RUNNER_FILE"

  if ! wezterm cli list --format json >/dev/null 2>&1; then
    open -na WezTerm
    local start
    start="$(date +%s)"
    until wezterm cli list --format json >/dev/null 2>&1; do
      if (( $(date +%s) - start >= 20 )); then
        echo "timed out waiting for WezTerm GUI" >&2
        return 1
      fi
      sleep 1
    done
  fi

  wezterm cli spawn --new-window --cwd "$ROOT_DIR" bash "$RUNNER_FILE"
}

main() {
  require_cmd awk
  require_cmd grep
  require_cmd npm
  require_cmd rg
  require_cmd t-rec
  require_cmd wezterm

  mkdir -p "$RAW_DIR"
  : > "$LOG_FILE"
  rm -f "$STATUS_FILE"
  rm -f "$PANE_ID_FILE"
  RUN_START_EPOCH="$(date +%s)"
  export RUN_START_EPOCH

  log_line "START terminal_size=actual fps=$FPS"
  TARGET_PANE_ID="$(start_recording_terminal | tr -dc '0-9')"
  export TARGET_PANE_ID
  printf '%s\n' "$TARGET_PANE_ID" > "$PANE_ID_FILE"
  log_line "PANE target=$TARGET_PANE_ID"

  log_line "WAIT boot"
  local boot_start
  boot_start="$(date +%s)"
  while true; do
    if pane_is_ummaya && pgrep -f "$ROOT_DIR/bin/ummaya" >/dev/null 2>&1; then
      sleep 4
      break
    fi
    if (( $(date +%s) - boot_start >= BOOT_TIMEOUT )); then
      echo "timed out waiting for UMMAYA boot" >&2
      return 1
    fi
    sleep 1
  done

  local -a clean_prompts=()
  while IFS= read -r prompt; do
    [[ -n "${prompt//[[:space:]]/}" ]] && clean_prompts+=("$prompt")
  done <<< "$PROMPTS"

  local total="${#clean_prompts[@]}"
  local i prompt baseline baseline_answer
  for ((i = 0; i < total; i++)); do
    prompt="${clean_prompts[$i]}"
    baseline="$(done_count)"
    baseline_answer="$(assistant_answer_count)"
    log_line "PROMPT[$((i + 1))/$total] $prompt"
    send_line "$prompt"
    wait_for_answer "$baseline" "$baseline_answer" "$prompt" "$ANSWER_TIMEOUT"
    log_line "DONE[$((i + 1))/$total]"
    if (( i + 1 < total )); then
      send_line "/clear"
      sleep "$CLEAR_TIMEOUT"
    fi
  done

  log_line "EXIT"
  send_line "/exit"

  local start
  start="$(date +%s)"
  while [[ ! -f "$STATUS_FILE" ]] || ! grep -Eq '^done:' "$STATUS_FILE"; do
    if (( $(date +%s) - start >= 180 )); then
      log_line "EXIT_RETRY ctrl-d"
      printf '\004\004' | wezterm cli send-text --pane-id "$TARGET_PANE_ID" --no-paste
      start="$(date +%s)"
    fi
    sleep 2
  done
  log_line "$(cat "$STATUS_FILE")"
}

main "$@"
