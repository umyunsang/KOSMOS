# Spec 2293 Epic β — interactive /help slash command (visual companion).
# Generates specs/2293-ui-residue-cleanup/smoke-help.gif for human visual review.
# Companion of smoke-help-pty.txt (text log for LLM grep) and
# smoke-help.expect (reproducible interactive scenario).
# Run: vhs specs/2293-ui-residue-cleanup/scripts/smoke-help.tape

Output specs/2293-ui-residue-cleanup/smoke-help.gif
Set Shell "bash"
Set FontSize 14
Set FontFamily "JetBrains Mono"
Set Width 1200
Set Height 700
Set Theme "TokyoNightStorm"

Type "cd /Users/um-yunsang/KOSMOS-w-2293/tui && KOSMOS_BACKEND_CMD='sleep 60' bun run tui"
Enter
Sleep 5s

Type "/help"
Sleep 4s

Ctrl+C
Sleep 1s
Ctrl+C
Sleep 800ms
