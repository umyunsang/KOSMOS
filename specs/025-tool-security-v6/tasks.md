---
description: "Task list for Tool Template Security Spec V6 — auth_type ↔ auth_level consistency invariant"
---

# Tasks: Tool Template Security Spec V6 — `auth_type` ↔ `auth_level` consistency invariant

**Input**: Design documents from `/specs/025-tool-security-v6/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/v6-error-contract.md ✅, quickstart.md ✅

**Tests**: Included. V6 extends the V1–V5 chain that was landed with TDD in PR #653; this feature follows the same pattern (fail-first tests, then implementation). Test requirements are defined in FR-045.

**Organization**: Tasks are grouped by user story (US1 model validator — P1; US2 registry backstop — P2; US3 spec-doc v1.1 — P3). Most tasks are parallel-safe; only the registry-wide regression scan depends on US1 + US2 both landing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single-project layout per plan.md:
- Source: `src/kosmos/tools/` and `src/kosmos/security/`
- Tests: `tests/tools/`
- Docs: `docs/security/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify baseline is green before making any V6 change. No new project scaffolding needed — all infra exists.

- [ ] T001 Run `uv run pytest tests/tools/ -v` from repo root; confirm 0 failures (baseline green snapshot before V6 work). Record the test count in the implementation PR body.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Declare the canonical `_AUTH_TYPE_LEVEL_MAPPING` module constant that both US1 (validator) and US2 (backstop) will import. This is the single source of truth required by FR-040 and the anti-drift guarantee described in data-model.md §2.3.

**⚠️ CRITICAL**: US1 and US2 cannot proceed until T002 lands.

- [ ] T002 Add the `_AUTH_TYPE_LEVEL_MAPPING: Final[dict[str, frozenset[str]]]` module-level constant to `src/kosmos/tools/models.py` (near the top of the module, next to other module-level constants). Content per data-model.md §1: `{"public": frozenset({"public", "AAL1"}), "api_key": frozenset({"AAL1", "AAL2", "AAL3"}), "oauth": frozenset({"AAL1", "AAL2", "AAL3"})}`. Add a short module-level docstring line naming FR-039/FR-040/FR-042 as the invariant owners. Do NOT wire it into any validator yet.

**Checkpoint**: Foundation ready — US1 and US2 can start in parallel.

---

## Phase 3: User Story 1 — Model validator rejects inconsistent auth triples (Priority: P1) 🎯 MVP

**Goal**: Every `GovAPITool` construction with a `(auth_type, auth_level)` pair outside the canonical mapping fails at pydantic `@model_validator(mode="after")` time with an error message naming both fields and the allowed set. Every allowed pair succeeds. All 6 existing adapters continue to construct without change.

**Independent Test**: `uv run pytest tests/tools/test_gov_api_tool_extensions.py -k V6 -v` — 100% pass, covering all 8 allowed pairs (positive) and all 4 disallowed pairs (negative), plus the unknown-`auth_type` fail-closed branch.

### Tests for User Story 1 (write FIRST; they MUST FAIL before T007 lands) ⚠️

