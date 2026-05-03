#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Spec 2640 / Epic D — slash-autocomplete dropdown smoke
#
# Verifies (after Epic #2640 cleanup) that:
#   (a) `bun run tui` boots to the KOSMOS branding,
#   (b) the slash-autocomplete dropdown does NOT surface deleted commands
#       (/ant-trace, /teleport, /share, /summary, /env, /issue, /good-claude,
#        /bughunter, /perf-issue, /reset-limits, /backfill-sessions,
#        /break-cache, /mock-limits, /oauth-refresh, /debug-tool-call,
#        /autofix-pr, /ctx_viz, /commands, /claude-api*, /verify),
#   (c) clean exit on Ctrl-C × 2.
#
# Sourced by scripts/tui-tmux-capture.sh — receives helpers as exported funcs.
# Required helpers: wait_for_pane, snapshot_pane, send_keys_pane,
#                   send_text_pane, send_enter_pane, send_ctrlc_pane.

set -euo pipefail

# Stage 1 — boot
wait_for_pane "KOSMOS|tool_registry" 30
snapshot_pane "boot-branding"

# Stage 2 — slash trigger
send_text_pane "/"
sleep 1
snapshot_pane "slash-dropdown"

# Stage 3 — filter "ant" (should now match nothing — /ant-trace removed)
send_text_pane "ant"
sleep 1
snapshot_pane "filter-ant"

# Reset filter
send_keys_pane BSpace BSpace BSpace
sleep 0.5

# Stage 4 — filter "tele" (should match nothing — /teleport removed)
send_text_pane "tele"
sleep 1
snapshot_pane "filter-tele"

# Reset
send_keys_pane BSpace BSpace BSpace BSpace
sleep 0.5

# Stage 5 — filter "summ" (should match nothing — /summary removed)
send_text_pane "summ"
sleep 1
snapshot_pane "filter-summ"

# Stage 6 — clean exit
send_ctrlc_pane
sleep 0.3
send_ctrlc_pane
sleep 0.5
snapshot_pane "post-exit"
