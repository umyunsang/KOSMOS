# KOSAX Epic #2640 — slash-autocomplete dropdown PNG keyframes
# Verifies Stage-1 P0 auto-stub commands (ant-trace, teleport, share, summary,
# env, etc.) are no longer surfaced in the slash autocomplete dropdown after
# Epic #2640 cleanup, and that claude-api / verify bundled skills are removed.
#
# Scenarios:
#   keyframe-1 — boot + branding
#   keyframe-2 — slash dropdown (no /ant-trace, /teleport, /share, /summary)
#   keyframe-3 — filter "ant" (empty match)
#   keyframe-4 — filter "tele" (empty match)
#   keyframe-5 — filter "claude-api" (empty match)
#   keyframe-6 — clean exit

Output specs/2640-s5-commands-skills/smoke.gif
Set FontSize 14
Set Width 1400
Set Height 800
Set TypingSpeed 60ms
Set Theme "Dracula"

Type "cd tui && bun run tui"
Enter
Sleep 6s
Screenshot specs/2640-s5-commands-skills/smoke-keyframe-1-boot.png

# Slash trigger
Type "/"
Sleep 2s
Screenshot specs/2640-s5-commands-skills/smoke-keyframe-2-slash-dropdown.png

# Filter "ant" — /ant-trace removed in Epic #2640
Type "ant"
Sleep 1500ms
Screenshot specs/2640-s5-commands-skills/smoke-keyframe-3-filter-ant.png
Backspace 3

# Filter "tele" — /teleport removed in Epic #2640
Type "tele"
Sleep 1500ms
Screenshot specs/2640-s5-commands-skills/smoke-keyframe-4-filter-tele.png
Backspace 4

# Filter "claude-api" — bundled skill removed in Epic #2640
Type "claude-api"
Sleep 1500ms
Screenshot specs/2640-s5-commands-skills/smoke-keyframe-5-filter-claude-api.png
Backspace 10

# Clean exit
Ctrl+C
Sleep 300ms
Ctrl+C
Sleep 1s
