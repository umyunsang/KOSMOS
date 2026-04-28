# VHS tape — Epic #2152 P5 visual smoke (Layer 4 of docs/testing.md)
# This produces specs/2152-system-prompt-redesign/smoke.gif for human / Codex
# visual review. The deterministic SC-1 audit lives in smoke-stdio.sh
# (Layer 2). Memory `feedback_vhs_tui_smoke`: vhs is supplementary, the
# text logs are the source of truth.

Output specs/2152-system-prompt-redesign/smoke.gif

Set Width 1280
Set Height 720
Set FontSize 14
Set Theme "Dracula"
Set TypingSpeed 30ms
Set PlaybackSpeed 1.5

Hide
Type "cd ~/KOSMOS && set -a && source .env && set +a && cd tui"
Enter
Sleep 500ms
Show

Type "bun run tui"
Enter
Sleep 7s

Type "강남역 어디야?"
Sleep 500ms
Enter
Sleep 35s

Type "오늘 서울 날씨 알려줘"
Sleep 500ms
Enter
Sleep 35s

Type "근처 응급실 알려줘"
Sleep 500ms
Enter
Sleep 35s

Type "어린이 보호구역 사고 다발"
Sleep 500ms
Enter
Sleep 35s

Type "안녕"
Sleep 500ms
Enter
Sleep 15s

Ctrl+C
Sleep 1s
Ctrl+C
Sleep 2s
