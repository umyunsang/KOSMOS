# Tasks: Context Assembly v1 (Layer 5)

**Input**: `specs/009-context-assembly-v1/` (spec.md, plan.md, data-model.md, research.md)
**Epic**: #9 — Context Assembly v1 (Layer 5)
**Branch**: `feat/009-context-assembly-v1`

---

## Phase 1: Setup (Package Structure)

**Purpose**: Create the `src/kosmos/context/` sub-package and `tests/context/` directory.
No source code yet — just the file system skeleton that all later tasks populate.

- [ ] T001 Create `src/kosmos/context/__init__.py` with empty public export list
- [ ] T002 Create `tests/context/__init__.py` to make test directory a package

**Checkpoint**: `src/kosmos/context/` and `tests/context/` exist as importable packages.

---

## Phase 2: Foundational Models (Blocking)

**Purpose**: Lay down all five Pydantic v2 models and their validators. Every user story
phase depends on these types being present and correct. No user story work begins until
this phase is complete.

- [ ] T003 Implement `SystemPromptConfig`, `ContextLayer`, `ContextBudget`, `AssembledContext` frozen models with all field validators and `ContextBudget.from_estimate()` class method in `src/kosmos/context/models.py`
- [ ] T004 Add `active_situational_tools: set[str] = field(default_factory=set)` to `QueryState` dataclass in `src/kosmos/engine/models.py`
- [ ] T005 Write unit tests covering frozen constraints, non-empty validators, `ContextBudget` threshold logic, and `ContextLayer` role/layer_name invariant in `tests/context/test_models.py`

**Completion gate**: `uv run pytest tests/context/test_models.py` passes; `AssembledContext` can be constructed with only `system_layer` populated; `QueryState` construction without `active_situational_tools` argument continues to work.

---

## Phase 3: User Story 1 — Stable System Prompt Assembly (Priority: P1)

**Goal**: `ContextBuilder.build_system_message()` returns a deterministic, cache-stable
`ChatMessage(role='system')` containing all four mandatory policy sections (FR-009).

**Independent Test**: Construct `ContextBuilder` with a `SystemPromptConfig`, call
`build_system_message()` twice, assert both calls return identical content.

### Implementation for User Story 1

- [ ] T006 [US1] Implement `SystemPromptAssembler` with the four mandatory sections (platform identity, language policy, tool-use policy, personal-data reminder) in `src/kosmos/context/system_prompt.py`
- [ ] T007 [US1] Implement `ContextBuilder.__init__()` accepting `config: SystemPromptConfig | None = None`, caching the assembled system message on first call, in `src/kosmos/context/builder.py`
- [ ] T008 [US1] Implement `ContextBuilder.build_system_message()` delegating to `SystemPromptAssembler`, returning cached `ChatMessage` on subsequent calls, in `src/kosmos/context/builder.py`
- [ ] T009 [US1] Update `src/kosmos/context/__init__.py` to export `ContextBuilder`, `SystemPromptConfig`, `ContextLayer`, `ContextBudget`, `AssembledContext`
- [ ] T010 [P] [US1] Write determinism test (1,000 consecutive calls, same config) and section-presence assertions in `tests/context/test_system_prompt.py`
- [ ] T011 [P] [US1] Write `build_system_message()` unit tests: correct role, all sections present, identical across instances with same config, in `tests/context/test_builder.py`

**Completion gate**: SC-001 passes. `build_system_message()` is deterministic and returns `role='system'`.

---

## Phase 4: User Story 3 — Tool Schema Injection with Cache Partitioning (Priority: P1)

**Goal**: `build_assembled_context()` produces `AssembledContext.tool_definitions` with
core tools sorted by id in the prefix and active situational tools sorted by id in the
suffix (FR-004, FR-005). This phase completes before US2 because it is a pure model
computation with no dependency on attachment logic.

**Independent Test**: Register 3 core tools and 2 situational tools, call
`build_assembled_context()`, assert all core tools appear before all situational tools
sorted by `id`.

### Implementation for User Story 3

