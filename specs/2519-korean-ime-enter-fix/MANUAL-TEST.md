# PR #2519 — manual interactive test (Korean IME Enter)

**Why this exists**: the Korean IME composition false-positive that triggers
`isPasting=true` cannot be simulated by `expect`, `script`, or `vhs`. The
swallow regression is observable only when a real Hangul IME flushes Jamo
composition through the terminal. Layer 2 (`smoke-2519-boot.expect`) and
Layer 3 (`smoke-2519.tape`) cover the ASCII path; this document covers the
keystroke flow that the fix actually targets.

## Setup

```bash
cd ~/KOSMOS/tui
git checkout fix/2519-korean-ime-enter-swallow
bun install
bun run tui
```

Confirm KOSMOS branding, UFO mascot, and `tool_registry: 14 entries verified
(4 primitives)` in the boot banner.

## Required scenarios (all must pass before merge)

### S1 — Hangul + Enter (the fix's target)

1. Switch the OS input source to a Hangul IME (한글, 2-set / 3-set / Sebeolsik —
   any layout that triggers Jamo composition).
2. Type `안녕` and press **Enter**.
3. Observe: the message must dispatch to the assistant, the input must clear,
   and the assistant streaming spinner must appear.
4. Pre-fix behavior (`fa57212^`): Enter is swallowed when isPasting=true; the
   prompt freezes with `안녕` still in the buffer.
5. Post-fix behavior (`fa57212`): Enter dispatches normally.

Repeat with mixed input: `동아대 위치 알려줘`, `오늘 부산 날씨 어때`,
`종합소득세 신고 해줘`.

### S2 — IME + bracketed paste interleave

1. Type `테스트 ` (with a trailing space).
2. Without pressing Enter, paste a multi-line ASCII block from clipboard
   (`hello\nworld`).
3. Press **Enter** immediately after the paste settles.
4. Observe: the paste text stays as a single paste-block; the user Enter must
   submit, not get absorbed by the paste timer.

### S3 — Empty Enter no-crash

1. Type nothing.
2. Press **Enter** five times in succession.
3. Observe: no crash, no scroll explosion, prompt stays on the empty REPL line.

### S4 — Slash command via Enter

1. Type `/help`.
2. Press **Enter**.
3. Observe: the four-group help banner renders (세션 · 권한 · 도구 · 저장).
4. Press **Esc** to dismiss.
5. Type `/agents` and Enter — agents overview must render.

### S5 — Tool dispatch round-trip (sanity)

Layer 4 covers tool dispatch separately, but this verifies the input path
end-to-end with the fix in place:

1. Type `부산 동아대 어딨어` and Enter.
2. Observe: assistant streams, `resolve_location` tool block appears with
   the rendered `query: ...` preview (the new `renderToolUseMessage`
   string), citizen-facing answer follows.

## Reporting

For each scenario, capture:

- ✅ / ❌ status
- A screenshot if anything differs from the expected behavior
- The exact keystroke sequence that produced the failure

Append findings to the PR #2519 conversation. Merge requires S1-S4 ✅;
S5 is preferred but may be deferred to follow-up if blocked by an
unrelated tool issue.
