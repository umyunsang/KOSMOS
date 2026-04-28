# KOSMOS Epic #2112 — Citizen E2E smoke (vhs visual scenario flow).
# Output: smoke.gif (interactive UI capture) + per-step PNG snapshots.
#
# Per memory feedback_vhs_tui_smoke: text log (smoke.txt via expect) is the
# single grep-source-of-truth for LLM/Codex audits. This .tape adds visual
# verification on top — humans can scrub the GIF to confirm interactive UI
# actually paints (logo, prompt, streaming, primitive call rendering).
#
# Scenarios (E2E):
#   1. Splash + greeting       — "안녕하세요" → Korean reply paint
#   2. Slash autocomplete      — "/" → command dropdown
#   3. Help command            — "/help" → commands list
#   4. Public-service lookup   — "강남역 어디?" → lookup primitive OR direct answer
#   5. Weather routing         — "오늘 서울 날씨" → KMA forecast tool OR direct answer
#   6. Clean exit              — "/quit"

Output specs/2112-dead-anthropic-models/smoke.gif
Set FontSize 14
Set Width 1400
Set Height 800
Set TypingSpeed 60ms
Set Theme "Dracula"

# Repo root (vhs runs from cwd; we cd into tui/).
Type "cd tui && bun run tui"
Enter
Sleep 8s
Screenshot specs/2112-dead-anthropic-models/smoke-scenario-0-launch.png

# Scenario 1 — Korean greeting
Type "안녕하세요"
Enter
Sleep 18s
Screenshot specs/2112-dead-anthropic-models/smoke-scenario-1-greeting.png

# Scenario 2 — Slash autocomplete (visual confirmation only)
Type "/"
Sleep 2s
Screenshot specs/2112-dead-anthropic-models/smoke-scenario-2-slash-autocomplete.png
Backspace 1

# Scenario 3 — Help
Type "/help"
Enter
Sleep 6s
Screenshot specs/2112-dead-anthropic-models/smoke-scenario-3-help.png

# Scenario 4 — Public-service lookup
Type "강남역 어디야?"
Enter
Sleep 45s
Screenshot specs/2112-dead-anthropic-models/smoke-scenario-4-lookup.png

# Scenario 5 — Weather routing
Type "오늘 서울 날씨 알려줘"
Enter
Sleep 50s
Screenshot specs/2112-dead-anthropic-models/smoke-scenario-5-weather.png

# Scenario 6 — Clean exit
Type "/quit"
Enter
Sleep 3s
