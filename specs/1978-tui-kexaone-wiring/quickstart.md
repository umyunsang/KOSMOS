# Quickstart: PTY-driven scenario rehearsal for Epic #1978

**For**: reviewers, demo rehearsal, KSC 2026 stage prep
**Plan**: [plan.md](./plan.md)
**Date**: 2026-04-27

This quickstart proves all three citizen scenarios from spec.md (Story 1, 2, 3) end-to-end on a real terminal. Pure code-grep checks are insufficient per memory `feedback_runtime_verification` — every reviewer MUST execute these steps before approving the PR.

## Prerequisites

- macOS or Linux. Windows out of scope.
- `bun ≥ 1.2`, `uv ≥ 0.5`, `python ≥ 3.12` on PATH.
- `KOSMOS_FRIENDLI_TOKEN` exported (FriendliAI serverless token).
- `KOSMOS_DATA_GO_KR_API_KEY` exported (for tool turn — adapter live-mode).
- **Crucially**: `unset ANTHROPIC_API_KEY` and `unset ANTHROPIC_AUTH_TOKEN` to verify FR-004 (no Anthropic dependency).

## One-time setup

```bash
cd /Users/um-yunsang/KOSMOS-wiring          # the worktree where this Epic ships
uv sync
cd tui && bun install && cd ..
```

## Scenario 1 — Greeting (User Story 1, P1)

```bash
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN
python scripts/pty-scenario.py greeting --capture-out /tmp/kosmos-s1.log
```

**Expected**:
- TUI banner shows `KOSMOS v… · K-EXAONE 236B (LG AI · FriendliAI)`.
- The script types `안녕하세요` and presses Enter.
- Within **2 s**, the first `assistant_chunk` delta appears on screen.
- Within **10 s**, the full reply has streamed in and a fresh prompt is back.
- Exit code: 0.
- `/tmp/kosmos-s1.log` contains exactly zero matches for `anthropic.com`, `INVALID_API_KEY`, `verifyApiKey`.

**On failure**:
- Inspect `/tmp/kosmos-s1.stderr.log` (script captures `KOSMOS_TUI_LOG_LEVEL=DEBUG` separately). Look for last `chat_request` send vs `assistant_chunk` receive — the gap names the broken layer.
- Run `python scripts/probe-bridge.py greeting` to check whether the backend emits `assistant_chunk` when given a hand-rolled `ChatRequestFrame` directly. If it does, the regression is on the TUI side.

## Scenario 2 — Tool turn (User Story 2, P1)

```bash
python scripts/pty-scenario.py tool-emergency-room --capture-out /tmp/kosmos-s2.log
```

**Expected**:
- TUI types `응급실 알려줘` and Enter.
- Within **5 s**, an `assistant_chunk` text reasoning block appears.
- A visible tool-invocation event (the existing `Tool.ts` UI line) names the tool that ran (e.g., `nmc_emergency_search` or `lookup{mode:"search", query:"응급실"}`).
- Within **25 s**, a follow-up assistant message renders with at least one source attribution (e.g., `(국립중앙의료원 NMC)`).
- Exit code: 0.
- `/tmp/kosmos-s2.log` contains: ≥1 `tool_call` frame, ≥1 `tool_result` frame paired by `call_id`, terminal `assistant_chunk{done=True}`.

**On failure**:
- If `tool_call` frame is in the log but no `tool_result`: TUI tool dispatch is broken. Trace `mcp.ts` connection to `mcp_server.py` (Phase G).
- If no `tool_call` frame: backend `_handle_chat_request` is not forwarding `tools` to LLMClient.stream — Phase D regression.
- If text reasoning streams but the model never calls a tool: the system prompt or tool definitions in the `ChatRequestFrame.tools` are malformed — Phase C/D regression.

## Scenario 3 — Permission gauntlet (User Story 3, P2)

```bash
python scripts/pty-scenario.py permission-medical --capture-out /tmp/kosmos-s3.log
```

**Expected**:
- TUI types a query that the registry classifies as Layer 2+ (gauntlet step 4 or 5).
- A modal appears within **1 s** of the gauntlet trigger, showing:
  - Tool name + ministry + PII class
  - Three buttons: `[Y 한번만]`, `[A 세션 자동]`, `[N 거부]` (CC-fidelity colour: orange ⓶)
  - A `transaction_id` displayed
- Script automatically taps `Y` ("allow once").
- Tool runs; result renders.
- A consent receipt file appears at `~/.kosmos/memdir/user/consent/<receipt_id>.json` with `decision: "allow_once"`.
- Exit code: 0.

Then re-run with `--auto-deny`:

```bash
python scripts/pty-scenario.py permission-medical --auto-deny --capture-out /tmp/kosmos-s3-deny.log
```

**Expected**:
- Modal appears, script taps `N`.
- Backend records denial; tool does NOT execute.
- Model receives a synthetic tool result with `error_type="permission_denied"` and replies politely without the data.
- Exit code: 0.
- `/tmp/kosmos-s3-deny.log` shows `permission_response{decision:"deny"}` and a follow-up `assistant_chunk` stream that does NOT contain real adapter data.

## Regression battery

```bash
# Backend
uv run pytest -q tests/ipc/ tests/permissions/ tests/integration/

# TUI
cd tui && bun test && cd ..

# Anthropic residue zero
uv run pytest -q tests/ipc/test_anthropic_residue_zero.py
```

All green. If `test_anthropic_residue_zero.py` fails, Phase B is incomplete — find the offending import via the test's diagnostic output.

## Telemetry inspection (optional, recommended for stage rehearsal)

```bash
# In a second terminal, before running scenarios:
docker compose -f docker-compose.dev.yml up -d langfuse otel-collector

# Re-run scenarios. Then visit:
open http://localhost:3000/traces  # Langfuse local UI
```

You should see one `kosmos.session` root span per scenario, each containing `kosmos.turn` children, each containing `kosmos.frame.*` children matching the captured frame log. If any frame from the captured log is missing in Langfuse, the OTEL collector wiring (Spec 028) regressed.

## Demo rehearsal checklist (KSC 2026)

- [ ] Run all three scenarios fresh on the demo laptop, verify all `Expected` blocks pass.
- [ ] Record Scenario 2 with `asciinema rec` for backup.
- [ ] Verify `~/.kosmos/memdir/user/consent/` is empty after `rm -rf` to start clean.
- [ ] Verify `unset ANTHROPIC_API_KEY` is in the demo shell rc.
- [ ] Have `/tmp/kosmos-s2.log` open in a second pane to show frame trace live.
- [ ] Backup plan: if FriendliAI is down, switch to `KOSMOS_IPC_HANDLER=echo` for the greeting demo and skip tool turn — disclosed honestly to audience.

## Reviewer sign-off

After running this quickstart, paste the following block into the PR review comment:

```
Scenario 1 (greeting): PASS / FAIL
  first chunk: __ s
  full reply:  __ s
  anthropic hits in log: 0 / >0

Scenario 2 (tool):   PASS / FAIL
  tool_call frame seen:    yes / no
  tool_result paired:      yes / no
  source attribution seen: yes / no
  end-to-end:              __ s

Scenario 3 (permission): PASS / FAIL
  modal render: __ s
  receipt file written: yes / no
  deny path correctly suppresses tool: yes / no

bun test:    PASS / FAIL  (count)
uv run pytest: PASS / FAIL  (count)
```

This block is the human-readable form of memory `feedback_runtime_verification` — closure declarations on this Epic require it.
