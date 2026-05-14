#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Rebuild the README demo with t-rec only. No VHS, asciinema, agg, or alternate
# recorder is allowed for this artifact.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FPS="${UMMAYA_DEMO_FPS:-10}"
RAW_DIR="${ROOT_DIR}/package-evidence/readme-demo"
DEMO_PROGRAM="${UMMAYA_DEMO_PROGRAM:-$ROOT_DIR/docs/demo/run-readme-demo.sh}"
FINAL_GIF="${ROOT_DIR}/assets/ummaya-demo.gif"
FINAL_TEXT="${ROOT_DIR}/assets/ummaya-demo.txt"

usage() {
  cat <<'USAGE'
Usage: docs/demo/record-readme-demo.sh

Records the live README demo with t-rec only. This must run from a macOS GUI
terminal that t-rec can identify and that has Screen Recording permission.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

require_cmd() {
  local cmd="${1:?}"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "missing required command: $cmd" >&2
    exit 127
  fi
}

optimize_gif() {
  local input="${1:?}"
  local output="${2:?}"

  if command -v gifsicle >/dev/null 2>&1; then
    gifsicle --lossy=45 -k 96 -O3 "$input" -o "$output"
  else
    cp "$input" "$output"
  fi
}

prepare() {
  mkdir -p "$RAW_DIR" "$(dirname "$FINAL_GIF")"
  rm -f "$RAW_DIR"/ummaya-demo-* "$RAW_DIR"/t-rec.*
  rm -f "$ROOT_DIR/assets/ummaya-demo.cast"
}

require_cmd t-rec
require_cmd bun
[[ -x "$DEMO_PROGRAM" ]] || {
  echo "demo program is not executable: $DEMO_PROGRAM" >&2
  exit 126
}

detect_front_terminal_window_id() {
  if [[ "$(uname -s)" != "Darwin" ]] || ! command -v swift >/dev/null 2>&1; then
    return 1
  fi

  swift -e '
import CoreGraphics
import Darwin

let terminalOwners: Set<String> = ["Terminal", "터미널", "iTerm", "iTerm2", "Ghostty", "WezTerm"]
let options = CGWindowListOption(arrayLiteral: .optionOnScreenOnly, .excludeDesktopElements)
if let windows = CGWindowListCopyWindowInfo(options, kCGNullWindowID) as? [[String: Any]] {
  for window in windows {
    let owner = window[kCGWindowOwnerName as String] as? String ?? ""
    let layer = window[kCGWindowLayer as String] as? Int ?? -1
    if layer == 0 && terminalOwners.contains(owner),
       let id = window[kCGWindowNumber as String] as? UInt32 {
      print(id)
      exit(0)
    }
  }
}
exit(1)
'
}

base="$RAW_DIR/t-rec"

prepare

if [[ -z "${UMMAYA_TREC_WIN_ID:-}" && -z "${WINDOWID:-}" ]]; then
  if detected_win_id="$(detect_front_terminal_window_id 2>/dev/null)" && [[ -n "$detected_win_id" ]]; then
    export UMMAYA_TREC_WIN_ID="$detected_win_id"
    export WINDOWID="$detected_win_id"
  fi
fi

trec_args=(
  --quiet
  --decor none
  --natural
  --fps "$FPS"
  --start-pause 800ms
  --end-pause 4s
  --idle-pause 3s
  --output "$base"
  --video
)
if [[ -n "${UMMAYA_TREC_WIN_ID:-}" ]]; then
  trec_args+=(--win-id "$UMMAYA_TREC_WIN_ID")
fi
trec_args+=("$DEMO_PROGRAM")

UMMAYA_DEMO_TEXT_OUT="$FINAL_TEXT" \
  t-rec "${trec_args[@]}"

[[ -f "$base.gif" ]]
optimize_gif "$base.gif" "$FINAL_GIF"
if [[ -f "$base.mp4" ]]; then
  cp "$base.mp4" "$ROOT_DIR/assets/ummaya-demo.mp4"
fi
{
  printf 'UMMAYA README demo terminal evidence\n'
  printf 'Generated: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'Recorder: t-rec direct live ummaya CLI\n'
  printf 'Program: %s\n' "$DEMO_PROGRAM"
  printf 'WindowId: %s\n' "${UMMAYA_TREC_WIN_ID:-${WINDOWID:-auto}}"
  printf 'Mode: real user-visible terminal session; prompts typed manually or by external GUI driver\n'
  printf '\n'
} > "$FINAL_TEXT"

printf 'README demo generated:\n'
printf '  GIF : %s\n' "$FINAL_GIF"
printf '  TXT : %s\n' "$FINAL_TEXT"
if [[ -f "$ROOT_DIR/assets/ummaya-demo.mp4" ]]; then
  printf '  MP4 : %s\n' "$ROOT_DIR/assets/ummaya-demo.mp4"
fi
