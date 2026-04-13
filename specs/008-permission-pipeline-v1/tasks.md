# Tasks: Permission Pipeline v1 (Layer 3)

**Epic**: #8
**Input**: `specs/008-permission-pipeline-v1/spec.md`, `plan.md`, `data-model.md`
**Prerequisites**: spec.md (approved), plan.md (approved), data-model.md (approved)

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: Which user story this task belongs to
- No new `pyproject.toml` entries — stdlib + pydantic only

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the package skeleton so all subsequent tasks have a valid import tree.

- [ ] T001 Create `src/kosmos/permissions/__init__.py` (empty module marker)
- [ ] T002 Create `src/kosmos/permissions/steps/__init__.py` (empty module marker)
- [ ] T003 Create `tests/permissions/__init__.py` (empty module marker)
- [ ] T004 Create `tests/permissions/conftest.py` with shared fixtures: `make_session_context()`, `make_permission_request()`, `caplog` re-export helper

**Checkpoint**: `python -c "import kosmos.permissions"` succeeds; `uv run pytest tests/permissions/` reports 0 collected (no tests yet, no errors).

---

## Phase 2: Foundational — Models (Blocking prerequisite for all stories)

**Purpose**: All Pydantic v2 data models and enums exist and validate correctly. No pipeline or step logic yet. Every subsequent task imports from this module.

**Warning**: No user story work can begin until T005 is done.

- [ ] T005 Implement `src/kosmos/permissions/models.py` — `AccessTier` enum, `PermissionDecision` enum, `SessionContext`, `PermissionCheckRequest`, `PermissionStepResult`, `AuditLogEntry` (frozen Pydantic v2 models, no `Any`, FR-001–FR-007)
- [ ] T006 [P] Write `tests/permissions/test_models.py` — validate all model fields, frozen enforcement, `AuditLogEntry` has no `arguments_json`, no `Any`, import-time env isolation (SC-010)

**Checkpoint**: `uv run pytest tests/permissions/test_models.py` passes.

---

## Phase 3: User Story 1 — Configuration-based access tier enforcement (P1)

**Goal**: Step 1 checks `AccessTier` against `KOSMOS_DATA_GO_KR_API_KEY` env var; all four tier branches return correct decisions.

**Spec reference**: US-001, US-002 (stub contract), FR-009, FR-010, FR-017, FR-018, FR-019

**Independent test**: `uv run pytest tests/permissions/test_step1_config.py` with env var patched.

- [ ] T007 [P] [US1] Implement `src/kosmos/permissions/steps/step1_config.py` — `check_config(request: PermissionCheckRequest) -> PermissionStepResult` covering all four `AccessTier` branches; reads `KOSMOS_DATA_GO_KR_API_KEY` at call time, strips whitespace, never logs the key value (FR-009, FR-017, FR-018, FR-019)
- [ ] T008 [P] [US1] Write `tests/permissions/test_step1_config.py` — five acceptance scenarios: `public` allows with no env var, `api_key` denies when unset, `api_key` allows when set (key not in log records), `authenticated` denies with correct reason, `restricted` denies with correct reason (SC-001, SC-002, SC-003)

**Checkpoint**: `uv run pytest tests/permissions/test_step1_config.py` passes.

---

## Phase 4: User Story 2 — Stub steps return allow without side effects (P1)

**Goal**: Steps 2–5 are callable no-ops with the correct `PermissionCheckRequest → PermissionStepResult` signature and emit exactly one DEBUG log line each.

**Spec reference**: US-002, FR-010

**Independent test**: `uv run pytest` with log capture asserting one DEBUG line per stub step.

- [ ] T009 [P] [US2] Implement `src/kosmos/permissions/steps/step2_intent.py` — `check_intent(request: PermissionCheckRequest) -> PermissionStepResult` returning `allow` at step 2 with one DEBUG log line (FR-010)
- [ ] T010 [P] [US2] Implement `src/kosmos/permissions/steps/step3_params.py` — `check_params(request: PermissionCheckRequest) -> PermissionStepResult` returning `allow` at step 3 with one DEBUG log line (FR-010)
- [ ] T011 [P] [US2] Implement `src/kosmos/permissions/steps/step4_authn.py` — `check_authn(request: PermissionCheckRequest) -> PermissionStepResult` returning `allow` at step 4 with one DEBUG log line (FR-010)
- [ ] T012 [P] [US2] Implement `src/kosmos/permissions/steps/step5_terms.py` — `check_terms(request: PermissionCheckRequest) -> PermissionStepResult` returning `allow` at step 5 with one DEBUG log line (FR-010)
- [ ] T013 [P] [US2] Write stub test coverage inside `tests/permissions/test_models.py` (or a dedicated `test_stubs.py`) — assert each stub returns `PermissionDecision.allow`, correct `step` field, and exactly one DEBUG record for any tool call (SC-004)

