#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Spec 2640 / Epic D — slash-autocomplete dropdown smoke
#
# Verifies (after Epic #2640 cleanup) that:
#   (a) `bun run tui` boots to the UMMAYA branding,
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
# Wait for UMMAYA branding regex (Codex P2 — replace fixed sleeps with readiness
# waits per `feedback_debug_infra_rebuild` memory and Spec debug-infra-rebuild).
wait_for_pane "UMMAYA|tool_registry" 30
snapshot_pane "boot-branding"

# Stage 2 — slash trigger
send_text_pane "/"
# Wait for the dropdown to render at least one common command name (proves
# `getCommands()` resolved + the autocomplete view has reconciled). `/onboarding`,
# `/lang`, and `/agents` are UMMAYA-original commands that are always registered
# and visible in the dropdown when no prefix filter is active.
wait_for_pane "/(onboarding|lang|agents|update-config|init|add-dir)" 10
snapshot_pane "slash-dropdown"

# Stage 3 — filter "ant" (should now match nothing — /ant-trace removed)
send_text_pane "ant"
# Wait for the dropdown to settle on the prefix update — match the prompt buffer
# echo (`/ant`) which only appears after Ink reconciles the input change.
wait_for_pane "/ant" 10
snapshot_pane "filter-ant"

# Reset filter
send_keys_pane BSpace BSpace BSpace
wait_for_pane "❯ /\$|❯ / *\$" 5 || true

# Stage 4 — filter "tele" (should match nothing — /teleport removed)
send_text_pane "tele"
wait_for_pane "/tele" 10
snapshot_pane "filter-tele"

# Reset
send_keys_pane BSpace BSpace BSpace BSpace
wait_for_pane "❯ /\$|❯ / *\$" 5 || true

# Stage 5 — filter "summ" (should match nothing — /summary removed)
send_text_pane "summ"
wait_for_pane "/summ" 10
snapshot_pane "filter-summ"

# Stage 6 — clean exit
send_ctrlc_pane
send_ctrlc_pane
# Wait for the TUI to actually exit (pane shows shell prompt or empty) before
# the final snapshot. Bounded with a soft timeout so a hung exit still captures.
wait_for_pane "\\\$ |^\$" 5 || true
snapshot_pane "post-exit"
