---

description: "Task list for Epic #2077 K-EXAONE tool wiring (CC reference migration)"
---

# Tasks: K-EXAONE Tool Wiring (CC Reference Migration)

**Input**: Design documents from `/specs/2077-kexaone-tool-wiring/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ (5 files) ✓, quickstart.md ✓
**Epic**: [#2077](https://github.com/umyunsang/2077)
**Branch**: `2077-kexaone-tool-wiring`

**Tests**: Inline tests are required for every implementation step. Static gates (bun test + uv run pytest) MUST pass before each phase boundary; citizen-perspective verification (PTY E2E + VHS GIF per `quickstart.md`) is the human gate at each user-story checkpoint.

**Organization**: Tasks are grouped by user story so each story is independently completable and demoable.

## Format: `[ID] [P?] [Story] Description with file path`

- **[P]**: Different file from sibling tasks; can run in parallel
- **[Story]**: User story label (US1/US2/US3) for traceability
- File paths are absolute or repo-root relative

## Path Conventions

KOSMOS dual-layer (per `plan.md § Project Structure`):

- Backend Python: `src/kosmos/`, `tests/` at repo root
- TUI TypeScript: `tui/src/`, `tui/tests/`
- CC reference cp lives at `src/kosmos/llm/_cc_reference/`

---

## Phase 1: Setup

**Purpose**: Confirm baseline state. KOSMOS already has all required infrastructure (Bun + uv environments, CC `claude.ts` cp from `fdfd3e9`); the epic adds no new project structure.

- [X] T001 Pre-flight verification: confirm branch `2077-kexaone-tool-wiring` checked out; `.env` present with `KOSMOS_FRIENDLI_TOKEN`; baseline `cd tui && bun test` ≥ 928 pass / 0 fail; baseline `uv run pytest tests/llm tests/ipc` green; record counts in `specs/2077-kexaone-tool-wiring/baseline.txt` for regression budget.

---

## Phase 2: Foundational (Step 1 — CC Reference cp)

**Purpose**: Materialize the `_cc_reference/` migration source so every subsequent step can cite line-numbers in cp'd files. Constitution §I file-lift policy applies: each cp file MUST carry a research-use header citing upstream path + version `2.1.88`.

**⚠️ CRITICAL**: No US1/US2/US3 work begins until Phase 2 is complete.

- [X] T002 [P] cp five utils-layer files into `src/kosmos/llm/_cc_reference/` with research-use headers: `api.ts` (from `.references/claude-code-sourcemap/restored-src/src/utils/api.ts`, 718 LOC), `tools.ts` (from `.references/.../tools.ts`, 389 LOC), `prompts.ts` (from `.references/.../constants/prompts.ts`, 914 LOC), `messages.ts` (from `.references/.../utils/messages.ts`, 5512 LOC), `toolResultStorage.ts` (from `.references/.../utils/toolResultStorage.ts`, 1040 LOC). Each file's first two lines: `// SPDX-License-Identifier: Apache-2.0 (Anthropic upstream) — research-use mirror` + `// Source: <upstream path> (CC 2.1.88)`. Per Constitution §I + research § R-1.

- [X] T003 [P] cp four services/query-layer files into `src/kosmos/llm/_cc_reference/` with research-use headers: `query.ts` (from `.references/.../query.ts`, 1729 LOC), `toolOrchestration.ts` (from `.references/.../services/tools/toolOrchestration.ts`, 188 LOC), `toolExecution.ts` (from `.references/.../services/tools/toolExecution.ts`, 1745 LOC), `permissions.ts` (from `.references/.../utils/permissions/permissions.ts`, 1486 LOC). Same header convention as T002. Per Constitution §I + research § R-2/R-4/R-5/R-6.

- [X] T004 Write `src/kosmos/llm/_cc_reference/README.md` index linking each cp file to its KOSMOS migration step (Step 2-7) and to the relevant section of `specs/2077-kexaone-tool-wiring/research.md`. Include the R-1 verification snippet for `zod/v4`'s `z.toJSONSchema()`. Depends on T002 + T003.

**Checkpoint**: `_cc_reference/` carries all 13 cp files (4 from `fdfd3e9` + 9 new from this epic). Reference citations in subsequent tasks resolve.

---

## Phase 3: User Story 1 — Citizen receives accurate answer (Priority: P1) 🎯 MVP