**Checkpoint**: All four stubs callable; log capture confirms exactly one DEBUG line per stub; `uv run pytest` for these tests passes.

---

## Phase 5: User Story 3 — Sandboxed execution context (P1)

**Goal**: Step 6 runs the adapter inside an isolated credential context, catches exceptions as deny results, and fully restores `os.environ` after each call.

**Spec reference**: US-003, US-007 (key injection), FR-011, FR-017

**Independent test**: `uv run pytest tests/permissions/test_step6_sandbox.py` with mock executor.

- [ ] T014 [P] [US3] Implement `src/kosmos/permissions/steps/step6_sandbox.py` — `run_sandboxed(request: PermissionCheckRequest, executor: ToolExecutor) -> ToolResult` coroutine; `_credential_scope(access_tier)` context manager that removes all `KOSMOS_*` vars from `os.environ`, yields credentials dict with only the tool's key, restores env in `finally`; catches all adapter exceptions as `PermissionDecision.deny` with `reason="execution_error"` (FR-011)
- [ ] T015 [P] [US3] Write `tests/permissions/test_step6_sandbox.py` — three scenarios: credential isolation (no other `KOSMOS_*` visible), exception capture returns deny (SC-005), env fully restored after call (no leakage between calls)

**Checkpoint**: `uv run pytest tests/permissions/test_step6_sandbox.py` passes.

---

## Phase 6: User Story 4 — Audit log on every invocation (P1)

**Goal**: Step 7 writes a structured `AuditLogEntry` at the correct log level; `arguments_json` is never present; step 7 itself never propagates an exception.

**Spec reference**: US-004, FR-012, NFR-004

**Independent test**: `uv run pytest tests/permissions/test_step7_audit.py` with `caplog`.

- [ ] T016 [P] [US4] Implement `src/kosmos/permissions/audit.py` — `AuditLogger` class with `log(entry: AuditLogEntry) -> None`; uses `getLogger("kosmos.permissions.audit")`; `INFO` for `outcome in ("success", "failure")`, `WARNING` for `outcome == "denied"`; swallows own exceptions with fallback `logging.error()` to root logger (FR-012, NFR-004, US-004 edge case)
- [ ] T017 [P] [US4] Implement `src/kosmos/permissions/steps/step7_audit.py` — `write_audit(request: PermissionCheckRequest, deciding_step: PermissionStepResult, outcome: Literal["success", "failure", "denied"], tool_result: ToolResult | None) -> None`; constructs `AuditLogEntry` from inputs and delegates to `AuditLogger.log()` (FR-012)
- [ ] T018 [P] [US4] Write `tests/permissions/test_step7_audit.py` — assert all required fields present, `arguments_json` absent, correct log levels for approved vs denied calls, fallback behavior when logger raises (SC-006)

**Checkpoint**: `uv run pytest tests/permissions/test_step7_audit.py` passes.

---

## Phase 7: User Story 5 — Bypass-immune enforcement (P1)

**Goal**: `BYPASS_IMMUNE_RULES` is a frozen constant; personal-data citizen-id mismatch always denies; `is_bypass_mode=True` emits a WARNING but does not override immune rules.

**Spec reference**: US-006, FR-014, FR-015, FR-016

**Independent test**: `uv run pytest tests/permissions/test_bypass.py`.

