# SPDX-License-Identifier: Apache-2.0
# Spec 2521 T025 — Layer 4 vhs visual smoke for thinking_delta render.
#
# Drives the actual TUI through a citizen prompt that triggers K-EXAONE's
# reasoning_content channel. Captures 3 PNG keyframes (boot / thinking /
# final result) for Lead Opus multimodal vision verification.
#
# Acceptance (per spec SC-001): keyframe-2-thinking.png MUST show the
# `∴ Thinking` dim italic glyph rendered between the citizen prompt
# (top of screen) and the first tool_call row.
#
# vhs ≥ 0.11.0 — Screenshot directive supported natively. ScrollUp/Down
# + Ctrl+Arrow chords also available if the scenario expands.

Output specs/2521-llm-swap-cc-rebuild/smoke-thinking-render.gif
Set Width 1200
Set Height 800
Set FontSize 14
Set TypingSpeed 50ms

Type "cd tui && bun run tui"
Enter
Sleep 8s
Screenshot specs/2521-llm-swap-cc-rebuild/smoke-keyframe-1-boot.png

Type "오늘 부산 날씨 어때?"
Enter
Sleep 6s
Screenshot specs/2521-llm-swap-cc-rebuild/smoke-keyframe-2-thinking.png

Sleep 60s
Screenshot specs/2521-llm-swap-cc-rebuild/smoke-keyframe-3-result.png

Ctrl+C
Sleep 500ms
Ctrl+C