- [ ] T003 [P] [US1] Add a parametrized positive test `test_v6_allows_compliant_auth_pairs` to `tests/tools/test_gov_api_tool_extensions.py`, enumerating all 8 allowed `(auth_type, auth_level)` pairs per data-model.md §1 ("Derived sets — Allowed pairs"). Build each via `GovAPITool(...)` using a minimal fixture and assert construction succeeds. Skip `(api_key|oauth, public)` — these require `requires_auth=False` (V5) and auth_level='public', which V5 already governs; they are disallowed by V6 and belong in T004.
- [ ] T004 [P] [US1] Add a parametrized negative test `test_v6_rejects_disallowed_auth_pairs` to `tests/tools/test_gov_api_tool_extensions.py` covering all 4 disallowed pairs: `(public, AAL2)`, `(public, AAL3)`, `(api_key, public)`, `(oauth, public)`. Assert `ValidationError` is raised, and assert the underlying error message contains substrings `"V6 violation"`, `"auth_type"`, `"auth_level"`, and every element of the allowed set for the offending `auth_type` (per contracts/v6-error-contract.md §Contract 1).
- [ ] T005 [P] [US1] Add test `test_v6_fail_closed_on_unknown_auth_type` to `tests/tools/test_gov_api_tool_extensions.py` that exercises FR-048 by constructing a `GovAPITool` via `model_construct` with an `auth_type` outside the Literal set (e.g., `"future_auth"`), then calling the validator directly or re-validating, and asserting the fail-closed error message (`"V6 violation (FR-048): unknown auth_type"`) surfaces. This defends against the case where the `auth_type` Literal is later widened without a matching mapping update.
- [ ] T006 [P] [US1] Add test `test_v6_does_not_regress_v5_interaction` to `tests/tools/test_gov_api_tool_extensions.py` covering the edge case from data-model.md §1.3: `(public, public, requires_auth=False)` passes; `(public, public, requires_auth=True)` still fails with a V5 error (not V6); `(public, AAL1, requires_auth=True)` — the MVP-meta-tool pattern — passes both V5 and V6.

### Implementation for User Story 1

- [ ] T007 [US1] Extend `GovAPITool._validate_security_invariants` in `src/kosmos/tools/models.py` by appending a V6 block after V5 (per data-model.md §3.2). Logic: `allowed = _AUTH_TYPE_LEVEL_MAPPING.get(self.auth_type)`; if `allowed is None` raise the FR-048 fail-closed `ValueError` from contracts/v6-error-contract.md §Contract 1 fail-closed variant; else if `self.auth_level not in allowed` raise the main `ValueError` from contracts/v6-error-contract.md §Contract 1 with `sorted(allowed)` formatted deterministically. Preserve the `return self` at the end of the method. Do NOT mutate any field. Run T001's baseline command plus T003–T006 to confirm all 4 new tests pass and no V1–V5 test regresses.

**Checkpoint**: US1 complete. `GovAPITool` model validation enforces V6 at the earliest point. Every existing adapter still constructs without change (verified by T001 re-run; registry-wide scan lives in T014).

---

## Phase 4: User Story 2 — Registry backstop rejects pydantic-bypass misconfigurations (Priority: P2)

**Goal**: `ToolRegistry.register()` independently re-checks V6 against the same `_AUTH_TYPE_LEVEL_MAPPING` constant, rejecting tool objects built via `GovAPITool.model_construct(...)` or mutated post-construction with `object.__setattr__(...)` when the `(auth_type, auth_level)` pair is disallowed. The backstop error is distinguishable from the pydantic error per FR-043.

**Independent Test**: `uv run pytest tests/tools/test_registry_invariant.py -k V6 -v` — 100% pass, covering bypass-negative cases (both `model_construct` and `__setattr__`), bypass-positive cases (`model_construct` with compliant pair must succeed so the backstop is not a blanket deny), and the FR-043 distinguishability assertion.

### Tests for User Story 2 (write FIRST; they MUST FAIL before T012 lands) ⚠️

