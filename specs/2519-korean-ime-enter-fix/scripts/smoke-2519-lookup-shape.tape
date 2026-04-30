# vhs tape — PR #2519 commit f5a2c7a (shape mismatch fix verification)
#
# Verifies the LookupPrimitive renderToolResultMessage fix unwraps the
# backend outer envelope { kind: 'lookup', result: { kind: 'search',
# candidates: [...] } } correctly. Pre-fix: every search rendered
# '(어댑터 미상)' under ⎿. Post-fix: empty search renders the red-coloured
# citizen hint, and a non-empty search renders the ranked candidate list.
#
# Execution:
#   vhs specs/2519-korean-ime-enter-fix/scripts/smoke-2519-lookup-shape.tape
#
# Emits:
#   specs/2519-korean-ime-enter-fix/smoke-2519-lookup-shape.gif
#   specs/2519-korean-ime-enter-fix/scripts/smoke-keyframe-shape-1-input.png
#   specs/2519-korean-ime-enter-fix/scripts/smoke-keyframe-shape-2-tool-call.png
#   specs/2519-korean-ime-enter-fix/scripts/smoke-keyframe-shape-3-result.png

Output specs/2519-korean-ime-enter-fix/smoke-2519-lookup-shape.gif

Set FontSize 14
Set Width 1400
Set Height 900
Set Theme "TokyoNight"

Type "cd ~/KOSMOS/tui && bun run tui"
Enter
Sleep 5s

# Type the citizen query that previously triggered the '(어댑터 미상)'
# regression: 부산 사하구 동아대 위치
Type "부산 사하구 동아대 위치 알려줘"
Sleep 1s

# Keyframe 1 — input typed, before submit.
Screenshot specs/2519-korean-ime-enter-fix/scripts/smoke-keyframe-shape-1-input.png
Sleep 800ms

Enter
Sleep 25s

# Keyframe 2 — first tool call dispatched (spinner running, lookup
# tool_use block visible under the assistant).
Screenshot specs/2519-korean-ime-enter-fix/scripts/smoke-keyframe-shape-2-tool-call.png

# Wait for additional tool turns (agentic loop) so the result rows
# under the ⎿ gutter have time to render.
Sleep 30s

# Keyframe 3 — the critical frame. Should show:
#   - lookup tool blocks rendered with the renderToolUseMessage prefix
#     (e.g. 'lookup(search: ...)')
#   - tool result rows under '  ⎿  ' gutter
#   - if backend returned empty candidates: red text reading
#     '검색 결과가 없습니다 — 다른 도구(resolve_location 등)를 시도하거나
#     시민에게 직접 안내하세요.'
#   - if backend returned candidates: numbered list of tool_id + score
#   - NEVER the pre-fix '(어댑터 미상)' bareword.
Screenshot specs/2519-korean-ime-enter-fix/scripts/smoke-keyframe-shape-3-result.png

Sleep 2s

Ctrl+C
Sleep 800ms
Ctrl+C
