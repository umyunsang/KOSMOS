# SPDX-License-Identifier: Apache-2.0
# Spec 2294 Epic γ — Layer 4 vhs visual + PNG keyframes for the citizen
# emergency-room lookup smoke. Companion to the Layer 2 expect transcript at
# smoke-emergency-lookup-pty.txt.
#
# Reference impl for the AGENTS.md § TUI verification chain after the
# 2026-04-29 promotion (Layer 4 mandatory + LLM-reviewable Screenshot PNGs).
# See docs/testing.md § Layer 4 — vhs visual + PNG keyframes.
#
# Run from the repo root:
#   vhs specs/2294-5-primitive-align/scripts/smoke-emergency-lookup.tape
# Outputs:
#   specs/2294-5-primitive-align/smoke-emergency-lookup.gif       (animated, humans + animated proof)
#   specs/2294-5-primitive-align/smoke-keyframe-1-boot.png        (LLM Read — boot guard + KOSMOS branding)
#   specs/2294-5-primitive-align/smoke-keyframe-2-input.png       (LLM Read — Korean input accepted)
#   specs/2294-5-primitive-align/smoke-keyframe-3-action.png      (LLM Read — agentic-loop entry)

Output specs/2294-5-primitive-align/smoke-emergency-lookup.gif
Set Width 1200
Set Height 700
Set FontSize 14
Set FontFamily "JetBrains Mono"
Set Theme "TokyoNightStorm"

# Backend mock so the TUI boots without a live FriendliAI key (CI parity).
Env KOSMOS_BACKEND_CMD "sleep 60"

Type "cd tui && bun run tui"
Enter
Sleep 6s
Screenshot specs/2294-5-primitive-align/smoke-keyframe-1-boot.png

# Citizen Korean query — exercises the agentic loop entry path
Type "의정부 응급실 알려줘"
Enter
Sleep 4s
Screenshot specs/2294-5-primitive-align/smoke-keyframe-2-input.png

# Wait for agentic loop to enter the Nucleating / Actioning state
Sleep 6s
Screenshot specs/2294-5-primitive-align/smoke-keyframe-3-action.png

# Clean exit
Ctrl+C
Sleep 500ms
Ctrl+C
Sleep 1s
