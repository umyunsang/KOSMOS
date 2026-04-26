---
description: "Task list for Epic #1978 — TUI ↔ K-EXAONE wiring + 5-primitive demo surface"
---

# Tasks: TUI ↔ K-EXAONE wiring closure (5-primitive demo surface)

**Input**: Design documents from `/specs/1978-tui-kexaone-wiring/`
**Prerequisites**: spec.md ✅, plan.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅
**Branch**: `feat/1978-tui-kexaone-wiring` (worktree at `/Users/um-yunsang/KOSMOS-wiring`)
**Initiative**: [#1631](https://github.com/umyunsang/KOSMOS/issues/1631) (reopened — premature closure correction). Sibling Epics: [#1979 Plugin DX TUI integration](https://github.com/umyunsang/KOSMOS/issues/1979), [#1980 Agent Swarm TUI integration](https://github.com/umyunsang/KOSMOS/issues/1980).

## Implementation methodology (mandatory — applies to every task)

**CC source migration pattern** (memory `feedback_cc_source_migration_pattern` + Constitution §I):

```
For every code-touching task:
  1. Locate construct in `.references/claude-code-sourcemap/restored-src/src/`
  2. Copy → adapt — services/api/* over stdio JSONL, tools/* over 5-primitive surface,
     net-new domain (PIPA, Korean tier, swarm) → KOSMOS-original with header
  3. Cite upstream path in task body
  4. Per-file `NOTICE` retains Anthropic attribution where lifted
```

Each task body below includes a `Ref:` or `KOSMOS-original (closest CC pattern: ...)` line. Tasks without one are constitution violations.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallel-safe (touches files no other concurrent task touches; no dependency on incomplete tasks)
- **[Story]**: User story this task advances — `[US1]` (lookup), `[US2]` (submit + permission), `[US3]` (verify), `[US4]` (subscribe). Foundational and Polish phases carry no story label.
- Every task cites concrete KOSMOS file paths AND the CC reference baseline.

## Phase → Task ID → User Story → Spec Coverage

| spec-kit Phase | plan.md Phase | Task IDs | User Story | FR / SC coverage |
|---|---|---|---|---|
| 1 — Setup | (worktree already provisioned) | none | — | — |
| 2 — Foundational | A — B1 root cause | T001–T004 | (blocks all) | FR-001 unblocks; B1 doc |
| 3 — User Story 1 (P1, lookup) | B — Anthropic residue elim | T005–T016 | US1 | FR-004, SC-004 |
| 4 — User Story 2 (P1, submit + permission) | C + D + F + G | T017–T060 | US2 | FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-013, FR-014, FR-015, FR-016, FR-017, SC-002, SC-006, SC-008 |
| 5 — User Story 3 (P2, verify) | F (extend) | T061–T067 | US3 | FR-005, FR-011, SC-003, SC-008 |
| 6 — User Story 4 (P3, subscribe — demo-time gated) | F (extend) | T068–T072 | US4 | FR-012, SC-008 |
| 7 — Polish & cross-cutting | H + cross-cutting | T073–T086 | (final E2E + telemetry + docs + SC-004 runtime evidence + KSC backup recording) | SC-001, SC-004, SC-005, SC-007, FR-018, FR-019, FR-020 |
| **Total** | | **86 tasks** | | ≤ 90 budget honoured (4 slots headroom) |

## Path Conventions

- Backend Python: `src/kosmos/...` and `tests/...` at repo root
- TUI TypeScript: `tui/src/...` and `tui/tests/...`
- E2E harness: `scripts/...`
- Diagnostics & rehearsal artefacts: `docs/spec-1978/...`
- CC reference: `.references/claude-code-sourcemap/restored-src/src/...`

---

## Phase 1: Setup (Shared Infrastructure)

*(Empty — worktree, branch, spec dir, agent context already provisioned during /speckit-specify and /speckit-plan.)*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish PTY-driven scenario harness and resolve the B1 input-suppression bug. Until this phase completes, no scenario from any user story can be verified end-to-end.

- [ ] T001 [P] Create PTY scenario harness skeleton at `scripts/pty-scenario.py` using stdlib `pty.fork`. Supports subcommands `greeting | lookup-emergency-room | submit-fine-pay | verify-gongdong | subscribe-cbs`, captures stdout (frames) and stderr (DEBUG log) separately. (Subcommand bodies land in Phase 7.)
       Ref: KOSMOS-original (closest CC pattern: `.references/claude-code-sourcemap/restored-src/src/utils/expect/` PTY testing patterns; CC has no scenario harness equivalent — KOSMOS needs one for `feedback_runtime_verification`)
       Acceptance: harness can spawn `bun run tui`, capture two streams, exit cleanly on SIGTERM. FR: testing infra for SC-001/002/003.
- [ ] T002 Patch `tui/src/ipc/bridge.ts:184-194 _log` helper so `KOSMOS_TUI_LOG_LEVEL=DEBUG` output goes ONLY to stderr, never to stdout (frame stream stays pure NDJSON).
       Ref: `.references/claude-code-sourcemap/restored-src/src/utils/log.ts` (CC `logForDebugging` pattern — stderr-only by convention)
       Action: copy CC stream-routing convention; KOSMOS deviation: KOSMOS uses NDJSON stdout for frames, so DEBUG MUST stay on stderr (CC has no IPC frame stream, both go to stdout). Deps: T001.
- [ ] T003 Run T001 harness against current main, capture exact `PromptInput.tsx` guard line that swallows Enter. Document findings in `docs/spec-1978/B1-root-cause-trace.md` with file:line evidence.
       Ref: `.references/claude-code-sourcemap/restored-src/src/components/PromptInput/PromptInput.tsx` (compare against KOSMOS port)
       Action: bisect onSubmit guards; identify divergence from CC behaviour. Deps: T001+T002.
- [ ] T004 Patch the identified guard in `tui/src/components/PromptInput/PromptInput.tsx` so Enter passes through to `onSubmit` end-to-end. Add a regression-guard comment citing the trace doc.
       Ref: `.references/claude-code-sourcemap/restored-src/src/components/PromptInput/PromptInput.tsx` (canonical onSubmit flow)
       Action: align KOSMOS guard with CC original — fidelity ≥ 99%. Deps: T003.

**Checkpoint**: After T004, the input pipeline reaches `bridge.send(...)` for every Enter.

---

## Phase 3: User Story 1 — Citizen finds public information through `lookup` (Priority P1) 🎯 MVP step 1

**Goal**: Eliminate Anthropic SDK residue so the lookup-primitive demo runs against K-EXAONE without any Anthropic call.

**Independent Test**: `python scripts/pty-scenario.py lookup-emergency-room`. First chunk visible < 2 s, full reply < 25 s, zero `anthropic.com` matches.

### Implementation for User Story 1

- [ ] T005 [P] [US1] Replace `verifyApiKey` runtime call in `tui/src/hooks/useApiKeyVerification.ts:3` with KOSMOS-aware stub returning `'valid'` when `KOSMOS_FRIENDLI_TOKEN` set.
       Ref: `.references/claude-code-sourcemap/restored-src/src/hooks/useApiKeyVerification.ts` (verification state-machine shape preserved)
       Action: keep the `VerificationStatus` enum + state machine identical; KOSMOS deviation: replace `verifyApiKey()` HTTPS call with env-var presence check, `getAnthropicApiKeyWithSource` → `getKosmosFriendliTokenWithSource`. file: `tui/src/hooks/useApiKeyVerification.ts`. Acceptance: FR-004.
- [ ] T006 [P] [US1] Replace `queryHaiku` call in `tui/src/utils/teleport.tsx:15` with `LLMClient.complete` adapter (same input/output shape).
       Ref: `.references/claude-code-sourcemap/restored-src/src/utils/teleport.tsx` (call signature)
       Action: copy file as-is; KOSMOS deviation: replace `queryHaiku(...)` import with `import { LLMClient } from '../ipc/llmClient.js'` + `new LLMClient({...}).complete({...})` adapter wrapping the same prompt+output expectation. file: `tui/src/utils/teleport.tsx`. Acceptance: FR-004.
- [ ] T007 [P] [US1] Replace `queryHaiku` call in `tui/src/commands/rename/generateSessionName.ts:1` with `LLMClient.complete` adapter.
       Ref: `.references/claude-code-sourcemap/restored-src/src/commands/rename/generateSessionName.ts`
       Action: copy file as-is; KOSMOS deviation: same as T006 (Haiku call → LLMClient.complete). file: `tui/src/commands/rename/generateSessionName.ts`. Acceptance: FR-004.
- [ ] T008 [P] [US1] Replace `queryWithModel` call in `tui/src/commands/insights.ts:17` with `LLMClient.complete` adapter.
       Ref: `.references/claude-code-sourcemap/restored-src/src/commands/insights.ts`
       Action: copy file as-is; KOSMOS deviation: `queryWithModel(...)` call swap; KOSMOS uses single fixed model so model-arg parameter dropped. file: `tui/src/commands/insights.ts`. Acceptance: FR-004.
- [ ] T009 [US1] Convert `tui/src/services/api/claude.ts` to type-only stub — preserve TypeScript type/interface re-exports referenced elsewhere.
       Ref: `.references/claude-code-sourcemap/restored-src/src/services/api/claude.ts` (canonical 3,419-line CC source — KOSMOS file is byte-identical today; this task carves out the type-only subset)
       Action: identify all named imports `from '.../services/api/claude'` across `tui/src/`, retain types only. Deps: T005, T006, T007, T008.
- [ ] T010 [US1] Collapse `tui/src/services/api/claude.ts` runtime body to ≤ 200 lines — every removed function reduced to `throw new Error('Anthropic SDK removed by Spec 1633/1978; use kosmos.ipc LLMClient')`.
       Ref: `.references/claude-code-sourcemap/restored-src/src/services/api/claude.ts` (3,419 lines — Constitution §I rewrite boundary terminus)
       Action: rewrite boundary applied per Constitution §I. file: `tui/src/services/api/claude.ts`. Acceptance: SC-004; `wc -l ≤ 200`. Deps: T009.
- [ ] T011 [P] [US1] Add `tui/tests/services/api/claude-stub.test.ts` asserting runtime calls to deleted exports throw the canonical error and type-only imports compile.
       Ref: KOSMOS-original (closest CC pattern: existing `tui/tests/services/api/claude.test.ts` patterns — replicate test fixture conventions)
       Acceptance: bun test green. file: `tui/tests/services/api/claude-stub.test.ts`.
- [ ] T012 [P] [US1] Add `tests/ipc/test_anthropic_residue_zero.py` — pytest grep ratchet asserting zero alive `from .*services/api/claude` imports outside the stub file or `// KOSMOS:` deletion comments. **Enforces invariant D5** (Anthropic SDK byte path unreachable in normal operation).
       Ref: KOSMOS-original (closest CC pattern: none — defence-in-depth regression guard for Constitution §I rewrite boundary)
       Acceptance: SC-004 (static); uv run pytest green; runs in CI. Pairs with T085 for runtime evidence. file: `tests/ipc/test_anthropic_residue_zero.py`.
- [ ] T013 [US1] Update existing `tui/tests/services/api/claude*.test.ts` to test the stub or delete tests no longer applicable.
       Ref: existing tests in `.references/.../tui/tests/services/api/` (where present); KOSMOS port preserves test naming
       Acceptance: bun test green. file: `tui/tests/services/api/`. Deps: T010.
- [ ] T014 [US1] Add `CHANGELOG.md` Unreleased entry: `fix(1978): T1 anthropic residue eliminated — claude.ts collapsed 3419→<200 lines, 4 callsites adapted to LLMClient`.
       Ref: KOSMOS-original (release-note convention from existing `CHANGELOG.md`)
       Acceptance: CHANGELOG entry present. file: `CHANGELOG.md`.
- [ ] T015 [P] [US1] Document residue elimination in `docs/spec-1978/anthropic-residue-elim-trace.md` — before/after file:line table, line-count delta.
       Ref: KOSMOS-original (closest CC pattern: none — KOSMOS deviation diagnostic)
       Acceptance: trace doc exists. file: `docs/spec-1978/anthropic-residue-elim-trace.md`.
- [ ] T016 [US1] Run `cd tui && bun test && cd ..` and `uv run pytest -q tests/ipc/test_anthropic_residue_zero.py`; capture results to `docs/spec-1978/phase-B-test-run.log`.
       Ref: KOSMOS-original (CI gate; no CC analog)
       Acceptance: both commands exit 0. Deps: T010, T011, T012, T013.

**Checkpoint**: After T016, US1 (lookup demo) becomes possible against K-EXAONE without Anthropic.

---

## Phase 4: User Story 2 — Citizen completes a write action through `submit` (Mock) with consent gauntlet (Priority P1) 🎯 MVP step 2

**Goal**: Activate `chat_request` + `tool_call` + `tool_result` + `permission_request` + `permission_response` frames, expose `submit` primitive to LLM, register Mock `fines_pay` adapter, integrate permission pipeline.

**Independent Test**: `python scripts/pty-scenario.py submit-fine-pay --auto-allow-once`. tool_call + permission_request + permission_response + receipt file all visible.

### Frame schema activation (Phase C — ADR-0001)

- [ ] T017 [US2] Add `ChatRequestFrame` Pydantic model to `src/kosmos/ipc/frame_schema.py` per `contracts/chat-request-frame.md`. **Enforces invariant D4** (tool message integrity — `name` and `tool_call_id` populated together when `role="tool"` via `model_validator`).
       Ref: `.references/claude-code-sourcemap/restored-src/src/entrypoints/agentSdkTypes.ts` (CC `SDKMessage` shape: messages/tools/system); `src/kosmos/ipc/frame_schema.py:194 UserInputFrame` (sibling arm in same union)
       Action: KOSMOS-original IPC arm; mirror CC SDKMessage field names (`messages`, `tools`, `system`) for impedance match with `tui/src/query/deps.ts:queryModelWithStreaming` adapter. file: `src/kosmos/ipc/frame_schema.py`.
- [ ] T018 [US2] Add `chat_request → {"tui"}` to `_ROLE_KIND_ALLOW_LIST`; do NOT add to `_TERMINAL_KINDS`.
       Ref: `src/kosmos/ipc/frame_schema.py:_ROLE_KIND_ALLOW_LIST` (KOSMOS-original — Spec 032 invariant E3)
       Action: extend allow-list. Deps: T017.
- [ ] T019 [US2] Add `ChatRequestFrame` to `IPCFrame` discriminated union; update exhaustiveness checks.
       Ref: `src/kosmos/ipc/frame_schema.py` (FrameUnion type alias — KOSMOS-original)
       Action: union extension. Deps: T017+T018.
- [ ] T020 [US2] Update `tui/src/ipc/schema/frame.schema.json` — add `chat_request` arm definition (lockstep with Pydantic).
       Ref: `tui/src/ipc/schema/frame.schema.json` (KOSMOS-original — Spec 032 published contract)
       Action: schema lockstep update; SHA-256 will change. Deps: T017.
- [ ] T021 [US2] Update `tui/src/ipc/frames.generated.ts` to include `ChatRequestFrame` discriminator arm.
       Ref: `tui/src/ipc/frames.generated.ts` (autogenerated — Spec 032)
       Action: regenerate via `bun run gen:ipc` or hand-edit. Deps: T020.
- [ ] T022 [P] [US2] Add `tests/ipc/test_chat_request_frame.py` — pydantic round-trip + each validation rule.
       Ref: existing `tests/ipc/test_*.py` patterns (Spec 032 KOSMOS-original)
       Acceptance: validation rules enforced. file: `tests/ipc/test_chat_request_frame.py`.
- [ ] T023 [P] [US2] Add `tui/tests/ipc/chat-request-frame.test.ts` — TS codec round-trip.
       Ref: existing `tui/tests/ipc/*.test.ts` patterns
       Acceptance: bun test passes. file: `tui/tests/ipc/chat-request-frame.test.ts`.
- [ ] T024 [US2] Update `kosmos.ipc.schema.hash` OTEL attribute computation in `src/kosmos/ipc/stdio.py` boot sequence.
       Ref: `src/kosmos/ipc/stdio.py` (Spec 032 FR-037 — KOSMOS-original observability hook)
       Action: re-hash schema bytes. Deps: T020.

### Backend tool wiring (Phase D — ADR-0005)

- [ ] T025 [US2] Replace `_handle_user_input_llm` with `_handle_chat_request` in `src/kosmos/ipc/stdio.py` — accepts `ChatRequestFrame`, forwards `messages, tools, system` to `LLMClient.stream`.
       Ref: `.references/claude-code-sourcemap/restored-src/src/services/api/claude.ts:752 queryModelWithStreaming` (signature + content_block_* event handling); `tui/src/query/deps.ts:queryModelWithStreaming` (KOSMOS adapter that this task mirrors on backend side)
       Action: copy CC streaming-event handling logic; KOSMOS deviation: yields IPC frames instead of CC StreamEvent objects. file: `src/kosmos/ipc/stdio.py`. Deps: T019, T024.
- [ ] T026 [US2] Add `pending_calls: dict[str, asyncio.Future[ToolResultFrame]]` registry per data-model.md D1 invariant.
       Ref: `.references/claude-code-sourcemap/restored-src/src/query.ts dispatch_tool_calls` (CC pending-call coordinator)
       Action: copy pattern; KOSMOS deviation: futures resolved by inbound IPC frame instead of in-process callback. file: `src/kosmos/ipc/stdio.py`. Deps: T025.
- [ ] T027 [US2] Implement K-EXAONE `function_call` → `ToolCallFrame` emit — accumulate `input_json_delta`, parse on `content_block_stop`.
       Ref: `tui/src/query/deps.ts` lines 96-145 (KOSMOS already has this exact accumulation logic on TUI side; backend mirrors it)
       Action: port the accumulation loop from TS to Python; emit IPC frame. file: `src/kosmos/ipc/stdio.py`. Deps: T026.
- [ ] T028 [US2] Implement `tool_result` frame consumer in `_dispatch_inbound_frame` — looks up `pending_calls[call_id]`, calls `future.set_result`.
       Ref: `.references/claude-code-sourcemap/restored-src/src/query.ts dispatch_tool_calls` continuation
       Action: KOSMOS deviation: future resolution by inbound frame consumer hook. file: `src/kosmos/ipc/stdio.py`. Deps: T026.
- [ ] T029 [US2] Implement message-history injection — append `{role:"tool", content, name, tool_call_id}` to local messages list, re-invoke `LLMClient.stream` (ReAct loop continuation per ADR-0005).
       Ref: `.references/claude-code-sourcemap/restored-src/src/query.ts` ReAct loop (CC's loop is verbatim adopted here)
       Action: copy ReAct iteration logic; KOSMOS deviation: messages array stays backend-local for one chat_request span. file: `src/kosmos/ipc/stdio.py`. Deps: T028.
- [ ] T030 [US2] Add `KOSMOS_TOOL_RESULT_TIMEOUT_SECONDS` env (default 120); gate outer `asyncio.gather` per `contracts/tool-bridge-protocol.md`.
       Ref: `.references/claude-code-sourcemap/restored-src/src/services/api/withRetry.ts` (CC timeout patterns)
       Action: copy timeout/retry semantics; KOSMOS deviation: synthetic `tool_result` injected on timeout. files: `src/kosmos/ipc/stdio.py` + `src/kosmos/llm/config.py`. Deps: T029.
- [ ] T031 [P] [US2] Update `tui/src/ipc/llmClient.ts` `LLMClient.stream` to send `ChatRequestFrame` instead of `UserInputFrame` when payload includes messages/tools/system.
       Ref: `.references/claude-code-sourcemap/restored-src/src/services/api/claude.ts` request body shape (mirrored on TUI side via `KosmosToolDefinition`)
       Action: outbound serialisation update; tool_call consumer at line 367 unchanged. file: `tui/src/ipc/llmClient.ts`. Deps: T020+T021.
- [ ] T032 [P] [US2] Update `tui/src/ipc/codec.ts` to add `ChatRequestFrame` writer hook + type guard.
       Ref: `tui/src/ipc/codec.ts` (KOSMOS-original — Spec 032)
       Action: extend codec. file: `tui/src/ipc/codec.ts`. Deps: T021.
- [ ] T033 [P] [US2] Backward compat: keep `_handle_user_input_llm` legacy path active treating `UserInputFrame` as `ChatRequestFrame{messages=[{role:"user",content:text}]}` for echo / smoke tests.
       Ref: existing legacy handler in `src/kosmos/ipc/stdio.py:461`
       Action: KOSMOS-original (defence-in-depth — no CC analog). file: `src/kosmos/ipc/stdio.py`. Deps: T025.
- [ ] T034 [P] [US2] Add `tests/ipc/test_chat_request_handler.py` — happy path no tools no permission.
       Ref: existing `tests/ipc/test_*.py` patterns
       Acceptance: assistant_chunk stream emitted with terminal `done=True`. file: `tests/ipc/test_chat_request_handler.py`.
- [ ] T035 [P] [US2] Add `tests/ipc/test_tool_call_emit.py` — tool_call frame emit on K-EXAONE function_call.
       Ref: pattern from `tui/src/query/deps.ts` test fixtures (mock stream events)
       Acceptance: ToolCallFrame fields match contract. file: `tests/ipc/test_tool_call_emit.py`.
- [ ] T036 [P] [US2] Add `tests/ipc/test_tool_result_consume.py` — tool_result resolution + history injection + restream.
       Acceptance: ReAct multi-turn invariant D1 holds. file: `tests/ipc/test_tool_result_consume.py`.
       Ref: KOSMOS-original (Spec 032 IPC test pattern)
- [ ] T037 [US2] Add OTEL `kosmos.turn` span emission in `_handle_chat_request` per ADR-0004.
       Ref: `.references/claude-code-sourcemap/restored-src/src/services/api/claude.ts` (CC's Anthropic-side span pattern); KOSMOS uses `opentelemetry-sdk` per Spec 021
       Action: open at frame receipt, close at terminal. file: `src/kosmos/ipc/stdio.py`. Deps: T025.
- [ ] T038 [US2] Add `tests/ipc/test_react_loop_invariants.py` — D1/D3/D6 invariants on synthetic two-tool turn.
       Ref: KOSMOS-original (data-model.md D-series invariants)
       Acceptance: integrity invariants enforced. file: `tests/ipc/test_react_loop_invariants.py`. Deps: T029.

### 5-primitive LLM expose (Phase D ext)

- [ ] T039 [US2] Expose `submit` primitive to LLM core surface — register Pydantic input/output schema in `src/kosmos/tools/mvp_surface.py` (or sibling) so it appears in `registry.export_core_tools_openai()`.
       Ref: `.references/claude-code-sourcemap/restored-src/src/Tool.ts` (Tool registration pattern); existing `src/kosmos/tools/mvp_surface.py:RESOLVE_LOCATION_TOOL`
       Action: copy mvp_surface.py registration template; KOSMOS deviation: 5 primitives are domain-agnostic envelopes (Spec 031). file: `src/kosmos/tools/mvp_surface.py`. Deps: T029.
- [ ] T040 [US2] Expose `verify` primitive to LLM core surface (same pattern as T039).
       Ref: `src/kosmos/primitives/verify.py:VerifyInput` (existing Spec 031 model)
       Action: extend `mvp_surface.py` with VERIFY_TOOL registration. file: `src/kosmos/tools/mvp_surface.py`. Deps: T039.
- [ ] T041 [US2] Expose `subscribe` primitive to LLM core surface.
       Ref: `src/kosmos/primitives/subscribe.py:SubscribeInput`
       Action: extend `mvp_surface.py` with SUBSCRIBE_TOOL. file: `src/kosmos/tools/mvp_surface.py`. Deps: T039.
- [ ] T042 [P] [US2] Add `tests/tools/test_mvp_surface_5primitive.py` — assert all 5 primitives exported by `registry.export_core_tools_openai()` after registration.
       Ref: existing `tests/tools/test_mvp_surface.py` patterns
       Acceptance: SC-008. file: `tests/tools/test_mvp_surface_5primitive.py`. Deps: T041.

### Backend permission wiring (Phase E — ADR-0002)

- [ ] T043 [US2] Import `PermissionPipeline` + `SessionContext` into `src/kosmos/ipc/stdio.py`; instantiate one pipeline + per-session context inside `_handle_chat_request` scope.
       Ref: `src/kosmos/permissions/pipeline.py:PermissionPipeline.evaluate` (existing Spec 033 — KOSMOS-original)
       Action: pipeline integration; mirror existing `kosmos` Rich REPL pattern in `src/kosmos/cli/app.py:236`. file: `src/kosmos/ipc/stdio.py`. Deps: T025.
- [ ] T044 [US2] Implement `_check_permission_via_bridge(tool, ctx)` per `contracts/permission-bridge-protocol.md`.
       Ref: `.references/claude-code-sourcemap/restored-src/src/hooks/useCanUseTool.ts` (CC sync-await permission gate); `src/kosmos/permissions/pipeline.py` (KOSMOS gauntlet)
       Action: KOSMOS-original — combine CC sync-wait with Spec 033 ASK branch. file: `src/kosmos/ipc/stdio.py`. Deps: T043.
- [ ] T045 [US2] Implement `permission_request` frame emit + `pending_perms` dict + `asyncio.wait_for(timeout=60)` per ADR-0002.
       Ref: T026 pending_calls pattern (sibling pattern, same file)
       Action: copy pending-future pattern; KOSMOS deviation: permission keyed by transaction_id. file: `src/kosmos/ipc/stdio.py`. Deps: T044.
- [ ] T046 [US2] Implement `permission_response` frame consumer in `_dispatch_inbound_frame`.
       Ref: T028 tool_result consumer pattern (mirror)
       Action: future resolution by transaction_id. file: `src/kosmos/ipc/stdio.py`. Deps: T045.
- [ ] T047 [US2] Implement default-deny on timeout per ADR-0002 (Constitution §II fail-closed). **Enforces invariant D2** (every `permission_request` resolved within 60 s OR synthetic deny generated).
       Ref: `.references/claude-code-sourcemap/restored-src/src/hooks/useCanUseTool.ts` timeout fallback (CC pattern); Constitution §II
       Action: KOSMOS deviation — default deny + audit synthetic frame. file: `src/kosmos/ipc/stdio.py`. Deps: T045.
- [ ] T048 [US2] Implement consent receipt write to `~/.kosmos/memdir/user/consent/<receipt_id>.json`.
       Ref: existing `src/kosmos/permissions/` consent store patterns (Spec 035 — KOSMOS-original)
       Action: append-only JSON write per data-model.md schema. files: `src/kosmos/ipc/stdio.py` + `src/kosmos/permissions/consent_store.py` (new if absent). Deps: T046.
- [ ] T049 [US2] Implement session-scoped grant memory — `allow_session` adds tool_id to `session_grants: set[str]`.
       Ref: `src/kosmos/permissions/models.py:SessionContext` (extend if needed)
       Action: KOSMOS deviation: session-bounded grant cache. files: `src/kosmos/ipc/stdio.py` + `src/kosmos/permissions/models.py`. Deps: T048.
- [ ] T050 [P] [US2] Update `tui/src/ipc/llmClient.ts` to handle inbound `permission_request` — invoke existing `showPermissionModal` from `tui/src/components/permissions/AskUserQuestionPermissionRequest/`.
       Ref: existing `tui/src/components/permissions/AskUserQuestionPermissionRequest/QuestionView.tsx` (CC-fidelity modal)
       Action: wire frame consumer to existing modal hook. file: `tui/src/ipc/llmClient.ts`. Deps: T031, T032.
- [ ] T051 [P] [US2] Add `tests/ipc/test_permission_bridge.py` — full handshake (ASK / ALLOW_ONCE / ALLOW_SESSION suppress / DENY / TIMEOUT).
       Acceptance: every contract branch covered. file: `tests/ipc/test_permission_bridge.py`.
       Ref: KOSMOS-original (Spec 033 contract test)
- [ ] T052 [US2] Add OTEL `kosmos.permission.*` and `kosmos.consent.receipt_id` attributes per ADR-0004 + Spec 033.
       Ref: `src/kosmos/observability/semconv.py` (extend existing constants)
       Action: KOSMOS-original semconv extension. files: `src/kosmos/ipc/stdio.py` + `src/kosmos/observability/semconv.py`. Deps: T037, T045.

### Mock adapter registration (Phase F — submit branch)

- [ ] T053 [US2] Create `src/kosmos/tools/mock/__init__.py:register_mock_adapters(registry, executor)` that wires every mock under `src/kosmos/tools/mock/` into the appropriate primitive dispatcher.
       Ref: `src/kosmos/tools/register_all.py` (existing Live adapter registration pattern)
       Action: KOSMOS deviation — Mock adapters bypass the GovAPITool registry, plug directly into primitive dispatchers (`submit._ADAPTER_REGISTRY`, etc.). file: `src/kosmos/tools/mock/__init__.py`. Deps: T039+T040+T041.
- [ ] T054 [US2] Register `mock_traffic_fine_pay_v1` from `src/kosmos/tools/mock/data_go_kr/fines_pay.py` into the `submit` primitive dispatcher.
       Ref: `src/kosmos/tools/mock/data_go_kr/fines_pay.py` (existing Mock — Spec 031 ship)
       Action: invoke its `REGISTRATION` object via `submit._ADAPTER_REGISTRY[tool_id] = ...` from T053's loader. file: `src/kosmos/tools/mock/data_go_kr/__init__.py`. Deps: T053.
- [ ] T055 [US2] Update `src/kosmos/tools/register_all.py` to call `register_mock_adapters(...)` after Live registrations.
       Ref: existing register_all.py flow
       Action: append Mock registration step. file: `src/kosmos/tools/register_all.py`. Deps: T053.

### MCP populate verification (Phase G — ADR-0003)

- [ ] T056 [P] [US2] Trace `mcpClients` populate site upward from `tui/src/Tool.ts:166`; document in `docs/spec-1978/G-mcp-populate-trace.md`.
       Ref: `.references/claude-code-sourcemap/restored-src/src/services/mcp/mcpClient.ts` (CC populate site pattern)
       Acceptance: site identified. file: `docs/spec-1978/G-mcp-populate-trace.md`.
- [ ] T057 [US2] Implement eager spawn of `kosmos.ipc.mcp_server` at TUI startup per ADR-0003 in `tui/src/ipc/bridgeSingleton.ts`.
       Ref: `.references/claude-code-sourcemap/restored-src/src/services/mcp/mcpClient.ts` (CC eager-spawn pattern)
       Action: copy CC spawn flow; KOSMOS deviation: spawns Python `mcp_server.py` instead of npm MCP servers. file: `tui/src/ipc/bridgeSingleton.ts`. Deps: T056.
- [ ] T058 [US2] Update `tui/src/Tool.ts` mcpClients consumer to fail fast if empty at first tool dispatch.
       Ref: existing Tool.ts:166 (no behaviour change beyond assertion)
       Acceptance: defence-in-depth. file: `tui/src/Tool.ts`. Deps: T057.
- [ ] T059 [P] [US2] Add `tui/tests/ipc/mcp-eager-spawn.test.ts`.
       Ref: KOSMOS-original (closest CC pattern: existing `tui/tests/services/mcp/` if present)
       Acceptance: spawn happens before mcpClients consumed. file: `tui/tests/ipc/mcp-eager-spawn.test.ts`.
- [ ] T060 [US2] Verify `tools/list` JSON-RPC reply on `kosmos.ipc.mcp_server` returns the registered primitive surface non-empty after T053-T055 register.
       Ref: `src/kosmos/ipc/mcp_server.py` (existing Spec 1634 — KOSMOS-original)
       Acceptance: N9 closed; tools/list non-empty. file: `src/kosmos/ipc/mcp_server.py`. Deps: T057+T055.

**Checkpoint**: After T060, US2 deliverable — submit Mock + permission gauntlet + ReAct loop + MCP active.

---

## Phase 5: User Story 3 — Citizen authenticates through `verify` (Mock 6-family) (Priority P2)

**Goal**: Register at least 2 verify-family Mock adapters so the discriminated-union shape is visible in citizen demo.

**Independent Test**: `python scripts/pty-scenario.py verify-gongdong`. AuthContext output shows `published_tier=gongdong_injeungseo_aal3` + `nist_aal_hint=AAL3`.

- [ ] T061 [US3] Register `verify_gongdong_injeungseo` Mock from `src/kosmos/tools/mock/verify_gongdong_injeungseo.py` into `verify` primitive dispatcher (via T053 loader).
       Ref: `src/kosmos/tools/mock/verify_gongdong_injeungseo.py` (existing Spec 031 ship)
       Action: extend T053 loader to walk `verify_*.py` mocks. file: `src/kosmos/tools/mock/__init__.py`. Deps: T053+T040.
- [ ] T062 [US3] Register `verify_digital_onepass` Mock from `src/kosmos/tools/mock/verify_digital_onepass.py`.
       Ref: `src/kosmos/tools/mock/verify_digital_onepass.py`
       Action: same as T061. file: `src/kosmos/tools/mock/__init__.py`. Deps: T061.
- [ ] T063 [P] [US3] Add `tests/primitives/test_verify_mock_registration.py` — assert at least 2 families registered + AuthContext shape per family.
       Ref: existing `tests/primitives/test_verify.py` patterns
       Acceptance: SC-003 + FR-011. file: `tests/primitives/test_verify_mock_registration.py`.
- [ ] T064 [P] [US3] Add `tui/tests/screens/REPL/verify-render.test.tsx` — assert AuthContext output renders both `published_tier` and `nist_aal_hint` in the conversation transcript.
       Ref: existing `tui/tests/screens/REPL/` snapshot patterns
       Acceptance: SC-003 visible to citizen. file: `tui/tests/screens/REPL/verify-render.test.tsx`.
- [ ] T065 [US3] Verify `verify` primitive's `family_hint` mismatch returns `VerifyMismatchError` per Spec 031 FR-010.
       Ref: `src/kosmos/primitives/verify.py:VerifyMismatchError` (existing)
       Action: integration test only — primitive code unchanged. file: `tests/primitives/test_verify_mismatch.py`. Deps: T061.
- [ ] T066 [US3] Add `tui/src/components/verify/AuthContextDisplay.tsx` (or extend existing) to render the discriminated-union output in citizen-readable form.
       Ref: `.references/claude-code-sourcemap/restored-src/src/components/` for any AuthContext-shaped component (likely none — KOSMOS-original); existing message renderer patterns
       Action: KOSMOS-original UI; closest CC pattern: `Message` renderer for tool_use blocks. file: `tui/src/components/verify/AuthContextDisplay.tsx`.
- [ ] T067 [US3] Add CHANGELOG entry: `feat(1978): verify Mock 2-family registration (gongdong_injeungseo + digital_onepass)`.
       Ref: KOSMOS-original
       file: `CHANGELOG.md`.

**Checkpoint**: After T067, US3 deliverable.

---

## Phase 6: User Story 4 — Citizen subscribes to disaster alerts (Priority P3 — demo-time gated)

**Goal**: Register Mock CBS subscribe adapter; surface streaming events in conversation flow.

**Independent Test**: `python scripts/pty-scenario.py subscribe-cbs`. Subscription handle visible; ≥ 1 simulated alert streams in 30 s.

- [ ] T068 [US4] Register `mock_cbs_disaster_msg` from `src/kosmos/tools/mock/cbs/` into `subscribe` primitive dispatcher.
       Ref: `src/kosmos/tools/mock/cbs/` (existing Spec 031 ship); `src/kosmos/primitives/subscribe.py:SubscriptionHandle`
       Action: extend T053 loader. file: `src/kosmos/tools/mock/__init__.py`. Deps: T053+T041.
- [ ] T069 [US4] Wire `SubscriptionHandle` lifetime — backend keeps the handle alive across multiple chat_request frames within the same session, streams CBS events as `assistant_chunk` frames or via a new lightweight notification path.
       Ref: `src/kosmos/primitives/subscribe.py:SubscriptionHandle` lifetime model (existing Spec 031)
       Action: KOSMOS-original — bridge primitive lifetime to IPC stream. file: `src/kosmos/ipc/stdio.py`. Deps: T068+T029.
- [ ] T070 [P] [US4] Add `tests/primitives/test_subscribe_cbs_mock.py` — handle issuance + at least 1 alert event in stream.
       Ref: existing `tests/primitives/test_subscribe.py` patterns
       Acceptance: FR-012. file: `tests/primitives/test_subscribe_cbs_mock.py`.
- [ ] T071 [P] [US4] Add `tui/tests/screens/REPL/subscribe-stream-render.test.tsx` — long-running stream renders alongside prompt.
       Ref: existing TUI streaming render patterns
       Acceptance: subscribe demo visible. file: `tui/tests/screens/REPL/subscribe-stream-render.test.tsx`.
- [ ] T072 [US4] Verify `/quit` cleanly closes subscription — no orphan process.
       Ref: existing TUI lifecycle hooks
       Acceptance: clean shutdown. files: `src/kosmos/ipc/stdio.py` + `tui/src/main.tsx`. Deps: T069.

**Checkpoint**: After T072, US4 deliverable (demo-time gated; may be Deferred).

---

## Phase 7: Polish & Cross-Cutting Concerns

### E2E scenario harness completion (Phase H)

- [ ] T073 Implement `scripts/pty-scenario.py greeting` subcommand body — sends `안녕하세요`, captures latencies.
       Ref: KOSMOS-original (T001 harness skeleton extension)
       Acceptance: SC-001. file: `scripts/pty-scenario.py`. Deps: T001+T004+T010+T025+T031.
- [ ] T074 Implement `scripts/pty-scenario.py lookup-emergency-room` subcommand body — sends `응급실 알려줘` AND `강남구 응급실` (covers US1 Acceptance #1 and #2; the second exercises the `resolve_location` → `lookup` chain explicitly). Closes analyze finding C3.
       Acceptance: SC-001 + lookup primitive + resolve_location chain both observable in captured frame log. file: `scripts/pty-scenario.py`. Deps: T073.
- [ ] T075 Implement `scripts/pty-scenario.py submit-fine-pay` subcommand body — `--auto-allow-once|--auto-allow-session|--auto-deny` flags.
       Acceptance: SC-002. file: `scripts/pty-scenario.py`. Deps: T073+T054+T048.
- [ ] T076 Implement `scripts/pty-scenario.py verify-gongdong` subcommand body.
       Acceptance: SC-003. file: `scripts/pty-scenario.py`. Deps: T073+T061.
- [ ] T077 Implement `scripts/pty-scenario.py subscribe-cbs` subcommand body (demo-time gated).
       Acceptance: SC-008 (if not Deferred). file: `scripts/pty-scenario.py`. Deps: T073+T068.
- [ ] T078 [P] Add `tests/e2e/test_tui_pty_scenarios.py` — pytest wrapper for all PTY scenarios, gated `@pytest.mark.e2e`.
       Acceptance: full pipeline reproducible. file: `tests/e2e/test_tui_pty_scenarios.py`.
- [ ] T079 [P] Add `scripts/probe-bridge.py` — hand-rolled `ChatRequestFrame` direct send.
       Ref: KOSMOS-original (quickstart.md "On failure" tooling)
       Acceptance: dev tooling. file: `scripts/probe-bridge.py`.
- [ ] T080 Run `quickstart.md` procedure end-to-end on a real terminal; capture to `docs/spec-1978/rehearsal-2026-NN-NN.log`; populate reviewer sign-off.
       Acceptance: SC-007. Deps: T073-T077.

### Telemetry + cross-cutting

- [ ] T081 [P] Implement `kosmos.session` root span in `src/kosmos/ipc/stdio.py` per ADR-0004; close at `session_event{event=exit}`.
       Ref: existing OTEL setup in `src/kosmos/observability/` (Spec 021)
       Action: span hierarchy completion. file: `src/kosmos/ipc/stdio.py`. Deps: T037.
- [ ] T082 [P] Update `docs/api/schemas/` to re-export `ChatRequestFrame` for the docs catalog.
       Ref: `scripts/build_schemas.py` (Spec 1637)
       Action: regenerate via build_schemas. file: `docs/api/schemas/`. Deps: T017.
- [ ] T083 [P] Update `docs/ipc-protocol.md` + `docs/requirements/kosmos-migration-tree.md` to mark P3 closure superseded by Epic #1978.
       Ref: existing docs
       file: `docs/ipc-protocol.md`, `docs/requirements/kosmos-migration-tree.md`.
- [ ] T084 Final integration run — full reviewer block from `quickstart.md`; verify every SC; draft integrated PR with `Closes #1978` + Copilot/Codex re-request.
       Ref: `AGENTS.md § Copilot Review Gate` + memory `feedback_copilot_rereview` + `feedback_codex_reviewer`
       Acceptance: PR ready, all 8 SC verifiable, all 20 FR traceable. Deps: ALL prior tasks.
- [ ] T085 Verify SC-004 measurable evidence — run `nettop -P -t wifi` (macOS) or `tcpdump -i any -n host anthropic.com` (Linux) during a 20-minute mixed conversation session; assert zero packets to `*.anthropic.com`; capture to `docs/spec-1978/anthropic-egress-zero-trace.md`. Closes analyze finding C1.
       Ref: KOSMOS-original (closest CC pattern: none — Constitution §I rewrite-boundary runtime evidence; complements static grep guard at T012)
       Acceptance: SC-004 verified with runtime evidence, not just static grep. file: `docs/spec-1978/anthropic-egress-zero-trace.md`. Deps: T010+T080.
- [ ] T086 Record `asciinema rec` of the three demo flows (lookup / submit / verify) for KSC 2026 backup; commit casts to `docs/spec-1978/asciinema/{greeting,lookup,submit,verify}.cast`. Closes analyze finding C2.
       Ref: KOSMOS-original (closest CC pattern: none — KSC stage backup asset)
       Acceptance: SC-007 backup demo asset exists; replayable by `asciinema play`. files: `docs/spec-1978/asciinema/`. Deps: T080.

---

## Dependencies & critical path

### Phase ordering (hard)

```
Phase 2 (T001-T004)  →  Phase 3 (T005-T016)  →  Phase 4 (T017-T060)
                                                       ↓
                                        Phase 5 (T061-T067 verify)  →  Phase 6 (T068-T072 subscribe — gated)
                                                                                      ↓
                                                                                Phase 7 (T073-T084 E2E + polish)
```

Phase 5 depends on T053 + T040 (loader + verify primitive expose). Phase 6 depends on T053 + T041 (loader + subscribe primitive expose).

### Critical path (longest dependency chain to T084)

```
T001 → T002 → T003 → T004 → T009 → T010 → T013 → T016
                              ↓
                              T017 → T018 → T019 → T024 → T025 → T026 → T027 → T028 → T029 → T030
                                                                                                   ↓
                                                                                                   T039 → T053 → T054 → T055
                                                                                                                            ↓
                                                                                                                            T043 → T044 → T045 → T046 → T047 → T048 → T049
                                                                                                                                                                          ↓
                                                                                                                                                                          T075 → T080 → T084
```

Critical path: ~26 tasks. Parallel rounds reduce wall-clock to ~22-24 sequential rounds with Agent Teams.

### Parallel-safe groupings (`[P]`)

35 tasks marked `[P]`. Examples:
- After T010: T011, T012, T015 (3 disjoint tests/docs)
- After T026: T031, T032, T034, T035, T036 (5 disjoint frame-side files)
- After T060: T056, T059, T063, T064, T070, T071, T078, T079, T081, T082, T083 (11 disjoint polish artefacts)

Convergence: `src/kosmos/ipc/stdio.py` (heaviest shared file). Tasks T024-T030, T033, T037, T043-T049, T052, T069, T081 — sequential.

## Implementation strategy

- **MVP scope** (T001-T060) = Phases 2+3+4 = lookup ✅ + submit ✅ + permission ✅ + 5 primitive surface ✅ + Mock fines_pay ✅ + MCP active ✅
- **Demo-ready scope** (T001-T080) = adds verify (Mock 2-family) + optional subscribe + PTY rehearsal complete
- **Ship-ready scope** (T001-T084) = all SC verified, telemetry complete, docs synced, PR drafted

Per `feedback_integrated_pr_only` — single PR at T084.

## Notes

- Sub-issue budget: 84 / 90. Headroom: 6 slots for `[Deferred]` placeholder issues + mid-cycle additions.
- Plugin DX TUI integration → tracked separately under [Epic #1979](https://github.com/umyunsang/KOSMOS/issues/1979).
- Agent Swarm TUI integration → tracked separately under [Epic #1980](https://github.com/umyunsang/KOSMOS/issues/1980).
- 7 Deferred Items in spec.md table — 2 already linked to issues (#1979 / #1980), 5 remain `NEEDS TRACKING` for `/speckit-taskstoissues`.
- All paths are absolute relative to `/Users/um-yunsang/KOSMOS-wiring/`.
- Every task body includes a `Ref:` line citing CC source path or a `KOSMOS-original (closest CC pattern: ...)` justification per `feedback_cc_source_migration_pattern`.