- [X] T008 [P] [US2] Add test `test_v6_backstop_rejects_model_construct_bypass` to `tests/tools/test_registry_invariant.py`. Build a `GovAPITool` via `model_construct(...)` with `auth_type="public", auth_level="AAL3"` (bypassing pydantic V6), hand to `ToolRegistry().register(tool)`, assert `RegistrationError` is raised and the message matches contracts/v6-error-contract.md §Contract 2 (substrings `"V6 violation"`, `"registry backstop"`, both field names, allowed-levels list).
- [X] T009 [P] [US2] Add test `test_v6_backstop_rejects_setattr_mutation` to `tests/tools/test_registry_invariant.py`. Build a compliant `GovAPITool`, then `object.__setattr__(tool, "auth_level", "AAL2")` while `auth_type` is `"public"`, hand to `register()`, assert the same `RegistrationError` shape.
- [X] T010 [P] [US2] Add test `test_v6_backstop_allows_compliant_model_construct` to `tests/tools/test_registry_invariant.py`. Build via `model_construct(...)` with a compliant pair `(public, AAL1)`, register, assert success. This guards against the backstop becoming a blanket deny-all for bypassed instances (spec.md Edge Case §1).
- [X] T011 [P] [US2] Add test `test_v6_backstop_error_distinguishable_from_pydantic` to `tests/tools/test_registry_invariant.py`. Construct two failures — one at `GovAPITool(...)` (ValidationError from pydantic), one at `register()` of a bypassed instance (RegistrationError) — assert `isinstance(layer1_err, ValidationError)`, `isinstance(layer2_err, RegistrationError)`, and that the layer-2 error message contains `"registry backstop — bypass of pydantic V6 detected"` while the layer-1 message does NOT. Satisfies FR-043.

### Implementation for User Story 2

- [X] T012 [US2] Extend `ToolRegistry.register()` in `src/kosmos/tools/registry.py` by adding a V6 backstop block immediately after the existing V3 FR-038 drift check (per data-model.md §3.3). Import `_AUTH_TYPE_LEVEL_MAPPING` from `kosmos.tools.models`. Logic: lookup `tool.auth_type`; if missing, emit structured ERROR log and raise `RegistrationError(tool.id, "V6 violation (FR-048): unknown auth_type ...")` per contracts/v6-error-contract.md §Contract 2 fail-closed variant; else if `tool.auth_level not in allowed`, emit structured log matching the V3 precedent format (`logger.error("V6 violation at registry.register: tool_id=%s auth_type=%s auth_level=%s allowed=%s", ...)`) and raise the main `RegistrationError` per Contract 2. Update the `register()` docstring's `Raises:` section to list the new V6 condition. Run T008–T011 to confirm all 4 pass and existing FR-038 backstop tests unchanged.

**Checkpoint**: US2 complete. Defense-in-depth is now two-layered. V3 FR-038 pattern is preserved. Pydantic bypass via `model_construct` / `__setattr__` cannot land a V6-violating tool.

---

## Phase 5: User Story 3 — Security spec document v1.1 publishes the V6 matrix (Priority: P3)

**Goal**: `docs/security/tool-template-security-spec-v1.md` receives a new "V6: auth_type ↔ auth_level consistency" section containing (a) the canonical mapping matrix as a table, (b) a worked example explicitly labeling `auth_type="public" + auth_level="AAL1" + requires_auth=True` as approved (not as an exception), (c) a rationale paragraph naming `PermissionPipeline.dispatch()` as the reason V5 alone is insufficient. Document version bumped to v1.1.

**Independent Test**: Manual review by opening the file and confirming all 4 spec.md §US3 acceptance scenarios pass (V6 section present, matrix table present, `resolve_location`/`lookup` worked example present as "approved" not "exception", dispatch-path rationale present). Also `grep "V6:" docs/security/tool-template-security-spec-v1.md` returns the section header, and `grep "v1.1" docs/security/tool-template-security-spec-v1.md` confirms the version bump.

### Implementation for User Story 3

- [X] T013 [US3] Append a new section titled `## V6 — auth_type ↔ auth_level consistency` to `docs/security/tool-template-security-spec-v1.md`, placed after the existing V5 section. Contents: (a) one-paragraph statement of the invariant referencing FR-039/FR-040; (b) the 3 × 4 matrix table from data-model.md §1 (auth_type rows × auth_level columns, ✅/❌ cells); (c) a "Worked example: MVP meta-tools" subsection documenting `auth_type="public", auth_level="AAL1", requires_auth=True` as the approved pattern used by `resolve_location` and `lookup` (explicitly note: this is a compliant combination, NOT an exception or carve-out — matches spec.md §US3 AS3); (d) a "Why V5 alone is insufficient" rationale subsection explaining that `PermissionPipeline.dispatch()` derives access tier from `auth_type` (not `requires_auth`), so without V6 a future adapter with `public + AAL2 + requires_auth=True` would pass V1–V5 yet be anonymously callable through the legacy pipeline path (matches spec.md §US3 AS4); (e) a short "Two-layer defense" paragraph explaining validator + registry backstop (mirrors the V3 FR-038 structure used earlier in the document). Then bump the document version header from `v1.0` to `v1.1` and add a "Changelog" entry: `v1.1 (2026-04-17): Added V6 invariant (Epic #654). No changes to V1–V5.`

