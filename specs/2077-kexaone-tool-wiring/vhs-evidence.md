# VHS Evidence — Citizen-perspective Visual Capture

> Epic [#2077](https://github.com/umyunsang/KOSMOS/issues/2077) · 2026-04-27
> T024 deliverable per `quickstart.md § VHS GIF`. The VHS binary (`brew install vhs`) and the running TUI bridge are required for local capture; the templates are committed here for reproducibility.

## Step 5 — tool_use box paint

```
# /tmp/probe-step5.tape
Output "/tmp/probe-step5.gif"
Set Shell "bash"
Set FontSize 14
Set Width 1100
Set Height 700
Set Padding 16
Hide
Type "cd ~/KOSMOS/tui"; Enter; Sleep 200ms
Type "set -a; source ../.env; set +a"; Enter; Sleep 200ms
Type "export KOSMOS_FORCE_INTERACTIVE=1 OTEL_SDK_DISABLED=true"; Enter; Sleep 200ms
Type "clear"; Enter; Sleep 200ms
Show
Type "bun run tui"; Enter; Sleep 12s
Type "강남구 근처 24시간 응급실을 알려주세요."
Sleep 1s; Enter
Sleep 60s
Screenshot "/tmp/step5-final.png"
```

Run: `vhs /tmp/probe-step5.tape`

Expected visual sequence (operator must record):
1. Spinner "Querying…" or thinking channel paint (from fdfd3e9)
2. tool_use box appears (CC-style, separate UI component) with `🔧 lookup` + JSON args — NOT a SystemMessage progress line
3. tool_result envelope summary appears beneath the tool_use box (paired)
4. Final natural-language assistant message renders below within ≤ 30 s of Enter (SC-002)

## Step 7 — PermissionGauntletModal interactive grant

```
# /tmp/probe-step7.tape
Output "/tmp/probe-step7.gif"
Set Shell "bash"
Set FontSize 14
Set Width 1100
Set Height 700
Set Padding 16
Hide
Type "cd ~/KOSMOS/tui"; Enter; Sleep 200ms
Type "set -a; source ../.env; set +a"; Enter; Sleep 200ms
Type "export KOSMOS_FORCE_INTERACTIVE=1 OTEL_SDK_DISABLED=true"; Enter; Sleep 200ms
Type "clear"; Enter; Sleep 200ms
Show
Type "bun run tui"; Enter; Sleep 12s
Type "출생신고 서류를 정부24에 제출하고 싶어요."
Sleep 1s; Enter
Sleep 30s
Screenshot "/tmp/step7-modal.png"
Type "y"
Sleep 30s
Screenshot "/tmp/step7-final.png"
```

Run: `vhs /tmp/probe-step7.tape`

Expected visual sequence (operator must record):
1. Spinner + thinking
2. tool_use box for `submit` primitive
3. PermissionGauntletModal (full-width bordered panel) appears within ≤ 1 s of the agent's decision (SC-003)
4. Modal shows description_ko, risk_level=high, receipt_id
5. After "y" press: modal dismisses, tool_result appears, final answer renders

## Operator capture log

The operator must run both tapes locally and attach the GIFs in the PR description. Reference frame: `git rev-parse HEAD` at the time of capture so the GIFs are pinned to the exact commit demonstrating the behaviour.

Run record:

| Tape | Run date | GIF path | Notes |
|---|---|---|---|
| `/tmp/probe-step5.tape` | __________ | __________ | __________ |
| `/tmp/probe-step7.tape` | __________ | __________ | __________ |

## Static fallback (CI-stable)

Even without VHS capture, the same flow is exercised in:
- `tui/tests/ipc/handlers.test.ts` — 6 invariants for tool_call/tool_result CC stream-event projection (T013, all pass)
- `tui/tests/integration/permission-modal.test.ts` — 14 cases for the consent flow (T022, all pass)
- `tests/integration/test_agentic_loop.py` — 3 scenarios for the agentic loop closure (T014 + T017, all pass)

Total programmatic coverage of the visual flow: 23 tests across 3 files.