**Goal**: A citizen prompt that requires a public-service lookup (e.g., "강남구 24시간 응급실") completes end-to-end — the agent invokes a registered KOSMOS tool, receives a result envelope, and emits a final natural-language answer that incorporates the result. Zero hallucinated CC training-data tools (Read/Glob/Bash/etc).

**Independent Test** (citizen-perspective): Run `vhs /tmp/probe-step5.tape` (per `quickstart.md`) with a 강남구 응급실 prompt; observe within 30 s a tool_use box → tool_result envelope → final assistant message; run SC-001 50-prompt regression and confirm zero `<tool_call>{"name":"Read|Bash|..."}` matches.

**Maps to handoff steps**: 2 (TUI tool serialization) + 3 (system prompt inject) + 4 (registry fallback) + 5 (tool_use projection) + 6 (tool_result projection).

### Implementation for US1

- [X] T005 [P] [US1] Implement `tui/src/query/toolSerialization.ts` exporting `toolToFunctionSchema(tool)` and `getToolDefinitionsForFrame()` per `contracts/tool-serialization.md`. Use `import { z } from 'zod/v4'` and call `z.toJSONSchema(tool.inputSchema)` for the parameters field. Include the `isPublishedToLLM` filter restricting output to the 5 primitives + MVP-7 auxiliary tools (excludes Read/Bash/Glob/etc per Migration Tree § L1-C.C6). Output is alphabetically sorted by `function.name`. Mirrors `_cc_reference/api.ts:toolToAPISchema()` (line 119-266).

- [X] T006 [P] [US1] Add `tui/tests/tools/serialization.test.ts` covering all 7 invariants from `contracts/tool-serialization.md`: (1) primitive emits `$schema: 'https://json-schema.org/draft/2020-12/schema'` + `anyOf` for discriminated unions, (2) `.describe()` strings preserved, (3) optional fields excluded from `required`, (4) `getToolDefinitionsForFrame()` returns ≥ 5 entries, (5) alphabetic sort, (6) excludes Read/Bash/Glob, (7) deterministic across two calls. Run `cd tui && bun test tests/tools/serialization.test.ts` and confirm pass.

- [X] T007 [US1] Wire `tools: await getToolDefinitionsForFrame()` into the `ChatRequestFrame` literal at `tui/src/query/deps.ts:73-81` per `contracts/chat-request-frame.md`. Import from `./toolSerialization.js`. Per `data-model.md § 1` lifecycle: emit per turn, no caching. Depends on T005.

- [X] T008 [P] [US1] Implement `src/kosmos/llm/system_prompt_builder.py` exporting `build_system_prompt_with_tools(base, tools)` per `contracts/system-prompt-builder.md`. Use `json.dumps(parameters, indent=2, sort_keys=True, ensure_ascii=False)` for byte-stable output. Return `base` unchanged when `tools` is empty. Mirrors `_cc_reference/api.ts:appendSystemContext()` + `_cc_reference/prompts.ts` dynamic composition (research § R-3).

- [X] T009 [P] [US1] Add `tests/llm/test_system_prompt_builder.py` covering 7 invariants from `contracts/system-prompt-builder.md`: (1) empty tools returns base unchanged byte-for-byte, (2) single tool appends section, (3) byte-stable for same input, (4) Korean description preserved, (5) `sort_keys=True` invariant, (6) caller order preserved (no internal sort), (7) no timestamp/env leakage. Run `uv run pytest tests/llm/test_system_prompt_builder.py -v` and confirm pass.

- [X] T010 [US1] In `src/kosmos/ipc/stdio.py`: (a) add module-level `_TOOL_REGISTRY` cache populated lazily by `_ensure_tool_registry()` at first `_handle_chat_request` call; (b) inside `_handle_chat_request` after `frame.tools` unpack at line 1099-1101, add `if not llm_tools: llm_tools = _ensure_tool_registry().export_core_tools_openai()` (Step 4 fallback per `contracts/chat-request-frame.md`); (c) call `build_system_prompt_with_tools(base_system, llm_tools)` and use as the system message text (Step 3 inject); (d) migrate hardcoded primitive whitelist at lines 627-679 (`_PERMISSION_GATED_PRIMITIVES`) and per-fname dispatch at lines 890-939 to pull from a `kosmos.primitives.PRIMITIVE_REGISTRY` constant (FR-003 single-source-of-truth). Depends on T008.