**Checkpoint**: US3 complete. External reviewers can verify the V6 invariant from the spec document alone (SC-004).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Close out FR-044 (registry-wide scan) and SC-005 (no V1–V5 regression), plus final audit run of the quickstart author flow.

- [ ] T014 Add test `test_all_registered_adapters_satisfy_v6` to `tests/tools/test_registry_invariant.py`. Instantiate the production registry factory (the same one the orchestrator uses — locate via existing fixtures; likely `build_default_registry()` or similar — grep for the existing invocation in `test_registry_invariant.py` if uncertain). Iterate `registry.all_tools()`; for each tool assert `tool.auth_level in _AUTH_TYPE_LEVEL_MAPPING[tool.auth_type]`. On failure, the assertion message MUST include the tool id, both field values, and the allowed set. Test MUST be deterministic (no sleep, no network, no randomness) and run in the default CI suite. Depends on T007 + T012 both landing (regression-scan gate). Satisfies FR-044 and SC-001.
- [ ] T015 Run `uv run pytest` at the repo root to confirm: (a) all new V6 tests pass, (b) zero V1–V5 tests changed or regressed (satisfies SC-005), (c) full tool suite green. Record pass count in PR body.
- [ ] T016 [P] Walk through `specs/025-tool-security-v6/quickstart.md` from an "adapter author" perspective: open the matrix table, pick each of the 4 disallowed pairs, attempt construction in a Python REPL (`uv run python -c "..."`) or ad-hoc script, confirm each fails with the expected V6 error message, confirm the MVP-meta-tool pattern `(public, AAL1, requires_auth=True)` succeeds. No code changes — this is a pre-PR smoke audit to confirm documented behavior matches implementation (satisfies SC-004 dry-run).
- [ ] T017 [P] Verify `CLAUDE.md` "Active Technologies" and "Recent Changes" sections were updated by the `/speckit-plan` hook (`update-agent-context.sh claude`). If the 025-tool-security-v6 entry is missing, re-run the hook. No source changes.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup (T001)**: No dependencies. Start immediately.
- **Phase 2 Foundational (T002)**: Depends on T001. BLOCKS US1 and US2.
- **Phase 3 US1 (T003–T007)**: Depends on T002. Can run fully in parallel with Phase 4 US2 after T002 lands.
- **Phase 4 US2 (T008–T012)**: Depends on T002. Can run fully in parallel with Phase 3 US1 after T002 lands.
- **Phase 5 US3 (T013)**: Depends on T007 + T012 (the spec doc describes behavior that must actually exist). CAN begin drafting in parallel with Phase 3 / 4 but MUST NOT land until US1 + US2 have landed.
- **Phase 6 Polish (T014–T017)**: T014 depends on T007 + T012 (regression scan needs both layers). T015 depends on all prior tasks. T016/T017 depend on T013 (docs) and T002 (context update) respectively.

### User Story Dependencies

- **US1 (P1)**: Depends only on T002. Independently testable via `test_gov_api_tool_extensions.py`.
- **US2 (P2)**: Depends only on T002. Independently testable via `test_registry_invariant.py` backstop tests (not the registry-scan; that is T014 polish).
- **US3 (P3)**: Describes behavior implemented by US1 + US2; content-authoring can start anytime but publication depends on both.

### Within Each User Story

- Tests (T003–T006 for US1; T008–T011 for US2) MUST be written and FAIL before implementation (T007 for US1; T012 for US2). Matches the V1–V5 TDD pattern established in PR #653.
- No model-before-service dependency here; V6 adds a single validator block + a single backstop block, not multi-layer code.

