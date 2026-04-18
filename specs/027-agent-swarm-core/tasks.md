# Tasks: Agent Swarm Core — Layer 4

**Input**: Design documents from `/Users/um-yunsang/KOSMOS-13/specs/027-agent-swarm-core/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (all present)
**Epic**: #13 — Agent Swarm Core
**Branch**: `feat/13-agent-swarm-core`

**Tests**: INCLUDED — spec mandates tests via FR-037, FR-038, FR-039, FR-040 and each user story declares an "Independent Test" acceptance path. Every integration test uses recorded fixtures from Epic #507 (no live `data.go.kr`).

**Organization**: Tasks are grouped by user story so each story can be implemented, reviewed, and merged independently. Five user stories: US1 (P1 parallel dispatch), US2 (P1 permission delegation), US3 (P2 cooperative cancellation), US4 (P2 crash resilience), US5 (P3 observability).

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (touches different files, no dependencies on incomplete tasks).
- **[Story]**: `[US1]`..`[US5]` — which user story the task serves. Setup / Foundational / Polish phases have no story label.
- Exact absolute file paths are given for every task.

## Path Conventions (per plan.md § Project Structure)

- Source: `/Users/um-yunsang/KOSMOS-13/src/kosmos/`
- Tests: `/Users/um-yunsang/KOSMOS-13/tests/agents/`
- Docs: `/Users/um-yunsang/KOSMOS-13/docs/`

All tasks target the single Python package layout (Option 1 from the template).

## Sizing (KOSMOS `size/{S,M,L}` convention)

- **size/S**: ≤ 100 LOC of source + tests, single file, ≤ 2 h effort.
- **size/M**: ≤ 300 LOC, 2–4 files, ≤ 6 h effort.
- **size/L**: ≤ 600 LOC, 5+ files, ≥ 1 day effort.

Each task carries one of these labels in square brackets after the file path.

## Layer label (per AGENTS.md § Issue hierarchy)

- `layer:agents` — everything under `src/kosmos/agents/`.
- `layer:observability` — `src/kosmos/observability/`.
- `layer:config` — `src/kosmos/settings.py` + `docs/configuration.md`.
- `layer:tests` — `tests/agents/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the empty package layout and test scaffolding. No business logic yet.

- [ ] T001 Create `src/kosmos/agents/` package with empty `__init__.py` and `src/kosmos/agents/mailbox/` sub-package with empty `__init__.py` at `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/__init__.py` and `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/mailbox/__init__.py`. [size/S] [layer:agents] [parallel-safe]
- [ ] T002 [P] Create `tests/agents/` test package with empty `__init__.py` at `/Users/um-yunsang/KOSMOS-13/tests/agents/__init__.py`. [size/S] [layer:tests] [parallel-safe]
- [ ] T003 [P] Create `tests/agents/conftest.py` at `/Users/um-yunsang/KOSMOS-13/tests/agents/conftest.py` with: (a) `tmp_mailbox_root` fixture (monkeypatch `KOSMOS_AGENT_MAILBOX_ROOT`), (b) `fixture_tape_llm` stub that replays scripted LLM responses from JSON files under `tests/agents/fixtures/`, (c) `build_test_registry()` helper that returns a `ToolRegistry` restricted to `{"lookup", "resolve_location"}` backed by `#507` recorded fixtures. [size/M] [layer:tests] [parallel-safe]
- [ ] T004 [P] Create `tests/agents/fixtures/` directory with placeholder `multi_ministry_query.json` (scripted 3-worker dispatch response) and `mailbox_crash_replay/pre_written_result.json` at `/Users/um-yunsang/KOSMOS-13/tests/agents/fixtures/multi_ministry_query.json` and `/Users/um-yunsang/KOSMOS-13/tests/agents/fixtures/mailbox_crash_replay/pre_written_result.json`. [size/S] [layer:tests] [parallel-safe]