- [ ] T012 [US3] Implement `ContextBuilder.build_assembled_context()` stub: calls `build_system_message()`, builds `tool_definitions` via `registry.export_core_tools_openai()` + active situational tools sorted by `id`, returns minimal `AssembledContext` (no attachment, no budget yet), in `src/kosmos/context/builder.py`
- [ ] T013 [P] [US3] Write tool ordering tests: 3 core + 2 situational verify `[core_a, core_b, core_c, sit_a, sit_b]` regardless of registration order; empty situational edge case; all-situational-tools WARNING log assertion, in `tests/context/test_builder.py`

**Completion gate**: SC-002 passes. Cache-partitioning acceptance scenarios for US3 pass.

---

## Phase 5: User Story 2 — Per-Turn Attachment Injection (Priority: P1)

**Goal**: `build_turn_attachment()` returns `ChatMessage(role='user')` containing
resolved tasks, in-flight state, API health warnings, and auth expiry context.
Returns `None` for empty sessions (turn 0, no state).

**Independent Test**: Construct `QueryState` with two resolved tasks and one in-flight
tool ID, call `build_turn_attachment()`, assert the content lists both tasks and the
pending tool.

### Implementation for User Story 2

- [ ] T014 [US2] Implement `AttachmentCollector` with private section methods for resolved tasks, in-flight tool state, API health, and auth expiry warning in `src/kosmos/context/attachments.py`
- [ ] T015 [US2] Implement `ContextBuilder.build_turn_attachment()` delegating to `AttachmentCollector`, returning `None` for empty sessions, in `src/kosmos/context/builder.py`
- [ ] T016 [P] [US2] Write attachment unit tests covering US2 scenarios: empty session returns None; two resolved tasks listed; degraded API warning; auth expiry warning (< 60 seconds), in `tests/context/test_attachments.py`

**Completion gate**: US2 acceptance scenarios 1–4 pass. Empty-session `None` return verified.

---

## Phase 6: User Story 5 — Reminder Cadence (Priority: P3)

**Goal**: `build_turn_attachment()` injects a structured reminder block when
`state.turn_count % config.reminder_cadence == 0` and `state.turn_count > 0`
(FR-008). Does not fire on turn 0 or non-cadence turns.

**Independent Test**: `QueryState.turn_count=10`, `reminder_cadence=5` — reminder block
present. `turn_count=11` — reminder block absent.

### Implementation for User Story 5

- [ ] T017 [US5] Add reminder section logic to `AttachmentCollector`: inject reminder listing `resolved_tasks` and pending in-flight state when cadence condition is met in `src/kosmos/context/attachments.py`
- [ ] T018 [P] [US5] Write reminder cadence tests: turn=10 cadence=5 includes reminder; turn=11 cadence=5 no reminder; cadence=1 fires every turn; turn=0 never fires, in `tests/context/test_attachments.py`

**Completion gate**: US5 acceptance scenarios 1–2 pass. Cadence=1 edge case passes.

---

## Phase 7: User Story 4 — Context Budget Guard (Priority: P2)

**Goal**: `build_assembled_context()` computes `ContextBudget` using
`engine.tokens.estimate_tokens()`, populates `is_near_limit` / `is_over_limit`,
and the `QueryEngine` yields `StopReason.api_budget_exceeded` when over limit.

**Independent Test**: Construct `AssembledContext` with estimated tokens above
`hard_limit_tokens`, assert `context_budget.is_over_limit` is `True`.

### Implementation for User Story 4

- [ ] T019 [US4] Implement `BudgetEstimator` with `estimate_layer_tokens()` and `estimate_tool_defs_tokens()` functions producing `ContextBudget` via `ContextBudget.from_estimate()` in `src/kosmos/context/budget.py`
- [ ] T020 [US4] Wire `BudgetEstimator` into `ContextBuilder.build_assembled_context()`: sum tokens across all layers and tool definitions, produce complete `AssembledContext.budget`, in `src/kosmos/context/builder.py`
- [ ] T021 [US4] Add `build_assembled_context()` budget-near-limit WARNING log in `src/kosmos/context/builder.py`
- [ ] T022 [P] [US4] Write budget unit tests covering US4 scenarios: over-limit fires, near-limit logs WARNING, within-limit both False, threshold boundary conditions, in `tests/context/test_budget.py`

