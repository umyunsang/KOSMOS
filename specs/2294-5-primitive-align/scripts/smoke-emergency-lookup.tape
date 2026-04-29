# SPDX-License-Identifier: Apache-2.0
# Spec 2294 Epic γ — VHS visual companion for the citizen emergency-room lookup smoke.
# Layer 3 of AGENTS.md TUI verification chain — companion to the mandatory
# Layer 2 expect transcript at smoke-emergency-lookup-pty.txt.
#
# Run from the repo root:
#   vhs specs/2294-5-primitive-align/scripts/smoke-emergency-lookup.tape
# Output: specs/2294-5-primitive-align/smoke-emergency-lookup.gif

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
Sleep 5s

# Verify boot guard line + KOSMOS branding visible
Sleep 1s

# Citizen Korean query — exercises the agentic loop entry path
Type "의정부 응급실 알려줘"
Enter
Sleep 8s

# Clean exit
Ctrl+C
Sleep 500ms
Ctrl+C
Sleep 1s
