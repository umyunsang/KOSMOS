# Feature Specification: Agent Swarm Core — Layer 4

**Feature Branch**: `feat/13-agent-swarm-core`
**Created**: 2026-04-18
**Status**: Draft
**Input**: Epic #13 — Agent Swarm Core (Layer 4). Multi-agent orchestration substrate built on top of the 2-tool facade (#507). Ships coordinator loop, worker lifecycle, file-based mailbox IPC, and permission delegation chain without ministry-specific prompts.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Parallel Research via Coordinator Dispatch (Priority: P1)

A citizen submits a multi-ministry query (e.g., "이사 준비 중인데, 전입신고랑 자동차 주소변경이랑 건강보험 주소변경 다 해야 하는데"). The coordinator recognises that three research threads are needed, spawns three workers in parallel, collects their findings via the mailbox, and synthesises a unified `CoordinatorPlan` — all within a single coordinator turn. The citizen receives a structured plan referencing which tasks must be sequential and which can run in parallel.

**Why this priority**: This is the core contract of Layer 4. Without parallel worker dispatch and coordinator synthesis, the Agent Swarm layer provides no value over the Phase 1 single-agent loop. Every other story in this spec depends on this substrate.

**Independent Test**: Drive a scripted session with a stub LLM that responds as the coordinator. Assert: (a) coordinator spawns exactly three `asyncio.Task` workers via the mailbox, (b) all three workers complete and post `result` messages before synthesis begins, (c) the returned `CoordinatorPlan` references the `correlation_id` values from the worker result messages, (d) synthesis never calls `lookup` or `resolve_location` itself, (e) no live `data.go.kr` calls are made — all workers operate against recorded fixtures from the #507 seed adapters.

**Acceptance Scenarios**:

1. **Given** a coordinator session with three registered specialist slots and a multi-ministry query, **When** the coordinator enters the Research phase, **Then** exactly three worker `asyncio.Task`s are created with isolated `AgentContext` objects (no shared mutable state between workers).
2. **Given** three workers running in parallel, **When** all three post `result` messages to the coordinator mailbox, **Then** the coordinator's Synthesis phase begins and produces a `CoordinatorPlan` Pydantic v2 model that references each worker's `correlation_id`.
3. **Given** a `CoordinatorPlan` with ordered steps, **When** the plan classifies a step as sequential (e.g., residence transfer must precede vehicle registration), **Then** the Implementation phase executes those steps in the declared order.
4. **Given** a `CoordinatorPlan` with independent steps, **When** the plan classifies those steps as parallel, **Then** the Implementation phase runs them concurrently via `asyncio.TaskGroup`.
5. **Given** the coordinator is in Synthesis phase, **When** the coordinator LLM is prompted, **Then** the tool definitions injected into the LLM context contain exactly `lookup` and `resolve_location` and no synthesis-phase call to those tools is dispatched (synthesis is LLM text generation only).

---

### User Story 2 — Permission Delegation Chain (Priority: P1)

