# SPDX-License-Identifier: Apache-2.0
# Spec 2296 Epic ε T038 — Layer 4 vhs visual + PNG keyframes for the citizen
# tax-return filing chain smoke. Companion to the Layer 2 expect transcript at
# smoke-citizen-taxreturn-pty.txt.
#
# Per AGENTS.md § TUI verification — Layer 4 mandate (promoted 2026-04-29):
#   - Emits BOTH animated Output .gif AND 3+ named Screenshot .png keyframes
#   - Keyframes are LLM-reviewable via the Read tool (multimodal vision)
#   - The animated .gif alone is no longer sufficient
#   - Lead Opus uses Read tool on each PNG before push
#
# Run from the repo root:
#   vhs specs/2296-ax-mock-adapters/scripts/smoke-citizen-taxreturn.tape
#
# Outputs:
#   specs/2296-ax-mock-adapters/smoke-citizen-taxreturn.gif       (animated, full chain)
#   specs/2296-ax-mock-adapters/smoke-keyframe-1-boot.png         (boot + KOSMOS branding)
#   specs/2296-ax-mock-adapters/smoke-keyframe-2-input.png        (citizen query typed in)
#   specs/2296-ax-mock-adapters/smoke-keyframe-3-action.png       (post-approval state / 접수번호)
#
# Reference: specs/2294-5-primitive-align/scripts/smoke-emergency-lookup.tape

Output specs/2296-ax-mock-adapters/smoke-citizen-taxreturn.gif
Set Width 1200
Set Height 700
Set FontSize 14
Set FontFamily "JetBrains Mono"
Set Theme "TokyoNightStorm"

# Use the real Mock backend (registered at KOSMOS_BACKEND_CMD by the TUI IPC bridge).
Env KOSMOS_BACKEND_CMD "uv run python -m kosmos.ipc.demo.mock_backend"

# KOSMOS_FORCE_INTERACTIVE=1: required under vhs PTY because Bun's
# process.stdout.isTTY is undefined in vhs-driven PTY sessions.
# See KOSMOS-1978 T003b and main.tsx:398.
Env KOSMOS_FORCE_INTERACTIVE "1"

Type "cd /Users/um-yunsang/KOSMOS-w-2296/tui && bun run tui"
Enter
Sleep 8s

# Keyframe 1: boot + KOSMOS branding visible
Screenshot specs/2296-ax-mock-adapters/smoke-keyframe-1-boot.png

# Citizen Korean query — exercises the agentic loop / verify → lookup → submit
Type "내 종합소득세 신고해줘"
Enter
Sleep 4s

# Keyframe 2: citizen query typed in, agentic loop processing
Screenshot specs/2296-ax-mock-adapters/smoke-keyframe-2-input.png

# Wait for permission prompt + approval flow + submit result (접수번호)
# Full chain (verify→lookup→submit) takes up to 30s with a live LLM.
# With mock backend alone (no LLM), the TUI stays in the processing state —
# keyframe 3 captures whatever final state is reachable.
Sleep 16s

# Keyframe 3: post-action state — 접수번호 surfaced (live LLM) or
# agentic-loop processing state (no LLM / mock-only path)
Screenshot specs/2296-ax-mock-adapters/smoke-keyframe-3-action.png

# Clean exit
Ctrl+C
Sleep 500ms
Ctrl+C
Sleep 1s