- [X] T011 [US1] Update `tests/ipc/test_stdio.py` with five new scenarios: (a) `test_chat_request_with_empty_tools_uses_registry_fallback` — assert backend invokes LLM with non-empty `llm_tools` even when `frame.tools = []`; (b) `test_chat_request_appends_available_tools_section` — assert the LLM-bound system message ends with the dynamically composed `## Available tools` block; (c) `test_unknown_tool_in_frame_dropped_silently` — assert backend logs `kosmos.tool.unknown_in_frame` span event and proceeds with intersection; (d) `test_agentic_loop_max_turns_honored` — fixture LLM emits one tool_call per turn forever; assert loop terminates at `_AGENTIC_LOOP_MAX_TURNS` (FR-011); (e) `test_otel_spans_preserved` — capture OTEL spans across one tool call and assert all baseline attribute keys (`kosmos.tool.name`, `kosmos.tool.call_id`, `kosmos.permission.*`, `kosmos.session.*`) present at counts ≥ baseline (FR-019/SC-005). Depends on T010.

- [X] T012 [US1] In `tui/src/query/deps.ts`: replace the `else if (fa.kind === 'tool_call') { yield createSystemMessage(...) }` branch at line 237-242 with the CC stream-event projection from `contracts/stream-event-projection.md` (Step 5 — yield `content_block_start` + `content_block_stop` with `type: 'tool_use'`); replace the `else if (fa.kind === 'tool_result')` branch at line 243-249 with `createUserMessage([{ type: 'tool_result', tool_use_id, content: JSON.stringify(envelope), ... }])` (Step 6). Promote `blockIndex` to an explicit turn-scoped counter; introduce `pendingContentBlocks` array and merge into the terminal `createAssistantMessage` content array. Mirrors `_cc_reference/claude.ts:1995-2052` + `_cc_reference/messages.ts:ensureToolResultPairing()`. Depends on T007 (same file).

- [X] T013 [US1] Add cases to `tui/tests/ipc/handlers.test.ts` covering 6 invariants from `contracts/stream-event-projection.md`: (1) `tool_call` yields two stream events not SystemMessage, (2) content_block_start carries id/name/input from frame fields, (3) `tool_result` yields user-role tool_result content block, (4) `is_error: true` set when `envelope.kind === 'error'`, (5) multiple tool_calls produce sequential indices (1, 2, 3 with text at 0), (6) terminal AssistantMessage content array contains text + N tool_use blocks. Run `cd tui && bun test tests/ipc/handlers.test.ts` and confirm pass. Depends on T012.

- [X] T014 [US1] Add backend integration test `tests/integration/test_agentic_loop.py` (NEW file) that exercises the full multi-turn closure end-to-end against a fixture LLM endpoint: (a) citizen prompt → backend emits `tool_call` frame → tool result returned to LLM context → next turn produces final answer with no `<tool_call>{"name":"Read|Glob|Bash|..."}` matches (validates US1 acceptance scenarios 1, 3 + SC-001 + FR-010); (b) extended scenario — fixture LLM chains 5 sequential tool_calls (4-5 turn agentic conversation); assert all 5 calls complete within FriendliAI Tier 1 RPM budget with zero rate-limit-induced error frames on the citizen's screen (validates SC-004 + FR-012 retry/rate-limit preservation). Depends on T007 + T010 + T012.

**Checkpoint**: US1 MVP — citizen prompt yields end-to-end agentic loop with KOSMOS tools only. SC-001 (no hallucinations), SC-002 (≤30 s), SC-006 (zero new deps), SC-007 (≥95 % first-attempt success) verifiable.

---

## Phase 4: User Story 2 — Transparent transcript records (Priority: P2)

**Goal**: Every tool invocation and result appears as a permanent, audit-grade transcript record that survives session save/resume and surfaces orphans as visible errors.

**Independent Test**: Run a 5-tool-per-turn synthetic prompt and assert all 10 records (5 tool_use + 5 tool_result) exist in transcript and pair correctly. Save session, restart TUI, resume — assert all 10 records still present and pair.

**Maps to handoff steps**: Builds on Steps 5+6 from US1 — adds quality riders (persistence + orphan detection + multi-tool).

### Implementation for US2

