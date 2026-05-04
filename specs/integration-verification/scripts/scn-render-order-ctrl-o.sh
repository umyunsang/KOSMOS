#!/usr/bin/env bash
# Source-only — relies on tui-tmux-capture.sh helpers + env (TMUX_SESSION/OUTDIR)
set -euo pipefail

# Wait for KOSMOS REPL (~/KOSMOS/tui prompt). Boot may take 5–8s.
wait_for_pane "KOSMOS|❯" 25
snapshot_pane 01-boot

# Type the citizen weather query
send_text_pane "부산 사하구 다대1동 날씨 알려줘"
sleep 1
snapshot_pane 02-typed
send_enter_pane

# K-EXAONE reasoning + KMA tool calls. Allow up to 90s for the full agentic
# loop (multiple turns) to settle. Watch for either: success record line OR
# error envelope OR thinking-only stalled state.
sleep 5
snapshot_pane 03-after-5s
sleep 10
snapshot_pane 04-after-15s
sleep 15
snapshot_pane 05-after-30s
sleep 20
snapshot_pane 06-after-50s

# Wait for the lookup record line (or error) before pressing Ctrl+O
wait_for_pane "record|검색|오류|Tool execution|error" 90 || true
snapshot_pane 07-pre-ctrlo

# Press Ctrl+O — chord registry path + raw useInput fallback should both fire
send_keys_pane "C-o"
sleep 1
snapshot_pane 08-after-ctrlo
sleep 2
snapshot_pane 09-after-ctrlo-2s

# Press Ctrl+O again — toggle back
send_keys_pane "C-o"
sleep 1
snapshot_pane 10-after-ctrlo-toggle

# Clean exit
send_ctrlc_pane
sleep 1
send_ctrlc_pane
sleep 1
snapshot_pane 11-final
