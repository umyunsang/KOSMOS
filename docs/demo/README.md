# README Demo Pipeline

UMMAYA's README demo is generated with `t-rec` only, without VHS, asciinema,
agg, or a mock IPC backend.

The pipeline records a real `ummaya` terminal session. By default, the person
recording types the natural Korean scenario prompt into the live Ink TUI, then
the running product calls FriendliAI and the public API adapters through the normal
`chat_request` path. Tool calls are not scripted; the model chooses them from
the scenario.

Use separate task-shaped prompts rather than one tool-catalog prompt:

```text
퇴근하고 다대포해수욕장 산책 가도 괜찮을까? 지금 기온이랑 비 오는지만 빠르게 확인해줘.
동아대 승학캠퍼스에서 친구가 갑자기 아프면 지금 바로 연락할 응급실 어디가 가까워? 찾아진 곳만 이름, 주소, 전화번호로 알려줘.
다대1동에서 오늘 전화해볼 수 있는 내과가 있을까? 찾아진 곳만 주소랑 전화번호까지 알려줘.
```

These prompts show natural user requests, not a tool catalog pitch. In the
release path, public API credentials are operator-managed by the live adapter
gateway; the user only logs in to FriendliAI.

## Generate

Before recording, run `ummaya` once and complete `/login` if the FriendliAI
session is not already active. Do not export Kakao/data.go.kr keys for the
README demo.

```bash
npm run demo:readme
```

When the `ummaya` prompt appears, type one scenario and wait for the answer.
Use the terminal's normal clear-screen shortcut or command between scenarios if
you want a cleaner shot, then type the next scenario. After the final answer is
visible, type `/exit` and press Enter so `t-rec` can finish and write the
GIF/MP4.

Outputs:

- `assets/ummaya-demo.gif` - README-embedded animation
- `assets/ummaya-demo.txt` - plain terminal evidence from the same run
- `assets/ummaya-demo.mp4` - t-rec video when video capture succeeds

For Codex/operator-driven capture on macOS, use:

```bash
docs/demo/drive-readme-demo-gui.sh
```

That helper opens a visible Terminal, runs `npm run demo:readme`, then types
scenario prompts into the real TUI from outside the t-rec child process. Do not
put `expect`, nested PTY harnesses, or fake tool output inside the recorder.

## Toolchain

Install the recorder stack on macOS:

```bash
brew install t-rec gifsicle ffmpeg
```

`t-rec` must run from a macOS GUI terminal that it can identify and that has
Screen Recording permission. If automatic window detection fails, set
`UMMAYA_TREC_WIN_ID` to one of the IDs from `t-rec --ls-win`. On macOS the
script first tries to detect the frontmost Terminal/iTerm/Ghostty/WezTerm window
with CoreGraphics and passes that ID to `t-rec --win-id`; it still intentionally
fails instead of switching to another recorder when `t-rec` cannot capture the
target window.

If t-rec reports `Cannot determine the WindowId`, refresh the target id with
`t-rec --ls-win` and pass it through `UMMAYA_TREC_WIN_ID` or `WINDOWID`. If it
reports a CGDisplay/CGWindow screenshot error, keep t-rec as the recorder and fix
Screen Recording permission, terminal visibility, or the stale window id.
