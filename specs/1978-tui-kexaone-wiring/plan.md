# Implementation Plan: TUI ↔ K-EXAONE wiring closure (5-primitive demo surface)

**Branch**: `feat/1978-tui-kexaone-wiring` | **Date**: 2026-04-27 (revised same-day for scope expansion) | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/1978-tui-kexaone-wiring/spec.md`
**Epic**: [#1978](https://github.com/umyunsang/KOSMOS/issues/1978) (under Initiative #1631 — closed prematurely; this Epic addresses regressions)

## Summary

Close the wiring gap that prevents `bun run tui` (Ink TUI on Bun, ported from Claude Code 2.1.88) from completing an end-to-end conversational turn against FriendliAI K-EXAONE — and crucially, **expose all five main-surface primitives** (`lookup`, `resolve_location`, `submit`, `verify`, `subscribe`) to the model so the citizen demo exercises the harness's full identity, not just a single read-path. Mock adapters under `src/kosmos/tools/mock/...` (already authored — `data_go_kr/fines_pay.py`, `verify_*.py × 6 family`, `cbs/*`) gain registration sites in this Epic so the model can call them through the same envelope as Live adapters.

Empirically (PTY rehearsal 2026-04-27): user types Korean, presses Enter → 0 byte response in 25 s. Diagnostic isolates the failure across two adjacent specs whose closures were declared on code-grep alone:

- **Spec 1633** (Anthropic → FriendliAI migration) deleted call sites in 8 files but left `tui/src/services/api/claude.ts` (3,419 lines) intact and 4 live call sites still importing from it (verifyApiKey on every boot; queryHaiku for session-name + teleport; queryWithModel for insights slash command).
- **Spec 1634** (P3 tool system wiring) declared "13-tool surface closure + stdio mcp" but `git show 06740c0 --name-only` confirms zero changes to `src/kosmos/ipc/stdio.py`. The backend's `_handle_user_input_llm` is a single-pass `LLMClient.stream(messages, max_tokens=2048)` — no `tools` argument, no `tool_call` frame emit, no `tool_result` frame consumer, no permission-pipeline integration.

Result: of the 19 IPC frame arms defined in `tui/src/ipc/schema/frame.schema.json`, only 4 are alive (`assistant_chunk`, `error`, `session_event`, dev `[echo]`); 15 are schema-only — including `tool_call`, `tool_result`, `permission_request`, `permission_response`. The TUI's frame consumer side (`tui/src/ipc/llmClient.ts:367` for `tool_call`, `codec.ts:271` for `permission_request`, etc.) is **already wired** — it has been waiting for backend emit that never arrived.

This plan stays inside the project's narrow rewrite boundary (Constitution §I): backend wiring + `services/api/` stub-down. CC's `query.ts` / `Tool.ts` / `QueryEngine.ts` / `query/deps.ts` are NOT touched (≥90% fidelity preserved per `feedback_cc_tui_90_fidelity`). The fix is concentrated in `src/kosmos/ipc/stdio.py` (≈+250 lines), `src/kosmos/ipc/frame_schema.py` (1 new arm), `tui/src/ipc/schema/frame.schema.json` (lockstep), `tui/src/ipc/llmClient.ts` (frame send adapter), and stub-collapse of `tui/src/services/api/claude.ts` (3,419 → ~120 lines).

## Technical Context

**Language/Version**: Python 3.12+ (backend, existing baseline); TypeScript 5.6+ on Bun ≥ 1.2 (TUI, existing Spec 287 stack).

**Primary Dependencies** (all existing, **zero new runtime dependencies** per AGENTS.md hard rule):
- Backend: `httpx ≥ 0.27` (FriendliAI HTTP client), `pydantic ≥ 2.13` (frame_schema models + LLM tool I/O), `pydantic-settings ≥ 2.0` (env catalog), `opentelemetry-sdk` + `opentelemetry-semantic-conventions` (Spec 021 GenAI spans, extended with `kosmos.frame.kind` per Spec 032).
- TUI: existing Ink + React + `@anthropic-ai/sdk` (used only as type provider — runtime calls already gated; this Epic completes the gating). No new JS deps.

**Storage**: 
- Conversation history: in-memory per session inside `tui/src/query.ts` (CC fidelity); **canonical history lives on the TUI side**, not the backend (ADR-0001 below). Backend stdio bridge is stateless across the chat-request frame boundary.
- Consent receipts: `~/.kosmos/memdir/user/consent/` (existing memdir per Spec 027 + Spec 035).
- Session JSONL: `~/.kosmos/memdir/user/sessions/<session_id>.jsonl` (existing, unchanged).

**Testing**: 
- Python: `pytest` + `pytest-asyncio` (frame schema, stdio handler, permission integration). Live FriendliAI calls gated under `@pytest.mark.live` and skipped in CI.
- TypeScript: `bun test` (TUI integration, frame send, llmClient adapter).
- E2E: a new `scripts/pty-scenario.py` Python harness (stdlib `pty.fork`) drives `bun run tui` through three citizen scripts (greeting, tool, permission); CI gate parses captured stdout for required markers.

**Target Platform**: macOS + Linux (existing). Windows out of scope (spec.md Assumptions).

**Project Type**: Multi-process CLI app — Bun TUI process + Python harness subprocess linked by stdio NDJSON. (Spec 032 transport.)

**Performance Goals** (from spec.md SC-001/002/003/005):
- Keystroke-to-first-response-chunk **< 2 s p50**
- Greeting-turn end-to-end **< 10 s p100** (sample of 20)
- Tool-turn end-to-end **< 25 s p100** (sample of 10)
- Permission modal render **< 1 s p100** after gauntlet trigger
- 30-min mixed session **0 unhandled exceptions**

**Constraints**:
- **Zero new runtime deps** (AGENTS.md).
- ≥ **90% CC 2.1.88 visual fidelity** in TUI (memory `feedback_cc_tui_90_fidelity`).
- Backend rewrite boundary **`services/api/` only** (Constitution §I).
- Single integrated PR (memory `feedback_integrated_pr_only`).
- Sub-issue ≤ **90 tasks** per Epic (memory `feedback_subissue_100_cap`).
- IPC envelope (`session_id` / `correlation_id` / `frame_seq`) preserved per Spec 032.
- Pydantic v2 strict typing for every frame arm (Constitution §III).

**Scale/Scope**: One citizen, one TUI process, one harness subprocess. Multi-citizen / fleet / multi-tenant is not in this Epic.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
|---|---|
| **I. Reference-Driven Development** | ✅ Primary reference: `.references/claude-code-sourcemap/restored-src/src/{query.ts, Tool.ts, services/api/claude.ts, query/deps.ts}`. Phase 0 research walks these files. Layer mapping per constitution §I table: Query Engine ⇒ CC restored-src `query.ts` (TUI side); Tool System ⇒ CC `Tool.ts`; TUI ⇒ Ink + CC reconstructed; **Permission ⇒ CC permission model**, but stdio bridge integration is KOSMOS-original (no upstream analog — documented as deviation in research.md). |
| **II. Fail-Closed Security (NON-NEGOTIABLE)** | ✅ Permission pipeline keeps existing fail-closed defaults. New backend handler `_handle_chat_request` still routes every tool through `PermissionPipeline.evaluate()` per Spec 033 — bypass-immune steps unchanged. New `permission_request` frame is **opt-in** to the citizen, never auto-allow. |
| **III. Pydantic v2 Strict Typing (NON-NEGOTIABLE)** | ✅ The new `ChatRequestFrame` arm (ADR-0001) and reused `ToolCallFrame` / `ToolResultFrame` / `PermissionRequestFrame` / `PermissionResponseFrame` are all Pydantic v2 `BaseModel(frozen=True, extra="forbid")`. No `Any` type in any I/O surface. |
| **IV. Government API Compliance** | ✅ Demo scenario uses an existing adapter validated under Spec 1637-p6-docs-smoke (memory `reference_koroad_portal` for emergency / KOROAD coverage). No new adapters. No live `data.go.kr` calls in CI tests; PTY scenario harness uses fixture-backed mock when `KOSMOS_LIVE_API=0`. |
| **V. Policy Alignment** | ✅ Surfaces PIPA gauntlet (Principle 8/9 — citizen consent over single conversational window). `kosmos-migration-tree.md § L1-A/B/C` pillars unchanged; this Epic only completes their TUI binding. |
| **VI. Deferred Work Accountability** | ⚠️ 5 deferred items in spec.md table currently `NEEDS TRACKING`. Resolved at `/speckit-taskstoissues` step. No untracked free-text deferrals — verified by grep of spec.md for forbidden patterns ("separate epic", "future phase", "v2"). All matches sit inside the Deferred Items table. |

**Gate result**: ✅ PASS. No constitution violations; the one ⚠ on Principle VI is a procedural placeholder resolved by a later spec-kit step, not a violation.

**Complexity Tracking**: Empty — no constitutional violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/1978-tui-kexaone-wiring/
├── plan.md                          # This file
├── research.md                      # Phase 0 — reference walk + ADR pre-work
├── data-model.md                    # Phase 1 — frame arms, history shape, consent receipt
├── quickstart.md                    # Phase 1 — PTY rehearsal procedure for reviewers
├── spec.md                          # /speckit-specify output (149 lines)
├── checklists/
│   └── requirements.md              # spec quality gate (passed first iteration)
├── contracts/
│   ├── chat-request-frame.md        # ChatRequestFrame envelope + role/terminal allow-list
│   ├── tool-bridge-protocol.md      # tool_call / tool_result frame round-trip
│   └── permission-bridge-protocol.md # permission_request / permission_response handshake
└── tasks.md                         # /speckit-tasks output (NOT created here)
```

### Source Code (repository root)

This Epic does NOT introduce new top-level structure. All changes are concentrated within existing trees per Constitution §I rewrite boundary:

```text
src/kosmos/ipc/
├── frame_schema.py            ← +1 arm (ChatRequestFrame), +role/terminal allow-list entries
├── stdio.py                   ← _handle_user_input_llm replaced by _handle_chat_request
│                                  + tool_call emit + tool_result consumer + permission bridge
└── (existing demo/, tx_cache.py, ring_buffer.py, etc. unchanged)

src/kosmos/permissions/
└── pipeline.py                ← read-only (existing); stdio.py imports and calls

tui/src/services/api/
└── claude.ts                  ← collapsed 3419 → ~120 lines (stub: re-exports types,
                                  routes runtime calls to LLMClient/deps adapter)

tui/src/ipc/
├── llmClient.ts               ← LLMClient.stream() now serializes messages+tools+system
│                                  to ChatRequestFrame instead of UserInputFrame
├── codec.ts                   ← +ChatRequestFrame writer hook
└── schema/
    └── frame.schema.json      ← +ChatRequestFrame arm definition (lockstep with Pydantic)

tui/src/hooks/
└── useApiKeyVerification.ts   ← rewritten as KOSMOS-aware: returns 'valid' when
                                  KOSMOS_FRIENDLI_TOKEN present, never calls anthropic.com

tui/src/commands/
├── insights.ts                ← queryWithModel call → LLMClient.complete adapter
└── rename/generateSessionName.ts ← queryHaiku call → LLMClient.complete adapter

tui/src/utils/
└── teleport.tsx               ← queryHaiku call → LLMClient.complete adapter

scripts/
└── pty-scenario.py            ← NEW Python E2E harness (stdlib only)

tests/
├── ipc/test_chat_request_handler.py     ← Phase D unit tests
├── ipc/test_permission_bridge.py        ← Phase E unit tests
├── ipc/test_anthropic_residue_zero.py   ← Phase B regression guard (grep-based)
└── e2e/test_tui_pty_scenarios.py        ← Phase H scenario tests (citizen scripts)

tui/tests/
├── ipc/llm-client-frame.test.ts         ← TUI-side ChatRequestFrame send
└── services/api/claude-stub.test.ts     ← stub coverage
```

**Structure Decision**: KOSMOS-native multi-process layout (Backend Python + TUI TS over stdio NDJSON). Matches existing Spec 032 / 287 / 1633 / 1634 conventions. No new top-level directories.

## Implementation methodology — CC source migration pattern (mandatory)

Every task that touches code follows the **CC source migration pattern** (memory `feedback_cc_source_migration_pattern`):

```
1. Locate the corresponding construct in `.references/claude-code-sourcemap/restored-src/src/`
2. Copy the relevant function / module / type into the KOSMOS path
3. Adapt to the KOSMOS shape — applying the rewrite boundary (Constitution §I)
   - services/api/* → KOSMOS Python backend over stdio JSONL
   - tools/* → thin renderers over KOSMOS's 5-primitive surface
   - net-new domain layers (Korean IME, public-API adapters, PIPA permission, swarm mailbox) → KOSMOS-original with header `// KOSMOS-original — no upstream analog`
4. Cite the upstream path in the task body and (when copying file content) in the file header per Constitution §I
5. Per-layer NOTICE declares Anthropic attribution where lifted material remains
```

**Task body required format**:

```
- [ ] T0NN [P?] [USx] <action> in <KOSMOS path>
       Ref: .references/claude-code-sourcemap/restored-src/src/<file>:<lines>
       Action: copy → adapt — <KOSMOS deviation in 1 line>
       OR: KOSMOS-original (closest CC pattern: <reference>)
```

This pattern is **load-bearing for every Phase below**. Task bodies missing a Ref line (or a justified KOSMOS-original claim) will be flagged in `/speckit-analyze`. The pattern is what makes "≥ 90% CC fidelity" measurable rather than aspirational.

## Phase 0 — Outline & Research

Phase 0 produces `research.md`. Five research streams, each grounded in **CC 2.1.88 source map first** per Constitution §I:

### Research stream 1 — How CC's tool loop carries `tools[]` to the model

- Read `.references/claude-code-sourcemap/restored-src/src/services/api/claude.ts`: identify `queryModelWithStreaming` signature → confirm `tools: Tools` parameter shape (already done in 2026-04-27 PTY diagnostic, line 752).
- Read `.references/.../src/query.ts`: identify how `tools` reaches the API call site.
- Read `tui/src/query/deps.ts:queryModelWithStreaming` (the KOSMOS-1633 P2 stub adapter): confirm `KosmosToolDefinition[]` is already prepared, just not delivered across the IPC boundary.

### Research stream 2 — Frame envelope extension vs new arm (resolves ADR-0001)

- Read `tui/src/ipc/schema/frame.schema.json` (76 KB): inventory existing user_input arm shape.
- Read `src/kosmos/ipc/frame_schema.py` lines 109-200: confirm `_BaseFrame` is the right superclass; `_ROLE_KIND_ALLOW_LIST` and `_TERMINAL_KINDS` extension points.
- Decision criteria: backward compat (existing `user_input` consumers must keep working), discoverability (a new arm is more legible than a polymorphic `text|messages` field), audit trail (Spec 024 `ToolCallAuditRecord` references `correlation_id` + `transaction_id`, both already on `_BaseFrame`).

### Research stream 3 — Permission bridge handshake (resolves ADR-0002)

- Read `src/kosmos/permissions/pipeline.py:PermissionPipeline.evaluate()` signature.
- Read CC `.references/.../src/hooks/useCanUseTool.ts` for sync-vs-async guard pattern.
- Read existing `tui/src/components/permissions/AskUserQuestionPermissionRequest/QuestionView.tsx` for modal UX baseline.
- Decision: synchronous `await response_event` is required (Spec 033 constitutional guarantee — every tool dispatch must have a Decision before execution). Async fire-and-forget is rejected.

### Research stream 4 — mcp.ts ↔ mcp_server.py lifecycle (resolves ADR-0003 + N9)

- `git show 06740c0 -- tui/src/ipc/mcp.ts | head -300`: confirm protocol version, handshake sequence.
- Trace `tui/src/Tool.ts:166 mcpClients` populate site upward (search for write callers).
- Decision driver: cold-start budget 500 ms (`mcp.ts` COLD_BUDGET_MS constant) vs eager-spawn cost.

### Research stream 5 — Telemetry correlation (resolves ADR-0004)

- Read `kosmos.observability.semconv` GenAI attributes (Spec 021).
- Read Spec 028 OTEL collector config for `kosmos.frame.kind` attribute.
- Decision: span hierarchy is `kosmos.session > kosmos.turn > kosmos.frame{kind} > gen_ai.{request,response}`. Tool calls are children of `kosmos.turn`, parented by frame_seq order.

### Deferred Items validation (Constitution §VI gate)

- Spec.md "Scope Boundaries & Deferred Items" section: present (5 entries).
- Each entry has a Reason for Deferral, a Target Epic/Phase, and `NEEDS TRACKING`.
- Free-text scan across spec.md for forbidden patterns:
  - `"separate epic"` — present 2 times, **all inside the Deferred Items table** (legal use).
  - `"future phase"` — 0 hits.
  - `"v2"` — 0 hits.
  - `"future work"` — present 1 time as table heading.
  - `"deferred to"` — present 0 times outside the table.
- Result: **PASS**. All deferrals tracked; `NEEDS TRACKING` markers will be resolved at `/speckit-taskstoissues`.

## Phase 1 — Design & Contracts

### ADR-0001 — IPC carries `messages[] / tools[] / system` via a new `ChatRequestFrame` arm (not a `UserInputFrame` extension)

**Decision**: Introduce a new IPC frame arm `ChatRequestFrame` in `frame_schema.py` and lockstep in `frame.schema.json`. `UserInputFrame.text: str` stays as-is for existing consumers (echo handler, future plain-input scenarios).

**Rationale**:
1. **Discoverability**: a polymorphic `text | messages` shape on `UserInputFrame` would be a hidden discriminated union — readers of the schema cannot tell which variant a backend will receive.
2. **Schema evolution**: extending an existing arm couples old and new clients; old TUI versions parsing a `ChatRequestFrame`-shaped `UserInputFrame` would crash (`extra="forbid"` model config).
3. **Audit trail**: Spec 024 `ToolCallAuditRecord` already keys off `correlation_id` + `transaction_id` (both on `_BaseFrame`); adding `ChatRequestFrame` as a sibling preserves the audit path without scaffolding.
4. **Naming hygiene**: matches existing Anthropic-compatible call shape (`messages`, `tools`, `system`) the TUI's `LLMClient.stream()` already uses internally — zero impedance mismatch.

**Alternatives rejected**:
- Extend `UserInputFrame` with optional `messages`, `tools`, `system` fields — would violate `extra="forbid"` semantics, force every existing emit/consume site to branch on field presence, and lose the Pydantic discriminated-union type narrowing.
- Keep `_handle_user_input_llm` and stuff messages JSON-encoded into `text` — opaque to schema validators, blocks Spec 024 audit, breaks `frame.schema.json` SHA-256 contract (FR-037 of Spec 032).

**ADR file**: NONE required — this is a frame-arm addition, not a project-wide rule change. ADR-0001 is captured in this plan.md.

### ADR-0002 — Permission bridge is synchronous request/response (not fire-and-forget)

**Decision**: When the backend tool dispatcher hits a tool requiring permission gauntlet escalation, it emits `PermissionRequestFrame` and **synchronously awaits** the matching `PermissionResponseFrame` (correlated by `transaction_id`) before proceeding to tool execution. Default timeout: 60 s; on timeout, treat as `deny` and emit `tool_result` with `error_type="permission_timeout"`.

**Rationale**:
- Constitution §II (fail-closed) demands no tool dispatch without an explicit Decision. Async fire-and-forget would race the tool against the prompt.
- Spec 033 multi-step gauntlet contract requires deterministic decision recording — async ordering breaks the receipt chain.
- Existing TUI consent modal (`tui/src/components/permissions/AskUserQuestionPermissionRequest/`) is already a blocking UI; matching this on the backend simplifies the contract.

**Alternatives rejected**:
- Async with optimistic execution + rollback: violates fail-closed (some tool side effects are irreversible per `is_irreversible: True`).
- Pre-flight permission check before LLM call: cannot work — model decides which tool to call mid-stream; permission must be evaluated per call.

### ADR-0003 — `mcp.ts` is eager-spawned at TUI startup (not lazy on first tool call)

**Decision**: TUI `bun run tui` spawns `uv run python -m kosmos.ipc.mcp_server` once at startup (parallel to the main `kosmos --ipc stdio` bridge spawn) and reuses the connection for the session lifetime. Cold-start budget remains 500 ms per `mcp.ts:COLD_BUDGET_MS` but is paid during boot, not during the first tool turn.

**Rationale**:
- SC-002 demands tool-turn end-to-end < 25 s p100. Lazy spawn would add 500 ms to the first tool call's latency budget — visible regression.
- Spec 1634 `contracts/mcp-bridge.md § 2.2` recommends eager. Restated.
- Two parallel subprocesses (main bridge + MCP) share session ID via the existing handshake; no new process management code beyond what bridgeSingleton already does.

**Alternatives rejected**:
- Lazy spawn on first tool call: latency regression on SC-002.
- Single subprocess multiplexing both stdio bridge + MCP: contracted-out by Spec 1634; would re-litigate that spec.

### ADR-0004 — Span hierarchy: `kosmos.session > kosmos.turn > kosmos.frame{kind}` with `correlation_id` propagation

**Decision**: 
- `kosmos.session` span opens at `kosmos --ipc stdio` startup, closes at `session_event{event=exit}`.
- `kosmos.turn` span opens at each `ChatRequestFrame` receive, closes at the final `assistant_chunk{done=True}` (or terminal `error` / `tool_result{is_final=True}` chain).
- Per-frame spans (`kosmos.frame.tool_call`, `kosmos.frame.tool_result`, `kosmos.frame.permission_request`, `kosmos.frame.permission_response`) child of `kosmos.turn`, ordered by `frame_seq`.
- Existing GenAI spans (`gen_ai.client.operation` per Spec 021) become children of `kosmos.turn`.
- `correlation_id` (UUIDv7) is the trace-correlation key — emitted on every span attribute set (`kosmos.correlation_id`).

**Rationale**:
- FR-014 demands turn reconstructibility from telemetry alone. Three-tier hierarchy gives operators a single root to drill down from.
- Spec 028 OTEL collector already accepts `kosmos.frame.kind`. No collector config change needed.

**Alternatives rejected**:
- Flat span list: loses turn boundary, makes Langfuse view noisy.
- Span per IPC byte-frame: too granular, breaks the OTEL batch-processor 512-frame budget.

### ADR-0005 — Conversation history canonical lives on the TUI side; backend stdio bridge is stateless across `ChatRequestFrame`

**Decision**: The TUI's `tui/src/query.ts` (CC-fidelity) owns the canonical conversation history — `Messages[]` array threaded through every `ChatRequestFrame`. Backend `_handle_chat_request` reads the messages from the inbound frame, passes them to `LLMClient.stream()`, emits the streaming response, and **forgets**. No backend per-session message store.

**Rationale**:
- Constitution §I rewrite boundary: `services/api/` only. Putting backend in charge of history would mean a second canonical store, breaking the boundary.
- CC fidelity (memory `feedback_cc_tui_90_fidelity`): CC's design has TUI own history. Honour it.
- Crash recovery: TUI persists history to `~/.kosmos/memdir/user/sessions/<session_id>.jsonl` per existing Spec 027 — this is the only persistence path; backend has nothing to replay from.

**Alternatives rejected**:
- Dual canonical stores: synchronization bug magnet.
- Backend-canonical with TUI as cache: violates rewrite boundary, would require deleting `tui/src/query.ts` history machinery (≈400 lines of CC-fidelity code).

### Data model (data-model.md highlights — full file in Phase 1 output)

| Entity | Storage | Lifetime |
|---|---|---|
| **Citizen Session** | TUI memory + memdir JSONL | Process lifetime (until `/quit`) |
| **Conversation Turn** | TUI `query.ts` `Messages[]` | Session lifetime |
| **Tool Invocation Event** (`call_id` ULID) | Frame in transit | Until matching `tool_result` |
| **Tool Result Event** | Frame in transit | Until injected into next `ChatRequestFrame.messages` |
| **Consent Decision** | Permission pipeline + TUI store | Session (one-time) or revoked |
| **Consent Receipt** | `~/.kosmos/memdir/user/consent/<receipt_id>.json` | Until citizen revokes |
| **`ChatRequestFrame`** (NEW) | Frame in transit | One-shot, per turn |

### Contracts (`contracts/*.md` outline; full files generated in Phase 1)

1. **`contracts/chat-request-frame.md`** — `ChatRequestFrame` Pydantic shape, JSON Schema arm, role allow-list entry (`role="tui"`), terminal-kind status (NOT terminal, follow-up `assistant_chunk`/`tool_call` are children), backward-compat note.
2. **`contracts/tool-bridge-protocol.md`** — Round trip: backend emits `tool_call{call_id}` → TUI dispatches via existing `tui/src/Tool.ts` + `mcp.ts` → TUI emits `tool_result{call_id}` → backend injects `{role: "tool", content: <result>}` into `messages[]` for next LLM turn → loop.
3. **`contracts/permission-bridge-protocol.md`** — Synchronous handshake: backend emits `PermissionRequestFrame{transaction_id, primitive_kind, tool_id, gauntlet_step}` → TUI renders modal → TUI emits `PermissionResponseFrame{transaction_id, decision, scope}` within 60 s → backend records receipt → resumes tool dispatch.

### Quickstart (`quickstart.md` outline)

A reviewer's PTY rehearsal procedure:

1. From `KOSMOS-wiring` worktree: `unset ANTHROPIC_API_KEY`, `unset ANTHROPIC_AUTH_TOKEN` (defence in depth — verify FR-004 absence regression).
2. Set `KOSMOS_FRIENDLI_TOKEN` + `KOSMOS_DATA_GO_KR_API_KEY`.
3. `uv sync` + `cd tui && bun install`.
4. `python scripts/pty-scenario.py greeting` — expect first chunk < 2 s, full reply < 10 s.
5. `python scripts/pty-scenario.py tool-emergency-room` — expect tool_call frame visible, source attribution, < 25 s.
6. `python scripts/pty-scenario.py permission-medical` — expect modal, choose "deny", verify model receives denial.
7. `bun test && uv run pytest -q` — both green.
8. Inspect `/tmp/kosmos-tui.log` (KOSMOS_TUI_LOG_LEVEL=DEBUG) for `gen_ai.*` + `kosmos.frame.*` span lines.

### Agent context update

The `update-agent-context.sh claude` script appends new tech to `CLAUDE.md` "Active Technologies". For this Epic the appendable line is:

```
- 1978-tui-kexaone-wiring: ChatRequestFrame IPC arm + stdio bridge tool/permission wiring + tui/src/services/api/claude.ts stub-down. Zero new runtime deps. Constitution §I rewrite boundary preserved (services/api/ only).
```

Plan applies it manually (Bash branch-naming guard would otherwise block the script).

## Estimated Task Count for `/speckit-tasks` (revised post 5-primitive scope expansion)

| Phase | Estimated tasks | Notes |
|---|---:|---|
| **A** B1 root cause確定 | 4 | PTY harness, stderr split, PromptInput trace patch, root cause doc |
| **B** Anthropic residue elimination | 12 | 4 callsite migrations, claude.ts stub-down, 2 regression guards, 2 docs |
| **C** Frame schema (ChatRequestFrame) | 8 | Pydantic arm, JSON Schema arm, allow-list updates, contract doc, 2 unit tests, 1 codegen, 1 sha256 attribute update |
| **D** Backend primitive wiring | 17 | Replace handler (3), tools forwarding (2), tool_call emit (2), tool_result consumer (2), history inject (2), **+expose `submit` / `verify` / `subscribe` primitives to LLM core surface (3)**, 3 unit tests |
| **E** Backend permission wiring | 10 | Pipeline import (1), permission_request emit (2), permission_response consume (2), receipt issue (2), 3 unit tests |
| **F (NEW)** Mock adapter registration sites | 5 | `register_mock_adapters()` site (1), `mock_traffic_fine_pay_v1` registration (1), `verify_gongdong_injeungseo` Mock registration (1), `verify_digital_onepass` Mock registration (1), `mock_cbs_disaster_msg` subscribe Mock registration (1) |
| **G** mcpClients populate verification | 6 | Trace populate (1), eager-spawn wiring (2), bridge singleton update (1), 2 unit tests |
| **H** E2E + regression | 14 | PTY harness body (4 scenarios — greeting, lookup-emergency-room, submit-fine-pay, verify-gongdong, optionally subscribe-cbs), 4 scenario tests, bun test fixes (2), pytest fixes (2), demo recording prep (1), CHANGELOG entry (1) |
| **Cross-cutting** | 8 | Telemetry attributes (3), span hierarchy assertions (2), docs/api/schemas update (2), agent-context update (1) |
| **Total** | **84** | **≤90 budget — safe (6 slot headroom for [Deferred] placeholders)** |

Phase (Swarm IPC) deliberately excluded — captured as Deferred Item per spec.md.

**Note on Phase F renaming**: this Epic's plan originally reserved "Phase F" for Swarm wiring (deferred). The new "Mock adapter registration" phase reuses the F label since Swarm is no longer in this Epic's task graph — per `feedback_subissue_100_cap` discipline, no slot is wasted on a deferred-only label.

## Re-evaluated Constitution Check (post-Phase 1 design)

| Principle | Compliance after design |
|---|---|
| I. Reference-Driven Development | ✅ All ADRs cite CC restored-src as primary; KOSMOS-original deviations (stdio bridge integration) documented |
| II. Fail-Closed Security | ✅ ADR-0002 enforces synchronous gauntlet; default deny on timeout |
| III. Pydantic v2 Strict Typing | ✅ ADR-0001 adds Pydantic v2 frozen frame arm |
| IV. Government API Compliance | ✅ Demo uses existing 1637-validated adapter; no live data.go.kr in CI |
| V. Policy Alignment | ✅ Permission gauntlet activation is the Principle 8/9 surface |
| VI. Deferred Work Accountability | ⚠ → ✅ at `/speckit-taskstoissues` (NEEDS TRACKING resolution) |

**Final gate**: ✅ PASS. Proceed to `/speckit-tasks`.

## Complexity Tracking

Empty — no constitution violations to justify, no architectural deviations beyond the documented ADRs.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_ | _(none)_ | _(none)_ |
