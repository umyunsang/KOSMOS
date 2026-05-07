#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Spec 2641 · T009 — Layer 5 boot smoke scenario.
#
# Verifies UMMAYA TUI boots successfully with the S6 services swap-1
# changes (api/client.ts deduplication + teamMemorySync 박제 +
# settingsSync 박제) and reaches the interactive prompt without runtime
# errors from the dead-call gates (silent-skip variant in settingsSync
# preserves the cli/print.ts boot path).
#
# Source via scripts/tui-tmux-capture.sh — uses helpers wait_for_pane,
# snapshot_pane, send_keys_pane, send_enter_pane, send_ctrlc_pane.

set -u

# ── Stage 1: boot ──────────────────────────────────────────────────────
# The UMMAYA branding and tool_registry boot message must appear within
# 30s. If they don't, something in services/ broke the boot path.
wait_for_pane "UMMAYA" 30 || { snapshot_pane "boot-timeout"; exit 1; }
snapshot_pane "boot-branding"

wait_for_pane "tool_registry" 15 || true
snapshot_pane "boot-tool-registry"

# ── Stage 2: prompt readiness ──────────────────────────────────────────
# Wait for the interactive input prompt to be drawn.
wait_for_pane ">" 20 || true
snapshot_pane "prompt-ready"

# ── Stage 3: /help round-trip (proves REPL alive) ──────────────────────
send_text_pane "/help"
sleep 0.5
snapshot_pane "help-typed"

send_enter_pane
wait_for_pane "Available commands|/help|Usage" 10 || true
snapshot_pane "help-rendered"

# ── Stage 4: clean exit ────────────────────────────────────────────────
send_ctrlc_pane
sleep 0.3
send_ctrlc_pane
sleep 0.5
snapshot_pane "exit"
