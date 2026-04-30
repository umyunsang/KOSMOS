# vhs tape — PR #2519 hotfix Layer 3 visual smoke
#
# Scope: ASCII path verification that the BaseTextInput.tsx:60 edit (removing
# the `if (isPasting && key.return) return` swallow) does NOT regress the
# normal slash-command Enter flow. Korean IME composition cannot be driven
# from vhs (no IME state machine in the headless renderer); MANUAL-TEST.md
# documents the human-driven Hangul Enter validation steps required before
# merge.
#
# Execution:
#   vhs specs/2519-korean-ime-enter-fix/scripts/smoke-2519.tape
#
# Emits:
#   specs/2519-korean-ime-enter-fix/smoke-2519.gif                      (animated)
#   specs/2519-korean-ime-enter-fix/scripts/smoke-keyframe-1-boot.png
#   specs/2519-korean-ime-enter-fix/scripts/smoke-keyframe-2-help-rendered.png
#   specs/2519-korean-ime-enter-fix/scripts/smoke-keyframe-3-post-enter.png
#
# Total wall-clock budget: ≤45s.
# Keyframes: 3 minimum at boot / help-banner / post-empty-enter stages.

Output specs/2519-korean-ime-enter-fix/smoke-2519.gif

Set FontSize 14
Set Width 1200
Set Height 720
Set Theme "TokyoNight"

# Spawn the TUI.
Type "cd ~/KOSMOS/tui && bun run tui"
Enter
Sleep 5s

# Keyframe 1: boot + KOSMOS branding rendered.
Screenshot specs/2519-korean-ime-enter-fix/scripts/smoke-keyframe-1-boot.png
Sleep 1s

# Type a slash command and submit via real Enter — the keystroke that the
# fix now lets through unconditionally. Without the fix, /help would not
# dispatch when isPasting=true (Korean IME false-positive case).
Type "/help"
Sleep 800ms
Enter
Sleep 3s

# Keyframe 2: help banner rendered (Korean labels — domain data, not source).
Screenshot specs/2519-korean-ime-enter-fix/scripts/smoke-keyframe-2-help-rendered.png
Sleep 1s

# Press Escape to dismiss help, then send an empty Enter — must not crash.
Escape
Sleep 1s
Enter
Sleep 2s

# Keyframe 3: prompt is back to the empty REPL state (no crash, no stuck input).
Screenshot specs/2519-korean-ime-enter-fix/scripts/smoke-keyframe-3-post-enter.png
Sleep 1s

# Exit cleanly.
Ctrl+C
Sleep 800ms
Ctrl+C