**Completion gate**: SC-003 passes. All three US4 acceptance scenarios pass.

---

## Phase 8: User Story 6 — QueryEngine Integration (Priority: P1)

**Goal**: Replace `_DEFAULT_SYSTEM_PROMPT` and `system_prompt: str | None` parameter
in `QueryEngine` with `context_builder: ContextBuilder | None`. Insert
`build_turn_attachment()` call in `run()` before the user message is appended.
Handle `is_over_limit` to yield `StopReason.api_budget_exceeded`.

**Independent Test**: Construct `QueryEngine` without `system_prompt`, run one turn,
assert `state.messages[0].content` matches `ContextBuilder.build_system_message()` output.

### Implementation for User Story 6

- [ ] T023 [US6] Replace `system_prompt: str | None` parameter with `context_builder: ContextBuilder | None` in `QueryEngine.__init__()`, remove `_DEFAULT_SYSTEM_PROMPT` constant, initialize `QueryState.messages` with `[context_builder.build_system_message()]`, in `src/kosmos/engine/engine.py`
- [ ] T024 [US6] Insert `context_builder.build_turn_attachment(state, api_health=None)` call in `QueryEngine.run()` before appending the user message; prepend attachment `ChatMessage` if non-None; yield `api_budget_exceeded` when `is_over_limit` is True, in `src/kosmos/engine/engine.py`
- [ ] T025 [P] [US6] Write integration test: engine without `system_prompt` produces history[0] matching `build_system_message()` output; budget exceeded scenario yields stop event, in `tests/context/test_engine_integration.py`
- [ ] T026 [P] [US6] Run full engine regression suite to verify no existing tests break: `uv run pytest tests/engine/` must be 100% green

**Completion gate**: SC-004 passes. `tests/engine/` regression-free. `QueryEngine` construction without `system_prompt` argument works unchanged.

---

## Phase 9: Polish and Performance

**Purpose**: Performance benchmark, edge-case hardening, and final cross-cutting concerns.

- [ ] T027 [P] Write `pytest-benchmark` assertion that `build_assembled_context()` completes in under 10 ms with 50 resolved tasks and 20 registered tools (SC-006) in `tests/context/test_builder.py`
- [ ] T028 [P] Write SC-001 determinism stress test: 1,000 consecutive `build_system_message()` calls assert identical content (add to `tests/context/test_system_prompt.py`)
- [ ] T029 [P] Write SC-005 reminder count test: 50-turn session with cadence=5 produces exactly 10 reminder blocks (add to `tests/context/test_attachments.py`)
- [ ] T030 Verify all new tests omit `@pytest.mark.live` marker and confirm CI-safe (SC-007) — inspect `tests/context/`
- [ ] T031 [P] Verify `all_tools_situational` WARNING log fires when no core tools are registered — add assertion to `tests/context/test_builder.py`
- [ ] T032 Add `pytest-benchmark` to `pyproject.toml` dev dependencies (if not already present)

**Completion gate**: SC-001 through SC-007 all pass. `uv run pytest tests/context/` is 100% green. `uv run pytest tests/engine/` remains 100% green.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    └── Phase 2 (Foundational Models) ← blocks everything below
            ├── Phase 3 (US1: System Prompt)
            │       └── Phase 4 (US3: Tool Schema Injection)  ← depends on builder.py skeleton from US1
            ├── Phase 5 (US2: Attachments)                    ← depends on models only
            │       └── Phase 6 (US5: Reminder Cadence)       ← extends attachments.py
            ├── Phase 7 (US4: Budget Guard)                   ← depends on models + builder stub
            └── Phase 8 (US6: Engine Integration)             ← depends on all prior phases complete
                    └── Phase 9 (Polish)
