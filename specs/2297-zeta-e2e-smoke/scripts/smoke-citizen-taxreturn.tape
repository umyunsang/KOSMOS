# vhs tape — Epic ζ #2297 US1 Layer 4 visual smoke
# Contract: contracts/vhs-keyframe-protocol.md I-K1 through I-K7
#
# Execution:
#   vhs specs/2297-zeta-e2e-smoke/scripts/smoke-citizen-taxreturn.tape
#
# Emits:
#   specs/2297-zeta-e2e-smoke/smoke-citizen-taxreturn.gif     (animated)
#   specs/2297-zeta-e2e-smoke/scripts/smoke-keyframe-1-boot.png
#   specs/2297-zeta-e2e-smoke/scripts/smoke-keyframe-2-dispatch.png
#   specs/2297-zeta-e2e-smoke/scripts/smoke-keyframe-3-receipt.png
#
# Total wall-clock budget: ≤120s (I-K6).
# Keyframes: 3 minimum (I-K2) at boot / dispatch / receipt stages (I-K1).

# I-K1.1 — output path (animated GIF).
Output specs/2297-zeta-e2e-smoke/smoke-citizen-taxreturn.gif

# I-K1.2 — canonical terminal sizing.
Set FontSize 14
Set Width 120
Set Height 36
Set Theme "Tokyo Night"

# I-K1.3 — spawn the TUI.
Type "cd ~/KOSMOS-w-2297/tui && KOSMOS_SMOKE_CHECKPOINTS=true bun run tui"
Enter
Sleep 5s

# I-K1.4 — keyframe 1: boot + KOSMOS branding rendered.
Screenshot specs/2297-zeta-e2e-smoke/scripts/smoke-keyframe-1-boot.png
Sleep 1s

# I-K1.5 — type citizen prompt and submit.
Type "종합소득세 신고해줘"
Sleep 1s
Enter
Sleep 8s

# I-K1.6 — keyframe 2: dispatch active (verify tool_call emitted / spinner visible).
Screenshot specs/2297-zeta-e2e-smoke/scripts/smoke-keyframe-2-dispatch.png
Sleep 1s

# I-K1.7 — wait for chain completion (verify → lookup → submit).
# Mock adapters respond in <1s each; LLM streams ~25s × 3 turns = 75s.
Sleep 60s

# I-K1.8 — keyframe 3: receipt rendered in citizen-facing assistant message.
# Lead Opus uses Read tool on this PNG to assert receipt-id text visible (I-K3).
Screenshot specs/2297-zeta-e2e-smoke/scripts/smoke-keyframe-3-receipt.png

# I-K1.9 — exit cleanly with Ctrl+C.
Ctrl+C
Sleep 1s
Ctrl+C
