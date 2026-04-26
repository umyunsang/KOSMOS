# T003 Manual Rehearsal Protocol — PromptInput.onSubmit Guard Identification

**Status**: active (pending user manual rehearsal — `feedback_runtime_verification`)
**Spec**: 1978
**Why this exists**: PTY harness silently fails inside the Claude Code Bash sandbox (Bun + PTY + Ink import-time native compatibility issue, see `docs/spec-1978/B1-root-cause-trace.md`). The user's interactive Terminal/iTerm shell DOES boot the TUI to the banner correctly. Identification of which `onSubmit` guard swallows Enter therefore shifts to the user's own environment — `feedback_runtime_verification` accepts terminal capture as evidence.

## Why we did NOT set up a full ink-testing-library wrapper

User selected option 2 ("ink-testing-library + T003 retry"). On inspection, `tui/src/components/PromptInput/PromptInput.tsx` exposes ~50 props plus a Zustand store dependency, theme provider, useStdin context, and IME state — full mount inside `ink-testing-library` requires a wrapper that mocks every collaborator. That work is real test-infrastructure scope, not a single-task patch. We therefore:

1. Added per-guard `logForDebugging(...)` traces inside `onSubmit` (T003 instrumentation) so the user's interactive rehearsal pins down the exact guard.
2. Marked full `ink-testing-library`-driven `PromptInput` integration tests as **Phase 7 work** (after T076 PTY scenarios) — the wrapper deserves its own test bed, not an inline T003 patch.

This preserves user direction (option 2 = avoid PTY harness; ink-testing-library is the long-term path) while unblocking T003 today.

## Procedure (user runs in interactive Terminal/iTerm)

```bash
cd ~/KOSMOS/tui      # NOT ~/KOSMOS — the `tui` script lives in tui/package.json,
                     # there is no root-level package.json. bun cannot resolve
                     # `bun run tui` from the repo root.

# Tail the structured DEBUG log in a SECOND terminal pane:
#   tail -f /tmp/kosmos-tui.log

# In the FIRST pane, launch with stderr split:
KOSMOS_TUI_LOG_LEVEL=DEBUG bun run tui 2> /tmp/kosmos-tui.log
```

Expected timeline:

1. Banner renders (`KOSMOS v… · K-EXAONE 236B …`).
2. Type any message in Korean (e.g., `안녕`).
3. Press Enter.

Three possible outcomes:

| Stderr line in `/tmp/kosmos-tui.log` | Diagnosis |
|---|---|
| `[onSubmit] enter input="안녕"` then `[onSubmit] guard:footerSelection swallow ...` | Footer pill (e.g., `↑ Opus now defaults to 1M context …`) is selected. Press `Esc` first. Patch target: prevent stale footer pill from auto-selecting on boot. |
| `[onSubmit] enter ...` then `[onSubmit] guard:viewSelectionMode=selecting-agent swallow` | A `/agents` modal is half-open. `Esc` recovers. Patch: ensure boot path leaves `viewSelectionMode='none'`. |
| `[onSubmit] enter ...` then `[onSubmit] guard:empty-input swallow` | Input was cleared before submit (typically a paste/IME race). Patch: guard the input buffer. |
| `[onSubmit] enter ...` then `[onSubmit] guard:suggestions-showing swallow (count=N)` | Slash-command dropdown intercepts. Press `Esc` to close, retry. Patch: suggestion dismissal on plain prose. |
| `[onSubmit] enter ...` then `[onSubmit] route:onSubmitProp (normal leader)` then nothing | onSubmit routed correctly — failure is downstream (LLMClient stream / IPC frame send). Investigate `bridge.ts` send path. |
| **No `[onSubmit] enter` line at all** | The Enter keystroke never reached `onSubmit`. Cause is upstream — likely the `BaseTextInput`'s `useInput` callback is suppressed or the `keybindingContext` is `null`. Check the `keybindings:contextNull` log emitted in line 1645–1653 of PromptInput.tsx. |

## Reporting back

Paste the relevant `/tmp/kosmos-tui.log` lines (the block immediately around the Enter keystroke — usually 5–15 lines) into a comment on Epic [#1978](https://github.com/umyunsang/KOSMOS/issues/1978) or share with the implementing agent. We will land T004 (the actual patch) based on which guard fired.

## Cleanup after T004 lands

The `logForDebugging('[onSubmit] …')` traces added under T003 are diagnostic — drop them in the T004 commit so production logs stay quiet. Keep the `[onSubmit] guard:suggestions-showing` log (it predates T003; it was already there for slash-command UX debugging).