**Checkpoint**: Package scaffold exists. `uv run pytest tests/agents/` collects zero tests, exits 0.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared models, exceptions, settings, and semconv constants consumed by EVERY user story. Must land before any story phase begins.

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T005 [P] Implement `AgentContext` frozen Pydantic v2 model at `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/context.py` per data-model.md §1 (fields: `session_id: UUID`, `specialist_role: str`, `coordinator_id: str="coordinator"`, `worker_id: str`, `tool_registry: ToolRegistry`, `llm_client: LLMClient`; `extra="forbid"`, `frozen=True`, `arbitrary_types_allowed=True`). FR-010. [size/S] [layer:agents] [parallel-safe]
- [ ] T006 [P] Implement agent exception hierarchy at `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/errors.py` per data-model.md §6: `AgentConfigurationError(ValueError)`, `AgentIsolationViolation(RuntimeError)`, `MailboxOverflowError(RuntimeError)`, `MailboxWriteError(IOError)`, `PermissionDeniedError(RuntimeError)`. Spec Edge Cases + FR-021 + FR-026. [size/S] [layer:agents] [parallel-safe]
- [ ] T007 [P] Implement `MessageType` `StrEnum` + 6 payload models (`TaskPayload`, `ResultPayload`, `ErrorPayload`, `PermissionRequestPayload`, `PermissionResponsePayload`, `CancelPayload`) + `AgentMessagePayload` `Annotated[... Field(discriminator="kind")]` closed union + `AgentMessage` model with `_msg_type_matches_payload_kind` model_validator at `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/mailbox/messages.py` per data-model.md §2. `ResultPayload.lookup_output` references the existing `LookupRecord | LookupCollection | LookupTimeseries` discriminated union from `src/kosmos/tools/models.py` (#507). All models `extra="forbid"`, `frozen=True`. NO `Any` anywhere. FR-016, FR-025, Constitution III. [size/M] [layer:agents] [parallel-safe]
- [ ] T008 [P] Implement `Mailbox` abstract base class at `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/mailbox/base.py` per data-model.md §4: abstract `async send(message) -> None`, abstract `async receive(recipient) -> AsyncIterator[AgentMessage]`, abstract `async replay_unread(recipient) -> AsyncIterator[AgentMessage]`. FR-014, FR-022. [size/S] [layer:agents] [parallel-safe]
- [ ] T009 [P] Implement `CoordinatorPlan`, `PlanStep`, `PlanStatus`, `ExecutionMode`, `StepStatus` Pydantic v2 models at `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/plan.py` per data-model.md §3 including the `_depends_on_indices_are_valid` model_validator (range check + no-self-reference). `extra="forbid"`, `frozen=True`. FR-005, SC-002. [size/S] [layer:agents] [parallel-safe]
- [ ] T010 [P] Implement `ConsentGateway` ABC + `AlwaysGrantConsentGateway` stub at `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/consent.py` per research.md D7 + C10: single async method `async def request_consent(self, tool_id: str, correlation_id: UUID) -> bool`; stub returns `True` unconditionally. FR-027. [size/S] [layer:agents] [parallel-safe]
- [ ] T011 [P] Extend `src/kosmos/observability/semconv.py` at `/Users/um-yunsang/KOSMOS-13/src/kosmos/observability/semconv.py` with the 7 new `KOSMOS_AGENT_*` attribute constants listed in data-model.md §8 (table). Append only — do not modify existing constants. FR-031. [size/S] [layer:observability] [parallel-safe]
- [ ] T012 [P] Extend `KosmosSettings` in `/Users/um-yunsang/KOSMOS-13/src/kosmos/settings.py` with the 4 new `agent_*` fields from data-model.md §9: `agent_mailbox_root: Path`, `agent_mailbox_max_messages: int` (ge=100, le=10000, default=1000), `agent_max_workers: int` (ge=1, le=16, default=4), `agent_worker_timeout_seconds: int` (ge=10, le=600, default=120). Env prefix `KOSMOS_AGENT_*` via pydantic-settings convention. Validator: `agent_mailbox_root` MUST be an absolute path (reject relative). FR-032..FR-035. [size/S] [layer:config] [parallel-safe]
- [ ] T013 [US1] [P] Unit test for `AgentContext` frozen + extra="forbid" at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_context.py`: asserts rejection of unknown field, rejection of empty `specialist_role`, immutability after construction. [size/S] [layer:tests] [parallel-safe]
- [ ] T014 [P] Unit test for `AgentMessage` + payload discriminator at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_messages.py`: round-trip JSON serialize/parse for each of 6 payload kinds, reject `msg_type`/`payload.kind` mismatch via `_msg_type_matches_payload_kind`, reject `Any` (verified by schema inspection). [size/S] [layer:tests] [parallel-safe]
- [ ] T015 [P] Unit test for `CoordinatorPlan` validator at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_plan.py`: reject `depends_on` with out-of-range index, reject self-reference (`steps[i].depends_on == [i]`), accept empty `depends_on`. [size/S] [layer:tests] [parallel-safe]

**Checkpoint**: Foundation ready. All shared models and exceptions exist and are unit-tested. No coordinator / worker / file-mailbox yet. User story phases can now begin.

---

## Phase 3: User Story 1 — Parallel Research via Coordinator Dispatch (Priority: P1) — MVP

**Goal**: Coordinator recognises a multi-ministry query, spawns N parallel workers (each with isolated `AgentContext`), collects their `result` messages, and synthesises a `CoordinatorPlan` without calling tools during synthesis.

**Independent Test** (from spec): drive a scripted session with a stub LLM → assert exactly 3 `asyncio.Task` workers, all post `result` before synthesis, plan references every `correlation_id`, synthesis never calls `lookup`/`resolve_location`, zero live `data.go.kr` calls.

### Tests for User Story 1 (FR-037, FR-038 mandate these)

- [ ] T016 [P] [US1] Contract test validating `agent-message.schema.json` against every `AgentMessage` variant at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_agent_message_schema.py` (load schema, validate each of 6 payload kinds serialised from Pydantic). [size/S] [layer:tests] [parallel-safe]
- [ ] T017 [P] [US1] Contract test validating `coordinator-plan.schema.json` against synthesised `CoordinatorPlan` instances at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_coordinator_plan_schema.py`. [size/S] [layer:tests] [parallel-safe]
- [ ] T018 [US1] Integration test `tests/agents/test_coordinator_phases.py` at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_coordinator_phases.py`: end-to-end 3-worker dispatch → synthesis → CoordinatorPlan. Asserts (a) 3 workers spawned as `asyncio.Task`, (b) each has isolated `AgentContext` (no shared refs), (c) all post `result` before synthesis begins, (d) plan references every worker `correlation_id` (SC-002 zero-orphan-id), (e) execution_mode classification correct per scripted input. FR-001..FR-005, SC-001, SC-002. [size/M] [layer:tests]
- [ ] T019 [US1] Test `test_synthesis_tool_gate.py` at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_synthesis_tool_gate.py` asserting during synthesis phase the LLM call receives an EMPTY tool-definitions list (or omits the kwarg entirely) — verified by inspecting the mock LLM client's recorded call args. FR-004, FR-038. [size/S] [layer:tests] [parallel-safe]
- [ ] T020 [US1] Test for `role="solo"` backward compatibility at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_solo_role_compat.py`: instantiate coordinator with `role="solo"`, verify behaviour matches existing Phase 1 `QueryEngine` public contract (no worker spawn, single inline loop). FR-007, SC-007. [size/S] [layer:tests] [parallel-safe]
- [ ] T021 [US1] Test for `Worker` lifecycle at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_worker_lifecycle.py`: worker sees only `{"lookup", "resolve_location"}` in its tool registry, posts `result` on normal completion with `ResultPayload` carrying a `LookupRecord|LookupCollection|LookupTimeseries`, posts `error` on unrecoverable failure. FR-008..FR-013. [size/M] [layer:tests] [parallel-safe]

### Implementation for User Story 1

- [ ] T022 [US1] Implement `Worker` class at `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/worker.py` that wraps `QueryEngine` and delegates its inner loop to `src/kosmos/engine/query.py::_query_inner()` VERBATIM. Worker receives `AgentContext` at construction; its tool registry MUST be restricted to `{"lookup", "resolve_location"}` (assertion at `__init__`, raises `AgentConfigurationError` otherwise). On normal completion posts `result` message (`ResultPayload`); on unrecoverable failure posts `error` message (`ErrorPayload`). FR-008, FR-009, FR-010, FR-011, FR-012, FR-013. [size/M] [layer:agents]
- [ ] T023 [US1] Implement `Coordinator` class + 4-phase state machine at `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/coordinator.py`: phases `RESEARCH → SYNTHESIS → IMPLEMENTATION → VERIFICATION` per data-model.md §7.1. Public API: `Coordinator(session_id, llm_client, tool_registry, mailbox, consent_gateway)` + `async run(citizen_request: str) -> CoordinatorPlan`. Intent classification by coordinator LLM (no static keyword table per research.md non-goals). Synthesis phase calls LLM with EMPTY tool-definitions list. Implementation phase runs parallel steps via `asyncio.TaskGroup`, sequential steps in declared order. `role: Literal["solo", "coordinator", "specialist"]` variant; `solo` path unchanged from Phase 1. FR-001..FR-007. [size/L] [layer:agents]
- [ ] T024 [US1] Implement `Coordinator.spawn_worker()` helper in `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/coordinator.py` (same file as T023): asserts `AgentContext.tool_registry.tool_ids() == {"lookup", "resolve_location"}` BEFORE constructing the worker; raises `AgentConfigurationError` for any mismatch; generates `worker_id = f"worker-{role}-{uuid4()}"` per research.md C2; enforces `KOSMOS_AGENT_MAX_WORKERS` cap via `asyncio.Semaphore`. FR-002, FR-010, FR-011, FR-034, Edge Case "spawned with no specialist role". [size/S] [layer:agents]
- [ ] T025 [US1] Re-exports in `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/__init__.py`: `Coordinator`, `Worker`, `AgentContext`, `CoordinatorPlan`, `PlanStep`, `AgentMessage`, `ConsentGateway`, `AlwaysGrantConsentGateway` (after T022, T023, T024). Mailbox classes re-exported after Phase 4. [size/S] [layer:agents]

**Checkpoint**: US1 complete. A coordinator dispatches 3 parallel workers end-to-end against fixture tapes and produces a valid `CoordinatorPlan`. MVP delivered (can merge/demo here).

---

## Phase 4: User Story 2 — Permission Delegation Chain (Priority: P1)

**Goal**: A worker blocked by `LookupError(reason="auth_required")` sends `permission_request` to the coordinator, coordinator consults `ConsentGateway`, replies `permission_response`, worker retries. Permissions never flow laterally between workers.

**Independent Test** (from spec): stub `LookupError(reason="auth_required")` → assert exactly 1 `permission_request` to `"coordinator"`, no other worker sees it, after `permission_response` worker retries with same `correlation_id`, round-trip < 1 s on loopback.

### Tests for User Story 2

- [ ] T026 [P] [US2] Integration test at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_permission_delegation.py`: full round-trip worker → coordinator → stub consent gateway → coordinator → worker. Asserts (a) exactly one `permission_request` with `recipient="coordinator"`, (b) other worker mailboxes are NOT modified (lateral-flow isolation per FR-025), (c) `correlation_id` preserved across retry, (d) round-trip wall-clock < 1 s. FR-023, FR-024, FR-025, FR-027, SC-004. [size/M] [layer:tests] [parallel-safe]
- [ ] T027 [P] [US2] Test for permission denial path at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_permission_denied.py`: stub gateway returns `False` → coordinator emits `permission_response(granted=False)` → worker converts to `error` message AND does NOT retry the denied tool call. FR-026. [size/S] [layer:tests] [parallel-safe]

### Implementation for User Story 2

- [ ] T028 [US2] Implement permission handling in `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/worker.py` (edits T022): catch `LookupError(reason="auth_required")` inside the inner loop, emit `permission_request(tool_id=..., reason=...)` addressed to `"coordinator"` with same `correlation_id`, await matching `permission_response`, on granted retry once, on denied emit `error` and terminate. FR-023, FR-026. [size/M] [layer:agents]
- [ ] T029 [US2] Implement permission routing in `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/coordinator.py` (edits T023): on receiving `permission_request`, call `consent_gateway.request_consent(tool_id, correlation_id)`, emit `permission_response(granted=..., tool_id=...)` addressed to the original `sender` field. Mailbox routes by declared `recipient` — coordinator MUST NOT broadcast. FR-024, FR-025. [size/S] [layer:agents]

**Checkpoint**: US2 complete. Worker ↔ Coordinator ↔ ConsentGateway delegation loop operates with enforced vertical-only flow.

---

## Phase 5: User Story 3 — Cooperative Cancellation (Priority: P2)

**Goal**: `coordinator.cancel()` propagates `asyncio.CancelledError` to all in-flight workers within 500 ms. Mailbox state preserved for debugging; no cross-run replay.

**Independent Test** (from spec): spawn 3 workers → after start, before completion, call `coordinator.cancel()` → assert all 3 raise `CancelledError` within 500 ms, coordinator task completes cleanly, no uncaught exceptions, `cancel` message is last delivered.

### Tests for User Story 3

- [ ] T030 [US3] Integration test at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_cooperative_cancellation.py`: 3-worker scenario, mid-flight cancel, wall-clock assertion ≤ 500 ms using `time.monotonic()` (not `perf_counter`). Asserts `cancel` message is the last message in each worker mailbox queue. Partial-results edge case: if a worker already posted `result` before `cancel`, it is preserved. FR-006, SC-003, spec Edge Cases (partial results). [size/M] [layer:tests] [parallel-safe]
- [ ] T031 [P] [US3] Test for cross-run replay isolation at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_cancel_no_crossrun_replay.py`: cancel a session, resume with the same `session_id`, assert unread messages from the previous run are NOT replayed (crash-replay applies only within the same run, per research.md C9). [size/S] [layer:tests] [parallel-safe]

### Implementation for User Story 3

- [ ] T032 [US3] Implement `Coordinator.cancel()` + cancellation propagation in `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/coordinator.py` (edits T023): emit `cancel` messages to all in-flight worker mailboxes via `asyncio.TaskGroup`; call `task.cancel()` on every worker `asyncio.Task`; await all with `asyncio.gather(..., return_exceptions=True)` bounded by 500 ms timeout; preserve any already-posted `result` messages when assembling partial `CoordinatorPlan`. Per research.md risk-3: wrap fsync-heavy mailbox writes in `asyncio.to_thread()` so `CancelledError` can propagate. FR-006, SC-003. [size/M] [layer:agents]
- [ ] T033 [US3] Implement `Worker` cancellation handler in `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/worker.py` (edits T022): on receiving `cancel` message OR on `asyncio.CancelledError`, propagate `CancelledError` without swallowing it; do NOT post a further `result`/`error` message after cancel; ensure `_query_inner` generator is properly closed via `await gen.aclose()`. Per data-model.md §7.2 worker state diagram. FR-006. [size/S] [layer:agents]

**Checkpoint**: US3 complete. 500 ms cancellation bound verified on loopback. Partial results preserved.

---

## Phase 6: User Story 4 — File-Based Mailbox Crash Resilience (Priority: P2)

**Goal**: Process crash mid-session; on restart with the same `session_id`, coordinator replays unread messages in per-sender FIFO order before dispatching new workers.

**Independent Test** (from spec): manually write a `result` message to the mailbox directory → start coordinator in replay mode → assert FIFO order, correct deserialisation, consumed marker written after processing (not re-delivered on second restart).

### Tests for User Story 4

- [ ] T034 [P] [US4] Unit test for `FileMailbox.send` + on-disk layout at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_mailbox_file.py`: (a) temp-rename atomic write sequence, (b) overflow at `KOSMOS_AGENT_MAILBOX_MAX_MESSAGES` raises `MailboxOverflowError`, (c) unwritable directory raises `MailboxWriteError`, (d) routing by `recipient` (FR-025), (e) permission `0o700`/`0o600` invariant from mailbox-abi.md §1. FR-014..FR-022. [size/M] [layer:tests] [parallel-safe]
- [ ] T035 [P] [US4] Crash-replay integration test at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_mailbox_crash_replay.py`: place a pre-written `result` JSON in a tmp session directory, start a fresh coordinator instance, assert it is read in FIFO order, deserialised correctly, marked consumed, and NOT re-delivered on a second coordinator restart. FR-019, SC-005. [size/M] [layer:tests] [parallel-safe]
- [ ] T036 [P] [US4] Corruption-tolerance test at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_mailbox_corrupt_skip.py`: write a truncated `.json` file (simulating a crash mid-write), assert `replay_unread` logs WARNING and continues with remaining valid messages without raising. FR-020, spec Edge Case "partially written message file". [size/S] [layer:tests] [parallel-safe]
- [ ] T037 [P] [US4] Per-sender FIFO ordering test at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_mailbox_fifo.py`: two senders, multiple messages each, assert per-sender FIFO holds by `<timestamp_ns>-<uuid4>.json` filename sort. Cross-sender ordering is unspecified (not asserted). FR-018. [size/S] [layer:tests] [parallel-safe]

### Implementation for User Story 4

- [ ] T038 [US4] Implement `FileMailbox` at `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/mailbox/file_mailbox.py` per mailbox-abi.md: (a) `send` — overflow check → O_EXCL temp file → fsync(fd) → close → rename → fsync(dir_fd) → return, (b) filename format `<timestamp_ns>-<uuid4>.json`, (c) `receive` — blocks until messages arrive, yields only messages matching `recipient`, (d) `replay_unread` — scans sender directories alphabetically, per-sender FIFO by filename sort, skips `.tmp` / corrupt / already-consumed messages, (e) wraps fsync calls in `asyncio.to_thread()` so the event loop stays responsive for cancellation. Mode `0o700`/`0o600` on all dirs/files. Auto-create `KOSMOS_AGENT_MAILBOX_ROOT` with `mkdir(parents=True, exist_ok=True, mode=0o700)` per research.md C6; on creation failure raise `MailboxWriteError`. FR-014..FR-022. [size/L] [layer:agents]
- [ ] T039 [US4] Implement consumed-marker helper in `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/mailbox/file_mailbox.py` (same file as T038): atomic write of `<id>.json.consumed` via temp + rename + fsync per mailbox-abi.md §3; called by `Coordinator` and `Worker` after successful message processing. FR-019. [size/S] [layer:agents]
- [ ] T040 [US4] Wire `FileMailbox` re-export into `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/__init__.py` (edits T025). [size/S] [layer:agents]

**Checkpoint**: US4 complete. Mailbox survives simulated crashes; unread messages replay in per-sender FIFO order; corrupt files skipped with WARNING.

---

## Phase 7: User Story 5 — Observability Spans (Priority: P3)

**Goal**: Coordinator, Workers, and Mailbox emit OTel spans compatible with Epic #501's boundary table. Langfuse surfaces phase transitions, tool-loop iterations, and delivery events.

**Independent Test** (from spec): run a session with a recording exporter → assert ≥ 1 `gen_ai.agent.coordinator.phase` span per transition, ≥ 1 `gen_ai.agent.worker.iteration` per tool-loop turn, 1 `gen_ai.agent.mailbox.message` per `send`, all `kosmos.agent.*` attribute names declared.

### Tests for User Story 5

- [ ] T041 [US5] Integration test at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_observability_spans.py` using `InMemorySpanExporter`: run a 3-worker session end-to-end, assert (a) exactly 4 `gen_ai.agent.coordinator.phase` spans with `phase` ∈ {research, synthesis, implementation, verification}, (b) ≥ 1 `gen_ai.agent.worker.iteration` span per worker with `kosmos.agent.role` + `kosmos.agent.session_id`, (c) 1 `gen_ai.agent.mailbox.message` span per `send` tagged with `msg_type`, `correlation_id`, `sender`, `recipient`, (d) message body is NEVER in span attributes (PIPA). FR-028..FR-031, SC-006. [size/M] [layer:tests] [parallel-safe]

### Implementation for User Story 5

- [ ] T042 [US5] Emit `gen_ai.agent.coordinator.phase` span per phase transition in `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/coordinator.py` (edits T023): one span per `RESEARCH`/`SYNTHESIS`/`IMPLEMENTATION`/`VERIFICATION` boundary with `kosmos.agent.coordinator.phase` attribute. FR-028. [size/S] [layer:observability]
- [ ] T043 [US5] Emit `gen_ai.agent.worker.iteration` span per tool-loop iteration in `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/worker.py` (edits T022): one span per `_query_inner` yield boundary with `kosmos.agent.role` + `kosmos.agent.session_id` attributes. Body content excluded per PIPA. FR-029. [size/S] [layer:observability]
- [ ] T044 [US5] Emit `gen_ai.agent.mailbox.message` span per `send` in `/Users/um-yunsang/KOSMOS-13/src/kosmos/agents/mailbox/file_mailbox.py` (edits T038): attributes `kosmos.agent.mailbox.msg_type`, `.correlation_id`, `.sender`, `.recipient`. FR-030. [size/S] [layer:observability]

**Checkpoint**: US5 complete. Langfuse dashboard shows coordinator phases, worker iterations, and mailbox deliveries for debugging multi-ministry queries.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, CI enforcement, and final integration checks.

- [ ] T045 [P] Document the 4 new `KOSMOS_AGENT_*` env vars in `/Users/um-yunsang/KOSMOS-13/docs/configuration.md` under a new "Agent Swarm (Epic #13)" section: name, default, range, purpose. FR-036, SC-009. [size/S] [layer:config] [parallel-safe]
- [ ] T046 [P] Assert no new runtime dependencies at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_no_new_deps.py`: diff `pyproject.toml` `[project.dependencies]` against the baseline captured at spec merge time; any addition fails the test. SC-008, AGENTS.md hard rule. [size/S] [layer:tests] [parallel-safe]
- [ ] T047 [P] Zero-live-API assertion at `/Users/um-yunsang/KOSMOS-13/tests/agents/test_zero_live_api.py`: intercept `httpx.AsyncClient` at session scope during `tests/agents/` collection; fail if any request targets `*.data.go.kr` without a fixture-tape match. SC-010, Constitution IV. [size/S] [layer:tests] [parallel-safe]
- [ ] T048 [P] Run `uv run pytest tests/agents/ -v --durations=10` and capture timing; document any test > 500 ms (informational) in `/Users/um-yunsang/KOSMOS-13/tests/agents/README.md`. Cancellation test MUST stay ≤ 500 ms per SC-003. [size/S] [layer:tests] [parallel-safe]
- [ ] T049 Validate `quickstart.md` end-to-end: run every `bash`/`python` snippet from `/Users/um-yunsang/KOSMOS-13/specs/027-agent-swarm-core/quickstart.md` against the implemented code; fix any drift. [size/S] [layer:tests]
- [ ] T050 Submit `kosmos.agent.*` attribute names to Epic #501's boundary table: open a follow-up PR comment on #501 listing the 7 new attribute constants from `src/kosmos/observability/semconv.py`. FR-031. [size/S] [layer:observability]

**Checkpoint**: Polish complete. `uv run pytest` green; docs updated; #501 notified.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no prior phase; T001 runs first (creates the package roots); T002–T004 parallel after T001 is in place for test-package creation.
- **Foundational (Phase 2)**: depends on Phase 1. T005–T012 are all `[P]` parallel (distinct files). T013–T015 unit tests run after their respective models land (T013 after T005; T014 after T007; T015 after T009), but all three can still be authored in parallel since they touch different test files.
- **User Story 1 (Phase 3)**: depends on Phase 2 complete. T016–T017 (contract tests) parallel. T018–T021 (integration + unit tests) parallel to each other. T022 (Worker) and T023 (Coordinator) depend on Phase 2; T024 depends on T023 (same file); T025 re-exports after T022+T023+T024.
- **User Story 2 (Phase 4)**: depends on US1 (edits `coordinator.py` and `worker.py`). Cannot run in parallel with T022/T023/T024.
- **User Story 3 (Phase 5)**: depends on US1 (edits the same files). Runs sequentially after US2 to avoid `coordinator.py`/`worker.py` merge conflicts.
- **User Story 4 (Phase 6)**: depends on Phase 2 (Mailbox ABC + messages). CAN run in parallel with US2/US3 IF a different Teammate handles it — touches `mailbox/file_mailbox.py` (distinct file). Coordinator uses only the ABC until US4 `FileMailbox` lands.
- **User Story 5 (Phase 7)**: depends on US1 + US4 (adds span emission to `coordinator.py`, `worker.py`, `file_mailbox.py`). Runs after US4.
- **Polish (Phase 8)**: depends on all user stories complete.

### User Story Parallelisation Map

| Phase | Can start when | Parallel-safe with |
|---|---|---|
| US1 (Phase 3) | Phase 2 done | — (blocks other stories that edit same files) |
| US2 (Phase 4) | US1 done | US4 only |
| US3 (Phase 5) | US2 done | US4 only |
| US4 (Phase 6) | Phase 2 done | US1/US2/US3 if different Teammate |
| US5 (Phase 7) | US4 done | — |

### Within Each User Story

- Tests authored in parallel with implementation (not strict TDD — spec's "Independent Test" acceptance is a gate, not a mandate that tests fail first).
- Models (Phase 2) before services (Phase 3+).
- Services before observability wrappers (Phase 7).
- Story-complete checkpoints are explicit; stop and validate before moving on.

### Parallel Opportunities

- Phase 1: T002, T003, T004 all `[P]` after T001.
- Phase 2: T005–T012 all `[P]` (8 distinct files). T013, T014, T015 `[P]` (3 distinct test files).
- US1: T016, T017, T019, T020, T021 `[P]` (5 distinct test files).
- US2: T026, T027 `[P]` (2 distinct test files). T028/T029 sequential (edit different files but belong to the same feature; safe to do in parallel if coordinated).
- US4: T034, T035, T036, T037 all `[P]` (4 distinct test files).
- Polish: T045, T046, T047, T048 all `[P]` (4 distinct files).

**Parallel-safe task count**: 24 of 50 tasks carry `[parallel-safe]` markers.

---

## Parallel Execution Example: Phase 2 (Foundational)

```text
# Launch all 8 model/infrastructure tasks in parallel (distinct files):
Task T005: AgentContext  → src/kosmos/agents/context.py
Task T006: errors        → src/kosmos/agents/errors.py
Task T007: messages      → src/kosmos/agents/mailbox/messages.py
Task T008: Mailbox ABC   → src/kosmos/agents/mailbox/base.py
Task T009: CoordinatorPlan → src/kosmos/agents/plan.py
Task T010: ConsentGateway → src/kosmos/agents/consent.py
Task T011: semconv extend → src/kosmos/observability/semconv.py
Task T012: settings extend → src/kosmos/settings.py

# Then launch the 3 unit tests in parallel:
Task T013: test_context.py
Task T014: test_messages.py
Task T015: test_plan.py
```

## Parallel Execution Example: User Story 1

```text
# Launch all 5 test tasks in parallel (distinct files):
Task T016: test_agent_message_schema.py
Task T017: test_coordinator_plan_schema.py
Task T019: test_synthesis_tool_gate.py
Task T020: test_solo_role_compat.py
Task T021: test_worker_lifecycle.py

# Implementation is sequential on shared files:
Task T022: worker.py
Task T023: coordinator.py        # depends on T022 import
Task T024: spawn_worker helper   # same file as T023
Task T025: __init__.py re-export # after T022, T023, T024
Task T018: test_coordinator_phases.py  # integration; run after T022+T023+T024
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories).
3. Complete Phase 3: User Story 1.
4. STOP and VALIDATE: `uv run pytest tests/agents/test_coordinator_phases.py tests/agents/test_synthesis_tool_gate.py tests/agents/test_worker_lifecycle.py`.
5. Merge / demo. MVP delivered.

