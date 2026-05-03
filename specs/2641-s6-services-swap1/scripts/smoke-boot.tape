# SPDX-License-Identifier: Apache-2.0
# Spec 2641 · T009 — Layer 4 vhs visual smoke for S6 services swap-1.
#
# Captures 3 PNG keyframes proving the TUI boots and renders normally
# despite the api/client.ts dedup + teamMemorySync 박제 + settingsSync 박제
# changes. Lead Opus reads each PNG via the Read tool to confirm visual
# fidelity (no rendering regressions, no error overlays).

Output specs/2641-s6-services-swap1/scripts/smoke-boot.gif
Set FontSize 14
Set Width 1400
Set Height 800
Set TypingSpeed 60ms
Set Theme "Dracula"

# Repo root: vhs runs from cwd; we cd into tui/.
Type "cd tui && bun run tui"
Enter
Sleep 6s
Screenshot specs/2641-s6-services-swap1/scripts/smoke-keyframe-1-boot.png

# Stage 2 — interactive prompt readiness + /help typed
Type "/help"
Sleep 1s
Screenshot specs/2641-s6-services-swap1/scripts/smoke-keyframe-2-help-typed.png

# Stage 3 — /help dropdown rendered (proves REPL alive after services init)
Enter
Sleep 3s
Screenshot specs/2641-s6-services-swap1/scripts/smoke-keyframe-3-help-rendered.png

# Clean exit
Ctrl+c
Sleep 0.3s
Ctrl+c
Sleep 1s