### Parallel Opportunities

- T003, T004, T005, T006 — all `[P] [US1]`, all in `tests/tools/test_gov_api_tool_extensions.py`. Same file, BUT each task adds an independent test function; they can be authored concurrently by different workers and merged sequentially. Mark [P] at the authoring level; commit sequentially to avoid conflict resolution overhead.
- T008, T009, T010, T011 — all `[P] [US2]`, same file pattern as above.
- US1 and US2 are fully independent after T002 lands — an Agent Team could split US1 to one Teammate and US2 to another.
- T016, T017 — independent polish tasks in the final phase.
- The only strict serialization: T001 → T002 → {US1, US2 in parallel} → T013 (docs) ∥ T014 (scan) → T015 (final green).

---

## Parallel Example: US1 + US2 after T002 lands

```bash
# Worker A: US1 test authoring (tests/tools/test_gov_api_tool_extensions.py)
Task T003: positive parametrized test for 8 allowed pairs
Task T004: negative parametrized test for 4 disallowed pairs
Task T005: fail-closed unknown auth_type test
Task T006: V5↔V6 interaction test

# Worker B: US2 test authoring (tests/tools/test_registry_invariant.py)
Task T008: model_construct bypass negative
Task T009: __setattr__ mutation negative
Task T010: model_construct positive
Task T011: FR-043 distinguishability

# After both worker test batches land red:
Worker A: T007 (validator implementation) → tests go green
Worker B: T012 (backstop implementation) → tests go green

# Then sequential polish:
T013 (docs) → T014 (registry-wide scan) → T015 (full pytest green) → T016/T017 (parallel audit)
```

---

## Implementation Strategy

### MVP First (US1 only)

1. T001 (baseline green)
2. T002 (foundational mapping constant)
3. T003–T007 (US1 validator + tests)
4. **STOP and VALIDATE**: `pytest tests/tools/test_gov_api_tool_extensions.py -k V6 -v` green
5. At this point the primary threat (Epic #654 reference case `public + AAL2 + requires_auth=True` through pydantic) is already closed for 99% of real-world paths. US2 is defense-in-depth; US3 is governance.

### Incremental Delivery

1. T001 + T002 → foundation ready
2. US1 (T003–T007) → primary defense lands → MVP ship-ready for the pydantic-path threat
3. US2 (T008–T012) → bypass defense lands → full two-layer defense
4. US3 (T013) → governance artifact published
5. Polish (T014–T017) → regression scan + full-suite green + docs audit → PR-ready

### Parallel Team Strategy (Agent Teams)

With Lead (Opus) + 2 Teammates (Sonnet), assuming T001 + T002 have landed:

1. Teammate-A (Backend Architect): US1 — T003/T004/T005/T006/T007
2. Teammate-B (Security Engineer): US2 — T008/T009/T010/T011/T012
3. Lead (Opus): US3 doc authoring (T013) in parallel; merges both teammate PRs, runs T014/T015/T016/T017
4. Total: 3-way parallelism gated only by T002 completion.

---

## Notes

- `[P]` tasks = logically independent; same-file tests ([P]-marked) can be authored concurrently but commits should sequence to avoid merge conflicts.
- `[Story]` label maps each task to a user story for traceability against spec.md.
- No new runtime dependencies are added (Constitution rule; hard AGENTS.md rule).
- All tests MUST be deterministic; no live APIs (Constitution §IV).
- Error messages MUST match contracts/v6-error-contract.md verbatim for the substring assertions. If an implementation chooses a slightly different wording, the contract doc must be updated in the same PR — do not let test expectations drift from the documented contract.
- Avoid: modifying V1–V5 logic (SC-005), altering `TOOL_MIN_AAL` (out of V6 scope), adding fields to `GovAPITool` (V6 is pure cross-field validation), changing `PermissionPipeline.dispatch()` (explicitly deferred).
