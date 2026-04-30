# vhs tape — PR #2519 commit 6d5a37e (dispatchPrimitive stub-hide
# verification, retry after Turn 2 5-min timeout in smoke-2519-final).
#
# Single-turn scenario tightly focused on stub-hide:
#   user → "부산 사하구 동아대 위치 알려줘"
#
# Pre-fix: lookup tool block renders with "(어댑터 미상)—1건" + the
#          dispatchPrimitive stub envelope JSON under ⎿.
# Post-fix: each lookup tool block shows only the call line
#          "lookup(search: …)" — the result row is hidden because
#          renderToolResultMessage returns null on stub-envelope detect
#          (UserToolSuccessMessage.tsx:76 short-circuits null).

Output specs/2519-korean-ime-enter-fix/smoke-2519-stub-hide.gif

Set FontSize 14
Set Width 1400
Set Height 900
Set Theme "TokyoNight"

Type "cd ~/KOSMOS/tui && bun run tui"
Enter
Sleep 5s

Screenshot specs/2519-korean-ime-enter-fix/scripts/smoke-keyframe-stub-1-boot.png

Type "부산 사하구 동아대 위치 알려줘"
Sleep 800ms
Enter

# Wait for the lookup tool dispatch to materialise. Backend agentic
# loop fires server-side; spinner runs until the assistant_chunk
# completes. Sleep 30s to capture the active dispatch frame.
Sleep 30s

Screenshot specs/2519-korean-ime-enter-fix/scripts/smoke-keyframe-stub-2-dispatch.png

# Continue waiting up to 90s total for the assistant turn to wind
# down. K-EXAONE Tier 1 latency varies; cap with Sleep 90s.
Sleep 90s

Screenshot specs/2519-korean-ime-enter-fix/scripts/smoke-keyframe-stub-3-final.png

Sleep 2s

Ctrl+C
Sleep 1s
Ctrl+C