```

### Within-Phase Parallelism

Tasks marked `[P]` within the same phase touch different files and can run simultaneously:

- **Phase 3**: T010 and T011 are both test files — parallel with T006–T009 implementation
- **Phase 4**: T013 test file is parallel with T012 implementation
- **Phase 5**: T016 test file is parallel with T014–T015 implementation
- **Phase 6**: T018 test file is parallel with T017 implementation
- **Phase 7**: T022 test file is parallel with T019–T021 implementation
- **Phase 8**: T025, T026 test tasks are parallel with T023–T024 implementation
- **Phase 9**: T027, T028, T029, T030, T031 are all parallel (different test files or read-only inspection)

### Cross-Phase Parallelism

Once Phase 2 is complete, US1 (Phase 3) and US2 (Phase 5) can start in parallel —
they touch different files (`system_prompt.py` vs `attachments.py`). US4 (Phase 7)
can also start in parallel once the `builder.py` stub from Phase 3 exists.

---

## Parallel Execution Examples

### Example A: After Phase 2 completes, three Teammates start in parallel

```
Teammate A — US1 (Phase 3):
  src/kosmos/context/system_prompt.py  (T006)
  src/kosmos/context/builder.py        (T007, T008)
  tests/context/test_system_prompt.py  (T010)
  tests/context/test_builder.py        (T011)

Teammate B — US2 (Phase 5):
  src/kosmos/context/attachments.py    (T014)
  src/kosmos/context/builder.py        (T015) ← after Teammate A's builder.py is merged
  tests/context/test_attachments.py    (T016)

Teammate C — US4 (Phase 7):
  src/kosmos/context/budget.py         (T019)
  src/kosmos/context/builder.py        (T020, T021) ← after Teammate A's builder.py is merged
  tests/context/test_budget.py         (T022)
```

Note: `builder.py` is edited by multiple phases sequentially within each phase.
File-level coupling means T015 (Phase 5) waits for T008 (Phase 3) and T020 (Phase 7)
waits for T012 (Phase 4). Coordinate merges before starting the wiring steps.

### Example B: Phase 9 Polish — all parallel

```
Task: pytest-benchmark test (T027) — tests/context/test_builder.py
Task: determinism stress test (T028) — tests/context/test_system_prompt.py
Task: reminder count test (T029) — tests/context/test_attachments.py
Task: CI-safe marker audit (T030) — tests/context/ (read-only)
Task: all-situational WARNING test (T031) — tests/context/test_builder.py
```

---

## Task Count Summary

| Phase | Tasks | Parallel-eligible | User Story |
|-------|-------|-------------------|------------|
| Phase 1: Setup | 2 | 0 | — |
| Phase 2: Foundational | 3 | 0 | — |
| Phase 3: US1 System Prompt | 6 | 2 | US1 |
| Phase 4: US3 Tool Partitioning | 2 | 1 | US3 |
| Phase 5: US2 Attachments | 3 | 1 | US2 |
| Phase 6: US5 Reminder Cadence | 2 | 1 | US5 |
| Phase 7: US4 Budget Guard | 4 | 1 | US4 |
| Phase 8: US6 Engine Integration | 4 | 2 | US6 |
| Phase 9: Polish | 6 | 5 | — |
| **Total** | **32** | **13** | — |

- **Total tasks**: 32
- **Parallel-eligible**: 13 (marked `[P]`)
- **Sequential-only**: 19
- **P1 user stories**: US1, US2, US3, US6 (Phases 3–5, 8)
- **P2 user story**: US4 (Phase 7)
- **P3 user story**: US5 (Phase 6)
- **New source files**: 6 (`context/__init__.py`, `models.py`, `builder.py`, `system_prompt.py`, `attachments.py`, `budget.py`)
- **Modified source files**: 2 (`engine/engine.py`, `engine/models.py`)
- **New test files**: 7 (`tests/context/__init__.py`, `test_models.py`, `test_builder.py`, `test_system_prompt.py`, `test_attachments.py`, `test_budget.py`, `test_engine_integration.py`)