- [ ] T019 [P] [US5] Implement `src/kosmos/permissions/bypass.py` — `BYPASS_IMMUNE_RULES: frozenset[str]` module constant (not configurable); `check_bypass_immune(request: PermissionCheckRequest) -> PermissionStepResult | None` returning a deny result if `is_personal_data=True` and `citizen_id` in `arguments_json` does not match `session_context.citizen_id`; emits WARNING when `is_bypass_mode=True` before the check (FR-014, FR-015, FR-016)
- [ ] T020 [P] [US5] Write `tests/permissions/test_bypass.py` — three scenarios: citizen_id mismatch denies even with `is_bypass_mode=True` (SC-008), `BYPASS_IMMUNE_RULES` is a frozenset and raises `AttributeError` on mutation attempt, bypass attempt emits WARNING log

**Checkpoint**: `uv run pytest tests/permissions/test_bypass.py` passes.

---

## Phase 8: User Story 6 — Fail-closed on any step error (P1)

**Goal**: Any unexpected exception in steps 1–6 causes the pipeline to return `PermissionDecision.deny` with `reason="internal_error"`; the executor is never called when a pre-execution step fails.

**Spec reference**: US-005, FR-013

Note: This story is tested as part of `test_pipeline.py` in Phase 9. No isolated step-level test is needed here because the fail-closed behavior is a runner-level concern, not a per-step concern. The monkey-patch test (SC-007) belongs in `test_pipeline.py`.

---

## Phase 9: User Story 7 — Pipeline orchestrator + ToolExecutor integration (P2)

**Goal**: `PermissionPipeline.run()` assembles the full 7-step gauntlet, wraps `ToolExecutor`, and is the single entry point for Layer 1.

**Spec reference**: US-008, FR-008, FR-013, FR-020, FR-021, FR-022

**Dependencies**: All Phases 3–8 must be complete before this phase begins.

**Independent test**: `uv run pytest tests/permissions/test_pipeline.py`.

- [ ] T024 Extend `ToolResult.error_type` Literal in `src/kosmos/tools/models.py` — add `"permission_denied"` to the existing `Literal["validation", "rate_limit", "not_found", "execution", "schema_mismatch"]` union (Decision 4 from plan.md; additive, no existing tests broken). **Must complete before T021/T023 which construct ToolResult with this value.**
- [ ] T021 Implement `src/kosmos/permissions/pipeline.py` — `PermissionPipeline(executor: ToolExecutor, registry: ToolRegistry)` class; `_AUTH_TYPE_TO_ACCESS_TIER` lookup dict; `_PRE_EXECUTION_STEPS` list `[step1_config, step2_intent, step3_params, step4_authn, step5_terms]`; `run(tool_id, arguments_json, session_context) -> ToolResult` coroutine that: checks bypass immune first, runs steps 1–5 stopping at first deny/escalate (treating escalate as deny), wraps each step in try/except for fail-closed (FR-013), calls `run_sandboxed` for step 6, always calls `write_audit` for step 7, uses `inspect.isawaitable()` dispatch so sync/async steps are both supported (FR-008, FR-020, FR-021, FR-022)
- [ ] T022 [P] Update `src/kosmos/permissions/__init__.py` — export `PermissionPipeline`, `AccessTier`, `PermissionDecision`, `SessionContext` at package level
- [ ] T023 [P] Write `tests/permissions/test_pipeline.py` — end-to-end gauntlet: allow path returns `ToolResult(success=True)`, deny at step 1 returns `ToolResult(error_type="permission_denied")` and skips steps 2–6 (SC-002), step 7 always fires (SC-009 audit always fires variant), step 1 exception returns deny (SC-007), `is_bypass_mode=True` still enforces immune rules (SC-008), import-time env isolation confirmed (SC-010)

**Checkpoint**: `uv run pytest tests/permissions/test_pipeline.py` passes.

---

## Phase 10: Polish — Integration with query engine

**Purpose**: Wire `PermissionPipeline` into `dispatch_tool_calls()`.

**Dependencies**: Phase 9 must be complete (T024 already done in Phase 9).

- [ ] T025 Add optional fields to `QueryContext` in `src/kosmos/engine/models.py` — `permission_pipeline: PermissionPipeline | None = None` and `session_context: SessionContext | None = None` (additive; no existing callers break because fields default to `None`)
- [ ] T026 Update `dispatch_tool_calls()` in `src/kosmos/engine/query.py` — when `ctx.permission_pipeline` is not `None` and `ctx.session_context` is not `None`, replace `tool_executor.dispatch(tc.function.name, tc.function.arguments)` with `permission_pipeline.run(tc.function.name, tc.function.arguments, session_context)`; fall back to existing executor path when pipeline is absent (additive; backward-compatible)
- [ ] T027 [P] Run full test suite to confirm no regressions — `uv run pytest` (all existing tests for engine, tools, LLM layers must still pass; zero `@pytest.mark.live` tests in `tests/permissions/`)

