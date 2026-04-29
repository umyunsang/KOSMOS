# Spec 2293 Epic β — KOSMOS TUI boot smoke (visual)
# Generates specs/2293-ui-residue-cleanup/smoke.gif for human visual review.
# Companion of smoke-pty.txt (text log for LLM grep).
# Run: vhs specs/2293-ui-residue-cleanup/scripts/smoke.tape

Output specs/2293-ui-residue-cleanup/smoke.gif
Set Shell "bash"
Set FontSize 14
Set Width 1100
Set Height 600
Set Theme "Dracula"

Type "cd /Users/um-yunsang/KOSMOS-w-2293/tui && KOSMOS_BACKEND_CMD='sleep 60' bun run tui"
Enter
Sleep 4s
Ctrl+C
Sleep 800ms
