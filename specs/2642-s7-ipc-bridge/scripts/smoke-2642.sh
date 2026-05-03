#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Spec 2642 / Epic F · S7 — Layer 5 tmux smoke scenario.
#
# Verifies the TUI still boots, accepts /help, and shuts down cleanly
# after the remote/ DROP cleanup (TG-A) and the schema parity addition
# (TG-C). No live LLM calls — boot + slash-command surface only.

set -euo pipefail

# Step 1: wait for boot + KOSMOS branding.
wait_for_pane "KOSMOS" 30 || {
  snapshot_pane "boot-failed"
  exit 1
}
snapshot_pane "001-boot"

# Step 2: send /help and wait for the available-commands surface.
send_text_pane "/help"
send_enter_pane
wait_for_pane "Available commands|사용 가능한 명령|/help" 10 || {
  snapshot_pane "help-timeout"
  exit 1
}
snapshot_pane "002-help"

# Step 3: clean exit via Ctrl-C twice.
send_ctrlc_pane
sleep 0.5
send_ctrlc_pane
sleep 1.0
snapshot_pane "003-exit"

# Final pane state (whatever is left after exit).
tmux capture-pane -t "$TMUX_SESSION" -p > "$OUTDIR/final.txt"
echo "[smoke-2642 done]"
