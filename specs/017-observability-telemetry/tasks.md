---
feature: Observability and Telemetry
epic: "#290"
status: draft
---

# Tasks: Observability and Telemetry

**Input**: Design documents from `/specs/017-observability-telemetry/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Included — spec AC-A12 explicitly requires unit tests for all four instrumentation areas.

**Organization**: Tasks grouped by user story for independent implementation and testing. Phase A only (zero new dependencies). Phase B deferred per spec.md § Deferred Items.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US3)
- Include exact file paths in descriptions

---

## Phase 1: Foundation — EventLogger + EventType Extension

**Purpose**: Create the structured event emission infrastructure that all later phases depend on. Extends the existing `src/kosmos/observability/` files — does **not** replace them.

- [ ] T001 Extend `EventType` Literal in `src/kosmos/observability/events.py` — add `"permission_decision"` and `"llm_call"` to the union; update module docstring
- [ ] T002 Create `ObservabilityEventLogger` class in `src/kosmos/observability/event_logger.py` (new file) with `emit(event: ObservabilityEvent) -> None`, level-map keyed on `(event_type, success)`, PII key whitelist enforcement, and fail-safe try/except
- [ ] T003 Add `ObservabilityEventLogger` to re-export list in `src/kosmos/observability/__init__.py`

**Checkpoint**: `from kosmos.observability import ObservabilityEventLogger` succeeds. `emit()` emits structured JSON at the correct log level for each event type.

---

## Phase 2: User Story 3 — LLM Token and Duration Metrics (Priority: P1) MVP

**Goal**: `LLMClient.complete()` and `LLMClient.stream()` record `llm.call_duration_ms` histogram; `UsageTracker.debit()` increments `llm.input_tokens` and `llm.output_tokens` counters; both are wired via optional `metrics: MetricsCollector | None` constructor injection.

**Independent Test**: `uv run pytest tests/llm/test_metrics_integration.py` passes with no live API calls.

### Tests for User Story 3

- [ ] T004 [P] [US3] Create `tests/llm/test_metrics_integration.py` with: `test_complete_increments_token_counters`, `test_complete_observes_duration`, `test_stream_increments_token_counters`, `test_no_metrics_no_error` (backward compat), `test_histogram_percentiles_10_observations`

### Implementation for User Story 3

- [ ] T005 [US3] Add `metrics: MetricsCollector | None = None` parameter to `UsageTracker.__init__` in `src/kosmos/llm/usage.py`; in `debit()` increment `llm.input_tokens` and `llm.output_tokens` after budget logic, wrapped in try/except
- [ ] T006 [US3] Add `metrics: MetricsCollector | None = None` and `event_logger: ObservabilityEventLogger | None = None` parameters to `LLMClient.__init__` in `src/kosmos/llm/client.py`; pass `metrics` through to `UsageTracker` at construction
- [ ] T007 [US3] In `LLMClient.complete()` in `src/kosmos/llm/client.py` — bracket `_do_request` with monotonic timer; call `metrics.observe("llm.call_duration_ms", ms)` and `metrics.increment("llm.call_count")` on success; `metrics.increment("llm.error_count")` on failure; emit `ObservabilityEvent(event_type="llm_call")` via `event_logger`; all wrapped in try/except
- [ ] T008 [US3] In `LLMClient.stream()` in `src/kosmos/llm/client.py` — start timer before `async with`; record `llm.call_duration_ms` and `llm.call_count` at `event.type == "done"`; increment `llm.error_count` on `StreamInterruptedError`; emit `llm_call` event; all wrapped in try/except

**Checkpoint**: `test_complete_increments_token_counters` and `test_stream_increments_token_counters` pass. Histogram has non-zero p50/p95/p99 after 10 observations. AC-A3, AC-A4, AC-A11 (US3) validated.

---

## Phase 3: User Story 2 — Permission Pipeline Instrumentation (Priority: P1)

**Goal**: Every `PermissionPipeline.run()` call records `permission.pipeline_duration_ms`; every step outcome increments `permission.decision_count{step,decision}`; refusal circuit trips increment `permission.refusal_circuit_trips`; `permission_decision` events are emitted as structured JSON.

**Independent Test**: `uv run pytest tests/permissions/test_pipeline_metrics.py` passes with no live API calls.

### Tests for User Story 2

- [ ] T009 [P] [US2] Create `tests/permissions/test_pipeline_metrics.py` with: `test_decision_count_incremented_per_step_allow`, `test_decision_count_incremented_on_deny_step3`, `test_refusal_circuit_trips_incremented`, `test_pipeline_duration_recorded_on_deny`, `test_pipeline_duration_recorded_on_success`, `test_no_metrics_no_error`

### Implementation for User Story 2

- [ ] T010 [US2] Add `metrics: MetricsCollector | None = None` and `event_logger: ObservabilityEventLogger | None = None` parameters to `PermissionPipeline.__init__` in `src/kosmos/permissions/pipeline.py`
- [ ] T011 [US2] In `PermissionPipeline._run_pre_execution_steps()` in `src/kosmos/permissions/pipeline.py` — after each `step_result`, increment `permission.decision_count{step, decision}`; on step exception branch emit `decision=deny`; all wrapped in try/except (AC-A1)
- [ ] T012 [US2] In `PermissionPipeline._run_pre_execution_steps()` and `_execute_step6()` in `src/kosmos/permissions/pipeline.py` — after each decision metric, emit `ObservabilityEvent(event_type="permission_decision")` via `event_logger` with `metadata={"step": int, "decision": str, "reason": str}` (PII-clean); wrapped in try/except (AC-A5, AC-A7 partial)
- [ ] T013 [US2] Expose trip indicator from `src/kosmos/permissions/steps/refusal_circuit_breaker.py` — extend `record_denial()` return value or add a query function so `PermissionPipeline` can detect circuit trips; increment `permission.refusal_circuit_trips` on trip (AC-A3 refusal circuit)
- [ ] T014 [US2] In `PermissionPipeline.run()` in `src/kosmos/permissions/pipeline.py` — wrap body in `try/finally` after monotonic timer start; record `permission.pipeline_duration_ms` histogram on all exit paths (allow, deny, not-found, bypass); wrapped in try/except (AC-A2)

**Checkpoint**: `test_decision_count_incremented_on_deny_step3` passes. `test_pipeline_duration_recorded_on_deny` confirms duration is recorded even on early-exit deny. AC-A1, AC-A2, AC-A3 (refusal circuit), AC-A9 validated.

---

## Phase 4: User Story 2 (continued) — Tool and Recovery Event Wiring

**Goal**: Wire `ObservabilityEventLogger` into `ToolExecutor.dispatch()` and `RecoveryExecutor.execute()` for `tool_call`, `retry`, and `circuit_break` events (AC-A6, AC-A7).

**Independent Test**: Existing `tests/tools/` and `tests/recovery/` suites continue to pass; new event assertions verify emission.

### Tests for Tool + Recovery Event Wiring

- [ ] T015 [P] [US2] Add `test_tool_executor_emits_tool_call_event` to `tests/tools/test_executor.py` — mock `event_logger`; assert `emit()` called with `event_type="tool_call"` after dispatch
- [ ] T016 [P] [US2] Add `test_recovery_executor_emits_retry_event` and `test_recovery_executor_emits_circuit_break_event` to `tests/recovery/test_retry.py` — mock `event_logger`; assert events emitted with correct fields

### Implementation for Tool + Recovery Event Wiring

- [ ] T017 [US2] Add `event_logger: ObservabilityEventLogger | None = None` parameter to `ToolExecutor.__init__` in `src/kosmos/tools/executor.py`; after dispatch completes (both success and failure), emit `ObservabilityEvent(event_type="tool_call")` with `tool_id`, `duration_ms`, `success`, `metadata={"error_type": ...}`; wrapped in try/except (AC-A6)
- [ ] T018 [US2] Add `event_logger: ObservabilityEventLogger | None = None` parameter to `RecoveryExecutor.__init__` in `src/kosmos/recovery/executor.py`; emit `ObservabilityEvent(event_type="retry")` after retry batch with `metadata={"attempt": N, "error_class": str}`; emit `event_type="circuit_break"` on `if not breaker.allow_request()` branch with `metadata={"circuit_state": str(breaker.state)}`; both wrapped in try/except (AC-A7)

**Checkpoint**: Mock-based tests pass. `emit()` called exactly once per dispatch and once per circuit trip. AC-A6, AC-A7 validated.

---

## Phase 5: User Story 1 — `/metrics` REPL Command (Priority: P1)

**Goal**: Typing `/metrics` at the REPL renders a Rich table of `MetricsCollector.snapshot()` output — counters, histograms (p50/p95/p99), and gauges. Empty session shows a clear "no data" message.

**Independent Test**: `uv run pytest tests/cli/test_metrics_command.py` passes.

### Tests for User Story 1

- [ ] T019 [P] [US1] Create `tests/cli/test_metrics_command.py` with: `test_metrics_empty_collector` (output contains "No metrics collected in this session."), `test_metrics_renders_table` (output contains metric name and numeric value after inserting one counter + one histogram), `test_metrics_no_error_concurrent` (snapshot is non-blocking while background task writes metrics)

### Implementation for User Story 1

- [ ] T020 [US1] Register `"metrics"` `SlashCommand` entry in `COMMANDS` dict in `src/kosmos/cli/models.py` with description `"Show session metrics snapshot (counters, histograms, gauges)"`
- [ ] T021 [US1] Add `metrics: MetricsCollector | None = None` parameter to `REPLLoop.__init__` in `src/kosmos/cli/repl.py`; store as `self._metrics`
- [ ] T022 [US1] Add `elif name == "metrics": self._cmd_metrics()` dispatch branch in `REPLLoop._dispatch_command()` in `src/kosmos/cli/repl.py`
- [ ] T023 [US1] Implement `REPLLoop._cmd_metrics()` in `src/kosmos/cli/repl.py` using `rich.table.Table` — render COUNTERS section, HISTOGRAMS section (columns: name, p50, p95, p99, count; values formatted as `{v:.0f} ms`), GAUGES section; omit empty sections; show "No metrics collected in this session." when snapshot has no data (AC-A8)

**Checkpoint**: `/metrics` renders formatted table in REPL. Empty session shows no-data message without error. AC-A8, US-1 acceptance scenarios 1–3 validated.

---

## Phase 6: Startup Wiring — app.py Dependency Injection

**Purpose**: Create a single shared `MetricsCollector` + `ObservabilityEventLogger` at startup; inject into all subsystems; pass `metrics` to `REPLLoop`. This is the only phase that touches `app.py`.

- [ ] T024 Inspect `src/kosmos/engine/` to determine how `PermissionPipeline` is constructed (inside `QueryEngine` or externally) — document the injection point before coding
- [ ] T025 In `src/kosmos/cli/app.py` `_run_repl()`, create `MetricsCollector()` and `ObservabilityEventLogger()` instances; pass `metrics` and `event_logger` into `RecoveryExecutor`, `ToolExecutor`, `LLMClient`, and `PermissionPipeline` (or `QueryEngine` if pipeline is internal); pass `metrics` to `REPLLoop`
- [ ] T026 Update `src/kosmos/context/builder.py` or `QueryEngine` constructor (wherever `PermissionPipeline` is assembled) to accept optional `metrics` and `event_logger` parameters so the shared instances flow through

**Checkpoint**: Running `uv run python -m kosmos` starts without error. Typing `/metrics` after one query shows non-zero counters for `tool.call_count`, `llm.input_tokens`, and `permission.decision_count`.

---

## Phase 7: Testing and Validation

**Purpose**: Full AC-A12 test coverage, lint clean, and integration smoke test. No new source files — only new test files and CI verification.

- [ ] T027 [P] Create `tests/observability/test_event_logger.py` with: `test_emit_level_by_event_type_and_success` (parameterized over all `(event_type, success)` pairs), `test_emit_pii_key_dropped` (non-whitelisted key dropped, WARNING logged, no exception), `test_emit_fail_safe` (patched logger raises, `emit()` does not propagate), `test_emit_json_serializable` (output is valid JSON via `json.loads`) — AC-A12(c)
- [ ] T028 [P] Create `tests/e2e/test_observability_wiring.py` — boot full stack with `MetricsCollector` + `ObservabilityEventLogger` (no live API, use existing mock adapters); dispatch one tool call through `PermissionPipeline` → `ToolExecutor` → mock adapter; assert `tool.call_count`, `permission.decision_count`, `llm.input_tokens` all non-zero; assert `kosmos.events` logger received at least one valid JSON line (plan.md § 7.5)
- [ ] T029 Run `uv run pytest tests/` and confirm all tests pass (no regressions in existing permissions, recovery, llm, cli suites)
- [ ] T030 Run `uv run ruff check src/ tests/` and fix all lint issues
- [ ] T031 Run `uv run ruff format --check src/ tests/` and fix all format issues

**Checkpoint**: Full green CI. All 12 acceptance criteria from spec.md AC-A1 through AC-A12 validated.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Foundation)**: No dependencies — can start immediately
- **Phase 2 (LLM, US3)**: Depends on T001–T003 (Phase 1 complete); `ObservabilityEventLogger` must exist before `LLMClient` can use it
- **Phase 3 (Permission Pipeline, US2)**: Depends on T001–T003 (Phase 1 complete); independent of Phase 2
- **Phase 4 (Tool + Recovery Events, US2 continued)**: Depends on T001–T003 (Phase 1 complete); independent of Phases 2 and 3
- **Phase 5 (REPL command, US1)**: Depends on T001–T003 (Phase 1 complete); independent of Phases 2–4; `MetricsCollector` is already in `src/kosmos/observability/metrics.py`
- **Phase 6 (Startup wiring)**: Depends on Phases 2–5 all complete (all subsystems must have the new constructor params)
- **Phase 7 (Testing and Validation)**: T027 (EventLogger tests) depends on Phase 1 only and can run in parallel with Phases 2–5. T028 (E2E) depends on Phase 6. T029–T031 depend on all source changes complete.

### User Story Dependencies

- **US3 (LLM metrics, Phase 2)**: Requires Phase 1 foundation — no dependency on US1 or US2
- **US2 (Permission + Tool + Recovery events, Phases 3–4)**: Requires Phase 1 foundation — no dependency on US1 or US3
- **US1 (/metrics command, Phase 5)**: Requires Phase 1 foundation only — no dependency on US2 or US3 (reads from `MetricsCollector` which already exists)
- **All stories integrate at Phase 6** (startup wiring)

### Parallel Opportunities

- T002 and T003 can run in parallel (different files)
- After Phase 1: Phases 2, 3, 4, and 5 can ALL run in parallel (entirely different files)
- T004 (LLM test file) and T009 (permission test file) and T015/T016 (tool/recovery test files) and T019 (REPL test file) and T027 (EventLogger test file) — all on different files, fully parallel
- T005 (UsageTracker), T006 (LLMClient init), T017 (ToolExecutor), T018 (RecoveryExecutor), T010 (PermissionPipeline init), T020 (models.py), T021 (repl.py init) — all on different files, fully parallel
- T024 and T027 can run in parallel (T024 is read-only exploration)
- T030 and T031 can run in parallel (different lint/format checks)

---

## Parallel Example: Phases 2–5 after Foundation

```bash
# After Phase 1 complete, all four user story phases in parallel:
Agent A (Sonnet): "Phase 2 — LLM instrumentation (T004–T008) in src/kosmos/llm/"
Agent B (Sonnet): "Phase 3 — PermissionPipeline instrumentation (T009–T014) in src/kosmos/permissions/"
Agent C (Sonnet): "Phase 4 — ToolExecutor + RecoveryExecutor events (T015–T018)"
Agent D (Sonnet): "Phase 5 — /metrics REPL command (T019–T023) in src/kosmos/cli/"
```

## Parallel Example: Phase 7 Test Files

```bash
# All test-file creation tasks are independent:
Task: "Create tests/observability/test_event_logger.py (T027)"
Task: "Create tests/llm/test_metrics_integration.py (T004)"
Task: "Create tests/permissions/test_pipeline_metrics.py (T009)"
Task: "Create tests/cli/test_metrics_command.py (T019)"
```

---

## Implementation Strategy

### MVP First (US3 + US1: visible token metrics + /metrics command)

1. Complete Phase 1: Foundation (T001–T003)
2. Complete Phase 2: LLM instrumentation (T004–T008)
3. Complete Phase 5: `/metrics` command (T019–T023)
4. Complete Phase 6 partial: wire `LLMClient` + `REPLLoop` in `app.py`
5. **STOP and VALIDATE**: Run KOSMOS, issue one query, type `/metrics` — see `llm.input_tokens` and `llm.call_duration_ms`
6. Add Phase 3 (permission metrics) + Phase 4 (event emission) for full AC-A12 coverage

### Parallel Agent Team Strategy

With Agent Teams (Sonnet):
1. **Lead**: Complete Phase 1 Foundation (T001–T003) — shared dependency
2. **Agent A**: Phase 2 (LLM metrics)
3. **Agent B**: Phase 3 (Permission pipeline metrics + events)
4. **Agent C**: Phase 4 (Tool + Recovery events)
5. **Agent D**: Phase 5 (/metrics REPL command) + T027 (EventLogger tests)
6. **Lead**: Phase 6 (startup wiring) after A–D complete, then Phase 7 validation

---

## Notes

- Total tasks: **31**
- Phase 1 (Foundation): 3 tasks (T001–T003)
- Phase 2 (US3 — LLM metrics): 5 tasks (T004–T008)
- Phase 3 (US2 — Permission pipeline): 6 tasks (T009–T014)
- Phase 4 (US2 — Tool + Recovery events): 4 tasks (T015–T018)
- Phase 5 (US1 — /metrics command): 5 tasks (T019–T023)
- Phase 6 (Startup wiring): 3 tasks (T024–T026)
- Phase 7 (Testing + Validation): 5 tasks (T027–T031)
- Parallel opportunities: 7 groups of [P] tasks across phases
- MVP scope: Phase 1 + Phase 2 + Phase 5 + partial Phase 6 (12 tasks)
- Phase B (OTel export, US4–US5) is deferred per spec.md § Deferred Items — no tasks created here
- All tasks follow `- [ ] [TaskID] [P?] [Story?] Description with file path` format
- No new runtime dependencies in any task (Phase A zero-dep constraint)