**Checkpoint**: `uv run pytest` (full suite) passes. `uv run pytest tests/permissions/` reports all green with zero live API calls.

---

## Dependency Graph

```
T001 → T002 → T003 → T004   (Phase 1 — sequential setup)
                         ↓
                       T005   (Phase 2 — models, blocking)
                         ↓
           ┌─────────────┼──────────────────────────────────────┐
           │             │                                      │
          T006          T007+T008    T009–T013    T014+T015    T016–T018    T019+T020
     (model tests)   (Phase 3)      (Phase 4)    (Phase 5)    (Phase 6)    (Phase 7)
           │             │             │             │             │             │
           └─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
                                         ↓  (all Phases 3–8 complete)
                                    T024 (Phase 9 — ToolResult Literal extension, MUST precede T021/T023)
                                       ↓
                                    T021 (Phase 9 — pipeline orchestrator)
                                       ↓
                                    T022, T023 (parallel within Phase 9)
                                       ↓
                                    T025, T026 (parallel within Phase 10)
                                       ↓
                                    T027 (full suite regression check)
```

---

## Parallel Execution Examples

### Agent Team split: Phases 3–7 can run concurrently after Phase 2 completes

```
Agent A (Backend — step implementation):
  T007  src/kosmos/permissions/steps/step1_config.py
  T009  src/kosmos/permissions/steps/step2_intent.py
  T010  src/kosmos/permissions/steps/step3_params.py
  T011  src/kosmos/permissions/steps/step4_authn.py
  T012  src/kosmos/permissions/steps/step5_terms.py
  T014  src/kosmos/permissions/steps/step6_sandbox.py
  T016  src/kosmos/permissions/audit.py
  T017  src/kosmos/permissions/steps/step7_audit.py
  T019  src/kosmos/permissions/bypass.py

Agent B (Tests):
  T006  tests/permissions/test_models.py
  T008  tests/permissions/test_step1_config.py
  T013  test_stubs coverage
  T015  tests/permissions/test_step6_sandbox.py
  T018  tests/permissions/test_step7_audit.py
  T020  tests/permissions/test_bypass.py
```

After both agents complete Phases 3–7:

```
Lead (Phase 9 + 10):
  T024  src/kosmos/tools/models.py  (Literal extension — FIRST, before T021/T023)
  T021  src/kosmos/permissions/pipeline.py
  T022  src/kosmos/permissions/__init__.py
  T023  tests/permissions/test_pipeline.py
  T025  src/kosmos/engine/models.py (QueryContext optional fields)
  T026  src/kosmos/engine/query.py  (dispatch_tool_calls wiring)
  T027  full uv run pytest
```

---

## Task Count Summary

| Phase | Tasks | Parallel-safe | User story |
|-------|-------|---------------|------------|
| Phase 1 — Setup | T001–T004 | None (sequential) | — |
| Phase 2 — Models | T005–T006 | T006 [P] | — |
| Phase 3 — US1 Config enforcement | T007–T008 | Both [P] | US1 |
| Phase 4 — US2 Stub steps | T009–T013 | T009–T013 all [P] | US2 |
| Phase 5 — US3 Sandbox | T014–T015 | Both [P] | US3 |
| Phase 6 — US4 Audit log | T016–T018 | All [P] | US4 |
| Phase 7 — US5 Bypass immune | T019–T020 | Both [P] | US5 |
| Phase 8 — US6 Fail-closed | — (tested in Phase 9) | — | US6 |
| Phase 9 — US7/US8 Pipeline | T024, T021–T023 | T022, T023 [P] | US7/US8 |
| Phase 10 — Integration | T025–T027 | T025, T026 [P] | — |

**Total tasks**: 27
**Parallel-safe tasks**: 20 of 27
**Sequential gates**: Phase 1 → Phase 2 → (Phases 3–7 parallel) → Phase 9 → Phase 10
