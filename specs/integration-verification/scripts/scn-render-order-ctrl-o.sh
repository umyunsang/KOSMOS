#!/usr/bin/env bash
# Source-only — relies on tui-tmux-capture.sh helpers + env (TMUX_SESSION/OUTDIR)
set -euo pipefail

# Wait for KOSMOS REPL (~/KOSMOS/tui prompt). Boot may take 5–8s.
wait_for_pane "KOSMOS|❯" 25
snapshot_pane 01-boot

# Type the citizen weather query
send_text_pane "부산 사하구 다대1동 날씨 알려줘"
wait_for_pane "부산 사하구 다대1동 날씨 알려줘" 5
snapshot_pane 02-typed
send_enter_pane

# K-EXAONE reasoning + KMA tool calls can take 30-90s. Capture only after
# observable pane states appear; a timeout is a real smoke failure.
wait_for_pane "lookup\\(|Thinking|검색|오류|Tool execution|error" 45
snapshot_pane 03-first-tool-output
wait_for_pane "record|검색 오류|Tool execution|error" 90
snapshot_pane 04-tool-result
wait_for_pane "오늘 날씨 예보|오늘 사하구" 90
snapshot_pane 05-final-answer

# Press Ctrl+O — chord registry path should reveal detailed transcript mode.
send_keys_pane "C-o"
wait_for_pane "Showing detailed transcript" 10
snapshot_pane 06-after-ctrlo

# Press Ctrl+O again — toggle back
send_keys_pane "C-o"
wait_for_pane "❯|/effort|high" 10
snapshot_pane 07-after-ctrlo-toggle

# Clean exit
send_ctrlc_pane
wait_for_pane "Ctrl-C again|exit" 5
snapshot_pane 08-exit-armed
send_ctrlc_pane