A worker encounters an adapter protected by `requires_auth=True` (e.g., `nmc_emergency_search`). The worker cannot approve or bypass this gate. Instead, it sends a `permission_request` message up to the coordinator. The coordinator prompts the citizen (via a stub in this epic; the real TUI prompt is #287), receives consent, and sends a `permission_response` back to the worker. The worker retries the `lookup(mode="fetch")` call. Permissions never flow laterally between workers.

**Why this priority**: Constitution Principle II ("permissions never flow laterally") is non-negotiable. Shipping the coordinator without this chain would mean the auth gate from #507 either silently fails or is bypassed — both are blockers for any Phase 2 production use.

**Independent Test**: Create a worker that stubs `LookupError(reason="auth_required")` on the first `lookup(mode="fetch")` call, sends a `permission_request`, waits for `permission_response`, and retries. Assert: (a) the worker sends exactly one `permission_request` message to the coordinator; (b) no other worker receives or processes that message (no lateral flow); (c) after receiving `permission_response`, the worker retries and receives the stubbed success envelope; (d) the full round-trip completes within 1 second on loopback.

**Acceptance Scenarios**:

1. **Given** a worker that calls `lookup(mode="fetch", tool_id="nmc_emergency_search")` and receives `LookupError(reason="auth_required")`, **When** the worker handles the error, **Then** it emits exactly one `permission_request` message addressed to `"coordinator"` and enters a waiting state.
2. **Given** a `permission_request` in the coordinator mailbox, **When** the coordinator reads it, **Then** it prompts the citizen consent stub and emits a `permission_response` message addressed to the requesting worker's `sender` field.
3. **Given** a `permission_response` delivered to the worker, **When** the worker resumes, **Then** it retries `lookup(mode="fetch")` with the same `correlation_id` and the retry result is included in the worker's final `result` message to the coordinator.
4. **Given** two workers running concurrently, **When** one worker emits a `permission_request`, **Then** the other worker's mailbox queue is not modified and the second worker cannot observe or act on the first worker's permission request.

---

### User Story 3 — Cooperative Cancellation (Priority: P2)

The citizen cancels the in-progress multi-ministry request, or the coordinator decides the request is unresolvable. The coordinator sends a `cancel` message to all in-flight workers. Every worker propagates `asyncio.CancelledError` and terminates cleanly within 500 ms. Mailbox state for the session is preserved (messages already flushed to disk are readable for debugging but not replayed on next session).

**Why this priority**: Without cooperative cancellation, a stale worker consuming LLM rate-limit capacity could block subsequent citizen requests. The 500 ms bound is derived from the Phase 1 single-agent timeout expectations and the coordinator's per-session semaphore (from #019 hardening).

**Independent Test**: Spawn three workers via the coordinator. After all three workers have started but before any has completed, call `coordinator.cancel()`. Assert: (a) all three workers raise `asyncio.CancelledError` within 500 ms; (b) the coordinator `asyncio.Task` completes cleanly; (c) no uncaught exception leaks; (d) worker mailbox queues show the `cancel` message as the last delivered message.

**Acceptance Scenarios**:

1. **Given** three workers running in the Research phase, **When** the coordinator calls its cancellation path, **Then** all three workers are cancelled within 500 ms.
2. **Given** a worker that has already posted a `result` message before the `cancel` arrives, **When** the coordinator processes results, **Then** the already-completed result is included in any partial `CoordinatorPlan` and the cancel does not discard it.
3. **Given** a cancelled session, **When** the same `session_id` is resumed, **Then** unread mailbox messages from the previous run are NOT replayed (crash-replay applies only to messages within the same session run, not cross-run).

---

### User Story 4 — File-Based Mailbox Crash Resilience (Priority: P2)

The KOSMOS process crashes mid-session (e.g., OOM kill) after a worker has posted a `result` message but before the coordinator has read it. On process restart with the same `session_id`, the coordinator can replay unread messages from the file-based mailbox in per-sender FIFO order and resume synthesis.

**Why this priority**: A file-based mailbox that does not survive crashes is equivalent to an in-memory queue and provides no durability guarantee. This story verifies the mailbox's at-least-once delivery contract, which is the stated rationale for choosing files over in-process queues in `docs/vision.md § Layer 4`.

**Independent Test**: Write a `result` message to the mailbox directory manually (simulating a completed worker). Start the coordinator in replay mode. Assert: (a) the coordinator reads the pre-written message in FIFO order; (b) the message is deserialized into the correct `AgentMessage` variant; (c) replayed messages are marked as consumed (not re-delivered on a second restart).

**Acceptance Scenarios**:

1. **Given** a worker that has written a `result` message to `~/.kosmos/mailbox/<session_id>/` before the process terminates, **When** the coordinator restarts with the same `session_id`, **Then** it reads and processes the unread `result` message before dispatching new workers.
2. **Given** two workers that have both written messages to the mailbox, **When** the coordinator replays them, **Then** messages from each sender are delivered in the order they were written (per-sender FIFO).
3. **Given** a partially written message file (simulating a crash mid-write), **When** the mailbox reader encounters it, **Then** it skips the corrupted file, logs a warning, and continues with the remaining valid messages — it does not crash.

---

### User Story 5 — Observability Spans for Agent Phases and Mailbox Delivery (Priority: P3)

The coordinator and workers emit OpenTelemetry spans that are compatible with the attribute boundary table established in Epic #501. The Langfuse dashboard surfaces coordinator phase transitions, worker tool-loop iterations, and mailbox delivery events as structured trace data for debugging multi-ministry queries.

**Why this priority**: Without observability, diagnosing failures in the multi-worker flow requires log-scraping. The span schema is defined here so that #501's collector can ingest it without a breaking schema change. This is a deferrable quality-of-life item relative to correctness, but the attribute names must be frozen before any collector deploys.

**Independent Test**: Run a coordinator session end-to-end with a recording exporter. Assert: (a) at least one `gen_ai.agent.coordinator.phase` span per phase transition appears in the trace; (b) each worker emits at least one `gen_ai.agent.worker.iteration` span per tool-loop turn; (c) each mailbox `send` operation emits a `gen_ai.agent.mailbox.message` span tagged with `msg_type`; (d) all attribute names are in the `kosmos.agent.*` namespace declared in this spec.

**Acceptance Scenarios**:

1. **Given** a coordinator executing all four phases, **When** the trace is exported, **Then** exactly four `gen_ai.agent.coordinator.phase` spans appear with `phase` attribute values `"research"`, `"synthesis"`, `"implementation"`, `"verification"`.
2. **Given** a worker that executes two tool-loop iterations, **When** the trace is exported, **Then** exactly two `gen_ai.agent.worker.iteration` spans appear tagged with `kosmos.agent.role` set to the worker's specialist role value (from the `AgentContext`).
3. **Given** a `permission_request` message delivered via the mailbox, **When** the trace is exported, **Then** a `gen_ai.agent.mailbox.message` span appears with `msg_type="permission_request"` and the `correlation_id` as a span attribute.

---

### Edge Cases

- **Worker exceeds iteration cap**: A worker that hits `max_iterations` inside its tool loop MUST send an `error` message to the coordinator (not silently terminate). The coordinator MUST include this error in the `CoordinatorPlan` and mark the affected ministry task as `status="failed"`.
- **Coordinator mailbox full**: If the per-session mailbox directory contains more messages than `KOSMOS_AGENT_MAILBOX_MAX_MESSAGES`, new writes MUST fail with a structured `MailboxOverflowError` rather than silently dropping messages or growing unbounded.
- **Duplicate `result` message**: If a worker retries and delivers two `result` messages for the same `correlation_id`, the coordinator MUST use the first non-error result and log a warning for the duplicate. It MUST NOT produce a `CoordinatorPlan` with duplicate ministry entries.
- **Worker spawned with no specialist role in `AgentContext`**: The coordinator MUST refuse to spawn a worker whose `AgentContext.role` is `None`. This is a programmer error and MUST raise `AgentConfigurationError` at spawn time.
- **Synthesis called with zero worker results**: If the coordinator enters the Synthesis phase with an empty results set (all workers failed), the coordinator MUST yield a `CoordinatorPlan` with `status="no_results"` and an explanatory `message` field rather than producing a partial or empty plan silently.
- **File permission error on mailbox write**: If the mailbox directory is not writable (e.g., disk-full or permission denied), the mailbox writer MUST raise `MailboxWriteError` immediately — it MUST NOT retry or silently discard the message.
- **`AgentContext` shared mutable state attempt**: If a worker attempts to mutate state on an object shared with another worker (detectable via `AgentContext` isolation check), the coordinator MUST raise `AgentIsolationViolation` and cancel all workers.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Coordinator loop

- **FR-001**: The system MUST provide a `Coordinator` class at `src/kosmos/agents/coordinator.py` that orchestrates the 4-phase workflow: `Research → Synthesis → Implementation → Verification` as defined in `docs/vision.md § Layer 4`.
- **FR-002**: The coordinator MUST dispatch workers as `asyncio.Task` objects via `asyncio.create_task()`, each receiving an isolated `AgentContext` with no shared mutable state between workers.
- **FR-003**: The coordinator MUST classify citizen intent to determine which specialist roles to spawn. Intent classification MUST be performed by the coordinator LLM, not by a static keyword table.
- **FR-004**: The coordinator MUST execute the Synthesis phase itself — it MUST NOT delegate synthesis to a worker. During Synthesis, the coordinator LLM MUST NOT have `lookup` or `resolve_location` injected into its tool definitions.
- **FR-005**: The coordinator MUST produce a `CoordinatorPlan` Pydantic v2 model as the output of the Synthesis phase. `CoordinatorPlan` MUST reference the `correlation_id` values of the worker `result` messages that contributed to it.
- **FR-006**: The coordinator MUST implement cooperative cancellation: calling `coordinator.cancel()` MUST propagate `asyncio.CancelledError` to all in-flight worker tasks within 500 ms.
- **FR-007**: The coordinator MUST support a `role: Literal["solo", "coordinator", "specialist"]` variant in the system prompt context. The `solo` variant MUST be behaviorally identical to the Phase 1 single-agent loop (backward compatibility).

#### Worker lifecycle

- **FR-008**: The system MUST provide a `Worker` class at `src/kosmos/agents/worker.py` that wraps one `QueryEngine` instance and drives it through the 2-tool surface (`lookup` + `resolve_location`).
- **FR-009**: Workers MUST reuse `src/kosmos/engine/query.py`'s `_query_inner()` async generator as their inner tool loop verbatim. The worker MUST NOT reimplement the tool loop.
- **FR-010**: Each worker MUST receive an `AgentContext` at spawn time that pins the worker to a specific `session_id` and `specialist_role`. The `AgentContext` MUST be a Pydantic v2 frozen model with `extra="forbid"`.
- **FR-011**: A worker MUST only see `lookup` and `resolve_location` in its tool registry — no other tools, no direct adapter references, no per-API tool names.
- **FR-012**: When a worker's tool loop completes, the worker MUST post a `result` message to the coordinator mailbox containing a `LookupFetchOutput`-compatible payload (typed union member, not raw text).
- **FR-013**: When a worker's tool loop fails unrecoverably, the worker MUST post an `error` message to the coordinator mailbox with a structured error payload, and MUST NOT silently terminate.

#### Mailbox IPC

- **FR-014**: The system MUST provide a `Mailbox` class and related infrastructure at `src/kosmos/agents/mailbox/`. The file-based implementation MUST store messages under `KOSMOS_AGENT_MAILBOX_ROOT/<session_id>/<sender_id>/<message_id>.json`.
- **FR-015**: `KOSMOS_AGENT_MAILBOX_ROOT` MUST default to `~/.kosmos/mailbox` and MUST be configurable as a `KOSMOS_AGENT_MAILBOX_ROOT` environment variable.
- **FR-016**: The `AgentMessage` model MUST be a Pydantic v2 model with `extra="forbid"` and the following fields: `id: UUID`, `sender: str`, `recipient: str`, `msg_type: Literal["task", "result", "error", "permission_request", "permission_response", "cancel"]`, `payload: AgentMessagePayload` (a closed discriminated union — NOT `dict[str, Any]`), `timestamp: datetime`, `correlation_id: UUID | None`. The `Any` type is forbidden in the `payload` field and all its union members.
- **FR-017**: The mailbox MUST guarantee at-least-once delivery: a message MUST be fully written to disk (fsync) before the `send()` call returns.
- **FR-018**: Within a single sender, messages MUST be delivered in FIFO order. Cross-sender ordering is not guaranteed.
- **FR-019**: On coordinator startup with an existing `session_id`, the mailbox MUST replay unread messages in per-sender FIFO order before the coordinator dispatches new workers.
- **FR-020**: A partially-written or undeserializable message file MUST be skipped (logged at WARNING level) and MUST NOT crash the mailbox reader.
- **FR-021**: The mailbox MUST enforce a per-session message cap of `KOSMOS_AGENT_MAILBOX_MAX_MESSAGES` (default: 1000, clamped to [100, 10000]). Writes beyond the cap MUST raise `MailboxOverflowError` immediately.
- **FR-022**: The `Mailbox` interface MUST be an abstract base class so that a future Redis Streams backend can be substituted without changing the coordinator or worker code.

#### Permission delegation chain

- **FR-023**: When a worker receives `LookupError(reason="auth_required")` from its tool loop, the worker MUST emit a `permission_request` message addressed to `"coordinator"` and enter a waiting state (blocking its tool loop at the current iteration).
- **FR-024**: When the coordinator receives a `permission_request`, it MUST prompt the citizen consent stub (a `ConsentGateway` abstract class in this epic; the real TUI integration is #287) and emit a `permission_response` message addressed to the requesting worker's `sender` field.
- **FR-025**: Permissions MUST NOT flow laterally between workers. A worker MUST NOT read another worker's `permission_request` or `permission_response` messages. The mailbox MUST enforce this by routing messages only to the declared `recipient` field.
- **FR-026**: If the coordinator's consent gateway stub returns `denied`, the coordinator MUST emit a `permission_response` with `granted=False`. The worker MUST convert this into an `error` message to the coordinator and MUST NOT retry the denied tool call.
- **FR-027**: The `ConsentGateway` abstract class MUST define one async method: `async def request_consent(self, tool_id: str, correlation_id: UUID) -> bool`. The stub implementation for this epic MUST always return `True` (unconditional grant for testing purposes).

#### Observability

- **FR-028**: The coordinator MUST emit one `gen_ai.agent.coordinator.phase` OTel span per phase transition. The span MUST carry the attribute `kosmos.agent.coordinator.phase: Literal["research", "synthesis", "implementation", "verification"]`.
- **FR-029**: Each worker MUST emit one `gen_ai.agent.worker.iteration` span per tool-loop iteration. The span MUST carry `kosmos.agent.role` (the worker's specialist role string from `AgentContext`) and `kosmos.agent.session_id` (the session UUID, not PII).
- **FR-030**: The mailbox `send()` operation MUST emit one `gen_ai.agent.mailbox.message` span per delivery. The span MUST carry `kosmos.agent.mailbox.msg_type` and `kosmos.agent.mailbox.correlation_id`.
- **FR-031**: All new `kosmos.agent.*` attribute names MUST be declared as string constants in `src/kosmos/observability/semconv.py` (extending the existing module). The attribute names MUST be submitted to Epic #501's boundary table before any collector deployment.

#### Configuration and environment

- **FR-032**: `KOSMOS_AGENT_MAILBOX_ROOT` MUST default to `~/.kosmos/mailbox` and MUST accept any writable absolute path.
- **FR-033**: `KOSMOS_AGENT_MAILBOX_MAX_MESSAGES` MUST default to 1000 and be clamped to [100, 10000].
- **FR-034**: `KOSMOS_AGENT_MAX_WORKERS` MUST default to 4 and be clamped to [1, 16]. The coordinator MUST NOT spawn more concurrent workers than this cap.
- **FR-035**: `KOSMOS_AGENT_WORKER_TIMEOUT_SECONDS` MUST default to 120 and be clamped to [10, 600]. A worker that does not post a `result` or `error` message within this timeout MUST be cancelled by the coordinator and treated as an error.
- **FR-036**: All four `KOSMOS_AGENT_*` env vars MUST be documented in `docs/configuration.md` (the catalog owned by #468).

#### Testing

- **FR-037**: All agent integration tests MUST use recorded fixtures from the #507 seed adapters. No live `data.go.kr` calls are permitted in CI.
- **FR-038**: The synthesis phase MUST have a unit test that asserts `lookup` and `resolve_location` are never called during the synthesis LLM invocation (verified by asserting the tool definitions list injected into the LLM is empty or omitted in synthesis mode).
- **FR-039**: The mailbox crash-replay test MUST simulate a prior-run result message on disk and assert it is replayed correctly on coordinator startup.
- **FR-040**: The cooperative cancellation test MUST assert all three spawned workers are cancelled within 500 ms.

### Key Entities

- **`Coordinator`**: Orchestrates the 4-phase workflow. Owns the session-level `AgentContext`, spawns workers, reads the mailbox, synthesises the `CoordinatorPlan`, and manages the `ConsentGateway` reference.
- **`Worker`**: Wraps one `QueryEngine` instance. Drives the Phase 1 tool loop restricted to `lookup` + `resolve_location`. Posts `result` or `error` messages to the mailbox on completion.
- **`AgentContext`**: Frozen Pydantic v2 model injected at worker spawn time. Fields: `session_id: UUID`, `specialist_role: str`, `coordinator_id: str`, `tool_registry: ToolRegistry` (Phase 1 registry restricted to 2 tools), `llm_client: LLMClient`. `extra="forbid"`. `arbitrary_types_allowed=True` for non-Pydantic infra objects.
- **`AgentMessage`**: Pydantic v2 model for all inter-agent messages. `msg_type` is the closed discriminator. `payload` is a discriminated union across six concrete payload types (one per `msg_type` value). No `Any`.
- **`AgentMessagePayload`**: Discriminated union: `TaskPayload | ResultPayload | ErrorPayload | PermissionRequestPayload | PermissionResponsePayload | CancelPayload`. Each member is a Pydantic v2 model with `extra="forbid"`.
- **`ResultPayload`**: Contains `lookup_output: LookupRecord | LookupCollection | LookupTimeseries` (the frozen #507 union members) and `turn_count: int`.
- **`CoordinatorPlan`**: Pydantic v2 model produced by Synthesis. Fields: `session_id: UUID`, `status: Literal["complete", "partial", "no_results", "failed"]`, `steps: list[PlanStep]`, `worker_correlation_ids: list[UUID]`, `message: str | None`.
- **`PlanStep`**: `ministry: str`, `action: str`, `depends_on: list[int]` (indices into `steps` list), `execution_mode: Literal["sequential", "parallel"]`, `status: Literal["pending", "in_progress", "complete", "failed"]`.
- **`Mailbox`** (abstract): `async send(message: AgentMessage) -> None`, `async receive(recipient: str) -> AsyncIterator[AgentMessage]`, `async replay_unread(recipient: str) -> AsyncIterator[AgentMessage]`.
- **`FileMailbox`**: Concrete implementation. Stores messages as JSON files under `KOSMOS_AGENT_MAILBOX_ROOT/<session_id>/<sender_id>/`. At-least-once delivery via fsync.
- **`ConsentGateway`** (abstract): `async request_consent(tool_id: str, correlation_id: UUID) -> bool`. Stub implementation returns `True`. Real implementation is #287.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The coordinator dispatches at least two parallel workers for a synthetic multi-ministry query; all workers operate only on `lookup` and `resolve_location` (verified by asserting no other tool names appear in the worker tool registry during the test run).
- **SC-002**: The Synthesis phase produces a `CoordinatorPlan` that references the `correlation_id` values of all contributing worker `result` messages (zero-orphan-id assertion).
- **SC-003**: `asyncio.CancelledError` propagates from the coordinator to all in-flight workers within 500 ms on local loopback (measured by wall-clock timer in the cancellation integration test).
- **SC-004**: A worker that receives `LookupError(reason="auth_required")` triggers the full permission delegation chain (worker → coordinator → consent stub → coordinator → worker) and completes without lateral permission sharing (asserted by inspecting per-worker mailbox queues after the test run).
- **SC-005**: The file-based mailbox survives a simulated mid-session process termination: pre-written result messages on disk are replayed in per-sender FIFO order on coordinator restart (crash-replay integration test green).
- **SC-006**: `gen_ai.agent.coordinator.phase`, `gen_ai.agent.worker.iteration`, and `gen_ai.agent.mailbox.message` spans appear in the recording exporter output with all required attributes present (no missing `kosmos.agent.*` attributes).
- **SC-007**: The Phase 1 single-agent flow (`role="solo"`) is unaffected — the existing `QueryEngine` integration tests remain green after this epic is merged.
- **SC-008**: No `print()` calls, no `Any` on public model fields, no hardcoded paths, and no new runtime dependencies beyond those already declared in `pyproject.toml` appear in the merged diff.
- **SC-009**: All four `KOSMOS_AGENT_*` env vars are listed in `docs/configuration.md` before the PR is merged.
- **SC-010**: Zero live `data.go.kr` API calls are made during the full CI test run (verified by fixture tape inspection).

---

## Assumptions

- Epic #507 (2-tool facade: `lookup` + `resolve_location` + 4 seed adapters) is merged and stable before implementation of this epic begins.
- Epic #468 (env-var registry) is either merged or its `docs/configuration.md` section is open for additive edits when this epic lands.
- Epic #501 (observability boundary table) is either merged or its attribute boundary table is available in draft form so that the `kosmos.agent.*` attribute names declared here can be submitted before any collector deploys.
- The FriendliAI K-EXAONE endpoint supports independent LLM clients for each coordinator and worker without additional provisioning (each `LLMClient` instance uses the per-session semaphore from #019; no new concurrency infrastructure is needed).
- Ministry specialist system prompts (#14) are not required for this epic's integration tests — workers operate with a generic "specialist" system prompt stub that exercises the tool loop without ministry-specific intent.
- The file system where `KOSMOS_AGENT_MAILBOX_ROOT` resides supports POSIX fsync semantics (macOS and Linux CI environments both satisfy this).
- The `AgentContext` model uses `arbitrary_types_allowed=True` to accommodate `LLMClient` and `ToolRegistry` which are not Pydantic models. This follows the precedent set by `QueryContext` in `src/kosmos/engine/models.py`.
- No new Python runtime dependencies are introduced. All required primitives (`asyncio`, `uuid`, `datetime`, `pathlib`, `json`) are stdlib. All external imports (`pydantic`, `opentelemetry`, `httpx`) are already declared in `pyproject.toml`.

---

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **Individual adapter tool registration at the agent layer**: Coordinator and workers see only `lookup` + `resolve_location`. Per-API tools will never be exposed at the agent layer — this is an architectural constraint per `docs/vision.md § Layer 4` and `docs/design/mvp-tools.md`.
- **Nested tool calls (dispatcher-calls-sub-tool chains)**: Forbidden permanently per NESTful (arXiv:2409.03797) — nested tool calls amplify failure 17x. The coordinator never calls tools; only workers call tools, and workers never spawn sub-workers.
- **Lateral permission flow between workers**: Constitution Principle II is non-negotiable and permanent. Permissions flow only vertically (worker → coordinator → citizen → coordinator → worker).
- **Live `data.go.kr` API calls in CI tests**: Permanently forbidden per constitution Principle IV.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Ministry specialist system prompts (transport, health, welfare, civil affairs) | Requires stable swarm substrate first; specialist prompts are domain content, not infrastructure | Epic #14 — Ministry Specialists | #14 |
| TUI rendering of coordinator phase transitions (`Research…`, `Synthesizing…` spinners) | TUI layer is Phase 2+; the consent gateway stub in this epic is the integration point | Epic #287 — TUI | #287 |
| Production hardening: dead-letter queue, cross-process mailbox, per-worker retry budgets | MVP mailbox is single-process; production durability is a separate epic | Epic #21 — Production Hardening | #21 |
| Redis Streams mailbox backend | File-based mailbox is sufficient for Phase 2 local demo; Redis backend is Phase 3 | Phase 3 — Production Scale | NEEDS TRACKING |
| Cross-session agent memory (worker remembers prior citizen interactions) | Layer 5 auto-memory is per-session in Phase 2; cross-session memory is Phase 3 | Phase 3 — Context Assembly | NEEDS TRACKING |
| Account-wide LLM rate-limit orchestration across coordinator + N workers | Per-session semaphore from #019 is sufficient for Phase 2; account-wide budget is Layer 6 | Epic #21 / Layer 6 Error Recovery | NEEDS TRACKING |
| Scenario graph / multi-turn planning above the coordinator | Scenario-level orchestration is a layer above the coordinator and depends on this substrate landing first | Scenario Graph epic | NEEDS TRACKING |
| Agent-to-agent handoff (worker delegates to a peer worker) | Flat dispatch is the Phase 2 model; handoff patterns are Phase 3 multi-coordinator | Phase 3 | NEEDS TRACKING |
| Formal observability attribute registration with OTel upstream | `kosmos.agent.*` attributes are KOSMOS-internal extensions; upstream registration is a post-Phase-2 contribution | Phase 3 / OSS contribution | NEEDS TRACKING |
