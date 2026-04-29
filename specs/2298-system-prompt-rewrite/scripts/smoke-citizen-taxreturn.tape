Output specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn.gif

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 700
Set TypingSpeed 50ms

Type "bun run tui"
Enter
Sleep 4s

# Keyframe 1 — boot+branding
Screenshot specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-keyframe-1.png

Type "내 종합소득세 신고해줘"
Sleep 500ms

# Keyframe 2 — input-accepted (citizen prompt typed, just before Enter)
Screenshot specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-keyframe-2.png

Enter
Sleep 12s

# Keyframe 3 — receipt rendered
Screenshot specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-keyframe-3.png

# Cleanup
Ctrl+C
Ctrl+C
Sleep 500ms