### Incremental Delivery (recommended)

1. Phase 1 + 2 → foundation.
2. US1 → MVP (merge, demo).
3. US2 → permission delegation (merge).
4. US4 → crash resilience (merge; can land in parallel with US2/US3 on a separate PR).
5. US3 → cooperative cancellation (merge).
6. US5 → observability (merge).
7. Polish (Phase 8) → merge final PR closing Epic #13.

### Parallel Team Strategy (Agent Teams)

With 3+ Teammates available at `/speckit-implement`:

1. Team completes Phase 1 + 2 together (1 Teammate dispatches T001, then T002–T012 parallel).
2. Once Phase 2 green:
   - Teammate A: US1 (Phase 3) — owns `worker.py` + `coordinator.py`.
   - Teammate B: US4 (Phase 6) — owns `mailbox/file_mailbox.py`.
   - Teammate C: unit/contract tests T016, T017, T019, T020, T021 in parallel.
3. US2, US3 queue after US1 (same-file conflicts).
4. US5 queues after US4 (needs `FileMailbox` to emit spans).
5. Polish runs at end with 1 Teammate.

---

## Notes

- `[P]` tasks touch different files and have no dependencies on incomplete tasks.
- `[Story]` label maps each task to a specific user story for traceability.
- Every user story has an "Independent Test" acceptance path enforced by its test file.
- Commit after each task or logical group; no `--no-verify` (AGENTS.md hard rule).
- No new runtime dependencies — enforced by T046.
- No live `data.go.kr` calls — enforced by T047.
- Total: 50 tasks across 8 phases. Expected ~1200 LOC source + ~800 LOC tests per plan.md § Scale/Scope.

---

## Task count summary

| Phase | Tasks | Parallel-safe | Size breakdown |
|---|---|---|---|
| 1. Setup | 4 | 3 | 4S |
| 2. Foundational | 11 | 11 | 1M + 10S |
| 3. US1 (P1, MVP) | 10 | 5 | 1L + 3M + 6S |
| 4. US2 (P1) | 4 | 3 | 2M + 2S |
| 5. US3 (P2) | 4 | 2 | 2M + 2S |
| 6. US4 (P2) | 7 | 4 | 1L + 2M + 4S |
| 7. US5 (P3) | 4 | 1 | 1M + 3S |
| 8. Polish | 6 | 4 | 6S |
| **Total** | **50** | **33 carry `[parallel-safe]` or `[P]`** | **2L + 12M + 36S** |

**Ready for `/speckit-analyze`**.