- [X] T015 [P] [US2] Verify session save/resume preserves the new tool_use + tool_result content blocks. Inspect `tui/src/services/sessions/` JSONL serialization: confirm `AssistantMessage.content` array (containing text + tool_use blocks) and user-role tool_result messages round-trip cleanly. If serialization needs adjustment, update it. Add `tui/tests/store/sessionStore.test.ts` cases: (a) `tool_blocks_round_trip_save_resume` — 2-turn fixture session round-trips cleanly (FR-008 acceptance scenario 4); (b) `tool_blocks_round_trip_at_50_turn_scale` — synthetic 50-turn fixture (each turn has 1 tool_use + 1 tool_result) round-trips with 100% record retention (SC-008 scale invariant).

- [X] T016 [P] [US2] Add orphan detection in `tui/src/utils/messages.ts` (or wherever `handleMessageFromStream` finalizes the AssistantMessage): when a `tool_result` block arrives with `tool_use_id` that does not match any prior `tool_use` block in the transcript, emit an `ErrorEnvelope` (existing component, 113 LOC) marking the orphan with kind `'tool_result_orphan'`. Add `tui/tests/ipc/orphan.test.ts` validating orphan path. FR-009.

- [X] T017 [P] [US2] Add multi-tool-per-turn integration test in `tests/integration/test_agentic_loop.py` (extending T014's file): backend emits 3 tool_calls in one turn → 3 tool_results returned → all 3 paired correctly with sequential block indices 1, 2, 3 (text at 0) → next-turn LLM context includes all 3. US2 acceptance scenario 3.

**Checkpoint**: US2 — citizen sees a stable, auditable transcript across save/resume; orphans visible.

---

## Phase 5: User Story 3 — Interactive consent for irreversible actions (Priority: P2)

**Goal**: A citizen prompt triggering a gated primitive (e.g., 출생신고 서류 제출) opens an interactive consent prompt within 1 s; the citizen approves or denies; the tool runs only if approved.

**Independent Test**: Run `vhs /tmp/probe-step7.tape` with a submit-primitive-triggering prompt; observe within 1 s a `PermissionGauntletModal` with description/risk/receipt; press `y`; observe tool_result + final answer.

**Maps to handoff step**: 7 (PermissionGauntletModal wire).

### Implementation for US3

- [X] T018 [P] [US3] Extend `tui/src/store/sessionStore.ts` with `setPendingPermission(request)` (Promise-returning), `resolvePermissionDecision(request_id, decision)`, `getActivePermission()` selector, plus internal queue FIFO + 5-min timeout per `contracts/pending-permission-slot.md`. Read `KOSMOS_PERMISSION_TIMEOUT_SEC` (default 300) for timeout. Idempotent on duplicate `request_id`. Mirrors `_cc_reference/permissions.ts` flow.

- [X] T019 [P] [US3] Add `tui/tests/store/sessionStore.test.ts` (or extend existing) with 7 cases from `contracts/pending-permission-slot.md`: (1) stores active when slot empty, (2) queues when occupied, (3) resolve shifts queue, (4) Promise resolves with decision, (5) timeout → 'timeout', (6) duplicate → 'denied' immediately, (7) unknown id resolve is no-op. Run `cd tui && bun test tests/store/sessionStore.test.ts` and confirm pass.

- [X] T020 [US3] In `tui/src/query/deps.ts`: replace the auto-deny branch at line 250-266 with `const decision = await useSessionStore.getState().setPendingPermission({...})` followed by sending a `PermissionResponseFrame` with the resolved decision. Per `contracts/pending-permission-slot.md` caller pattern. Depends on T018.

- [X] T021 [US3] Update `PermissionGauntletModal` mount in `tui/src/screens/REPL.tsx:5275-5277` to subscribe to `useSessionStore(s => s.activePermission)`; render the modal only when active is non-null; wire `onGrant` and `onDeny` callbacks to `useSessionStore.getState().resolvePermissionDecision(active.request_id, 'granted'|'denied')`. Modal component itself unchanged (existing 100+ LOC component). Depends on T018.

- [X] T022 [US3] Add integration test `tui/tests/integration/permission-modal.test.ts` (NEW): render REPL with mocked backend; send `permission_request` frame for `submit` primitive; assert modal mounts with correct props (description_ko, risk_level=high, receipt_id) within 1 s (SC-003); simulate Y press; assert outbound `permission_response{decision: 'granted'}` frame; assert backend receives unblocking response; assert audit-ledger entry exists at `~/.kosmos/memdir/user/consent/` with matching `receipt_id` (FR-016 — consent receipt emission on grant). Depends on T020 + T021.

**Checkpoint**: US3 — interactive consent end-to-end. FR-013 through FR-018 + SC-003 verifiable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Lock in measurable success criteria, capture citizen-perspective evidence, and ship a regression-free PR.

- [X] T023 [P] Run SC-001 50-prompt hallucination regression via `/tmp/sc001-regression.py` (template in `quickstart.md § Test harnesses`); confirm all 50 prompts produce zero `<tool_call>{"name":"Read|Glob|Bash|Write|Edit|Grep|NotebookEdit|Task"}` matches; record per-prompt counts in `specs/2077-kexaone-tool-wiring/sc001-evidence.txt`.

- [X] T024 [P] Capture VHS GIFs per `quickstart.md` Steps 5/6/7: run `vhs /tmp/probe-step5.tape` (tool_use paint), capture additional inspection at `quickstart.md § Step 6` (tool_result + multi-turn), `vhs /tmp/probe-step7.tape` (consent flow). Commit GIFs to `docs/spec-2077-kexaone-tool-wiring/` so the PR can link them.

- [X] T025 [P] Verify SC-006 (zero new runtime deps): run `git diff main pyproject.toml tui/package.json tui/bun.lock | grep -E '^\+.*"\w+":'` and confirm no added dependency lines. Document the diff (or absence thereof) in `specs/2077-kexaone-tool-wiring/sc006-evidence.txt`.

- [X] T026 Full regression sweep — `cd tui && bun test` and `uv run pytest tests/`; both MUST be green at counts ≥ baseline from T001. Fix any drift before tagging the epic ready for PR. Per AGENTS.md hard rule (uv run pytest before every commit).

- [X] T027 Author PR description with citizen-perspective evidence: link to `sc001-evidence.txt`, embed the three VHS GIFs, summarize the contract coverage matrix (1 per `contracts/*.md`), include the 27-task completion checklist, declare the `Closes #2077` line (Epic only — never sub-issues per AGENTS.md PR closing rule). Final action: `gh pr create` with the body.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 has no deps; can start immediately.
- **Foundational (Phase 2)**: T002 + T003 [P] can run together; T004 depends on both. Phase 2 BLOCKS all user stories.
- **US1 (Phase 3)**: All US1 tasks depend on Phase 2 complete.
- **US2 (Phase 4)**: Depends on US1 (Phase 3) — US2 quality riders sit on top of US1 mechanism. T015/T016/T017 [P] within Phase 4.
- **US3 (Phase 5)**: Depends on Phase 2 complete only — independent of US1/US2 mechanically. Can run in parallel with US1 if staffed.
- **Polish (Phase 6)**: Depends on US1 + US2 + US3 all complete.

### User Story Dependencies

- **US1**: Phase 2 → T005-T014 (mostly parallel within US1).
- **US2**: US1 acceptance verified → T015/T016/T017 [P].
- **US3**: Phase 2 → T018-T022 (mostly parallel within US3).

### Within US1 (intra-phase order)

- T005 + T008 [P] (different files: TS + Python).
- T006 + T009 [P] (different test files).
- T007 depends on T005 (deps.ts needs `getToolDefinitionsForFrame`).
- T010 depends on T008 (stdio.py needs `build_system_prompt_with_tools`).
- T011 depends on T010 (test reflects backend impl).
- T012 depends on T007 (deps.ts edits same file as T007).
- T013 depends on T012 (test reflects deps.ts impl).
- T014 depends on T007 + T010 + T012 (full integration).

### Within US3 (intra-phase order)

- T018 + T019 [P] (different files: store + test).
- T020 depends on T018.
- T021 depends on T018.
- T022 depends on T020 + T021.

### Parallel Opportunities

| Group | Tasks | Rationale |
|---|---|---|
| Foundational cp | T002, T003 | Different files, identical verb |
| US1 implementation kickoff | T005, T006, T008, T009 | Different files (TS impl, TS test, Py impl, Py test) |
| US2 quality riders | T015, T016, T017 | Different files |
| US3 store + test | T018, T019 | Different files |
| Polish evidence | T023, T024, T025 | Different artifacts |

---

## Parallel Example: US1 Kickoff

After Phase 2 checkpoint, launch four tasks in one round:

```bash
# Agent A: implement TS tool serialization
Task: "T005 [P] [US1] Implement tui/src/query/toolSerialization.ts per contracts/tool-serialization.md"

# Agent B: implement Python system prompt builder
Task: "T008 [P] [US1] Implement src/kosmos/llm/system_prompt_builder.py per contracts/system-prompt-builder.md"

# Agent C: TS test scaffolding
Task: "T006 [P] [US1] Add tui/tests/tools/serialization.test.ts covering 7 invariants"

# Agent D: Python test scaffolding
Task: "T009 [P] [US1] Add tests/llm/test_system_prompt_builder.py covering 7 invariants"
```

Wiring tasks (T007 needs T005; T010 needs T008) follow once their primitives land.

---

## Implementation Strategy

### MVP First (US1 Only — Phases 1+2+3)

1. Complete Phase 1: T001 baseline.
2. Complete Phase 2: T002 + T003 + T004 (CC reference cp + index).
3. Complete Phase 3: T005-T014 (full agentic loop closure).
4. **STOP and VALIDATE**: SC-001 + SC-002 + SC-007 measured. Capture VHS GIF for citizen-prompt → tool_use box → tool_result envelope → final answer flow.
5. **Decision point**: ship MVP as-is (US2/US3 follow-up), or proceed to US3 (consent) since it's blocking submit-primitive demos.

### Incremental Delivery

1. Phase 1 + 2 + 3 → MVP rehearsal (Initiative #1631 unblocks #1979 plugin tools + #1980 swarm worker invocation pool).
2. Phase 4 (US2 polish) → Audit-grade transcript records for KSC 2026 narration.
3. Phase 5 (US3 consent) → Demonstrable submit-primitive end-to-end.
4. Phase 6 (Polish) → PR-ready package.

### Parallel Team Strategy

Lead (Opus) + 3 Sonnet teammates:

- **Round 1 (Phase 2)**: Teammate A → T002, Teammate B → T003. Lead reviews, drafts T004 (README index).
- **Round 2 (US1 kickoff)**: Teammate A → T005+T006, Teammate B → T008+T009, Teammate C → T012 (after T007 lands).
- **Round 3 (US1 wiring)**: Lead executes T007 + T010 + T011 (backend wiring + cross-file orchestration). Teammate C waits or starts T013.
- **Round 4 (US1 close + US3 kickoff in parallel)**: Teammate A → T014 (integration test). Teammates B, C → T018, T019 (US3 store).
- **Round 5 (US2 + US3 close)**: Teammate A → T015/T016/T017. Lead wires T020 + T021. Teammate B → T022.
- **Round 6 (Polish)**: All in parallel — T023, T024, T025; Lead consolidates T026, T027.

---

## Notes

- **Sub-issue budget**: 27 tasks ≤ 90 cap (well under 80 soft warning). Cohesion-merged 2 of 3 deps.ts edits into T012, 3 stdio.py edits into T010 to respect the same-file consolidation rule.
- **Cohesion merges applied**: T012 covers Steps 5+6 (both in deps.ts); T010 covers Steps 3+4+whitelist migration (all in stdio.py). T002+T003 split cp work along directory boundary for parallel execution.
- **Tests are inline** (not a separate phase) per AGENTS.md "uv run pytest before every commit" + KOSMOS implicit TDD discipline. Each implementation task names its companion test task.
- **Verify tests fail first** — when authoring T006/T009/T011/T013/T015/T016/T017/T019/T022, run them before the impl lands and confirm they fail; then implement and confirm pass. Skipped only for T002/T003 (mechanical cp).
- **Commit cadence**: one commit per task (or per cohesion-merged task body). Conventional Commits prefixes: `feat(llm)`, `feat(ipc)`, `feat(tui)`, `test(...)`, `docs(...)`.
- **Avoid**: cross-story dependencies that break US1's MVP independence (US3 must not silently require US2 polish; US2 must not silently require US3 modal).
- **PR closing rule**: PR body uses `Closes #2077` only — never sub-issue numbers. Sub-issues close after merge per `feedback_pr_closing_refs`.
- **Codex review gate**: after every push, read inline review comments from `chatgpt-codex-connector[bot]` per AGENTS.md § Code review. P1/P2/P3 severities resolved or replied-to before merge.
