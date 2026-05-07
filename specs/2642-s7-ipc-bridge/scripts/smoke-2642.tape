# SPDX-License-Identifier: Apache-2.0
# Spec 2642 / Epic F · S7 — Layer 4 vhs visual smoke.
#
# Captures three canonical PNG keyframes proving that:
#   1-boot      — UMMAYA branding renders post-boot (verifies remote/ DROP
#                 from TG-A did not break TUI compile / boot path).
#   2-help      — /help slash command surface paints (verifies REPL.tsx
#                 edit did not break activeRemote selector / SSH fallback).
#   3-input     — input line accepts Korean civic prompt after /help dismiss
#                 (verifies SSH-fallback active-remote selector still wires).
#
# Each PNG is read by Lead Opus via the Read tool to verify rendered UI
# (per AGENTS.md § TUI verification — Layer 4 mandate; the animated GIF
# alone is insufficient because agent Read renders only the first frame).

Output specs/2642-s7-ipc-bridge/smoke-2642.gif
Set Width 1200
Set Height 800
Set FontSize 14
Set TypingSpeed 60ms

Type "cd tui && bun run tui"
Enter
# Boot needs ~10s for Ink to negotiate raw-mode + paint the UMMAYA REPL.
Sleep 12s
Screenshot specs/2642-s7-ipc-bridge/smoke-2642-keyframe-1-boot.png

Type "/help"
Sleep 1s
Enter
Sleep 4s
Screenshot specs/2642-s7-ipc-bridge/smoke-2642-keyframe-2-help.png

Escape
Sleep 1s
Type "오늘 부산 날씨 어때?"
Sleep 2s
Screenshot specs/2642-s7-ipc-bridge/smoke-2642-keyframe-3-input.png

Ctrl+C
Sleep 1s
Ctrl+C
