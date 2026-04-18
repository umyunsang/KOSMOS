---

description: "Task list for 029 Phase 2 Adapters — NFA 119 + MOHW (SSIS)"
---

# Tasks: 029 Phase 2 Adapters — NFA 119 + MOHW (SSIS)

**Input**: Design documents from `/Users/um-yunsang/KOSMOS-15/specs/029-phase2-adapters-119-mohw/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. Happy-path + error-path unit tests per adapter are mandatory per spec §4 and `docs/tool-adapters.md` checklist. Tests are written alongside implementation (not strict TDD) to match the interface-only pattern used by `nmc_emergency_search`.

**Organization**: Tasks are grouped by user story. User Story 1 (NFA) and User Story 2 (MOHW) are independent — each touches a disjoint provider package (`src/kosmos/tools/nfa119/` vs `src/kosmos/tools/ssis/`), disjoint tests, and separate `TOOL_MIN_AAL` rows. They can be delivered in parallel by two Teammates.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: `[US1]` = NFA adapter, `[US2]` = MOHW adapter, `[US3]` = Scenario 3 E2E enablement
- All file paths are absolute under `/Users/um-yunsang/KOSMOS-15/`.

## Path Conventions

Single Python project per `plan.md § Project Structure`:
- Source: `src/kosmos/tools/<provider>/`, `src/kosmos/security/`
- Tests: `tests/tools/<provider>/`, `tests/fixtures/<provider>/`
- Docs: `docs/tools/`, `docs/security/dpa/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new provider package skeletons and fixture/docs directories. No per-story logic yet.

- [ ] T001 [P] Create NFA package skeleton: `mkdir -p src/kosmos/tools/nfa119` and add empty `src/kosmos/tools/nfa119/__init__.py` (module docstring only: `"""NFA (소방청) tool adapters."""`)
- [ ] T002 [P] Create SSIS package skeleton: `mkdir -p src/kosmos/tools/ssis` and add empty `src/kosmos/tools/ssis/__init__.py` (module docstring only: `"""SSIS (한국사회보장정보원) / MOHW tool adapters."""`)
- [ ] T003 [P] Create NFA test package: `mkdir -p tests/tools/nfa119` + `tests/tools/nfa119/__init__.py` (empty)
- [ ] T004 [P] Create SSIS test package: `mkdir -p tests/tools/ssis` + `tests/tools/ssis/__init__.py` (empty)
- [ ] T005 [P] Create fixture directories: `mkdir -p tests/fixtures/nfa119 tests/fixtures/ssis`
- [ ] T006 [P] Create DPA directory: `mkdir -p docs/security/dpa`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Ship the shared SSIS code-table enums (consumed by US2 and all future SSIS adapters per spec §9.2) and the DPA placeholder stub (required by V2 validator traceability before US2's `GovAPITool` construction can load). No user story work starts until these complete.

**CRITICAL**: T007 blocks US2. T008 blocks US2. Neither blocks US1.

- [ ] T007 Implement SSIS code-table enums in `src/kosmos/tools/ssis/codes.py` verbatim from `specs/029-phase2-adapters-119-mohw/data-model.md §1` (exports: `SrchKeyCode`, `CallType`, `OrderBy`, `LifeArrayCode`, `TrgterIndvdlCode`, `IntrsThemaCode`). All enums are `str, enum.Enum` subclasses. English identifier names, Korean meanings as inline comments only.
- [ ] T008 [P] Create DPA placeholder stub at `docs/security/dpa/dpa-ssis-welfare-v1.md` verbatim from `specs/029-phase2-adapters-119-mohw/data-model.md §9` (reserves the identifier for validator V2 traceability).
- [ ] T009 [P] Add enum coverage test in `tests/tools/ssis/test_codes.py`: assert each enum has the expected member count (SrchKeyCode=3, CallType=2, OrderBy=2, LifeArrayCode=7, TrgterIndvdlCode=6, IntrsThemaCode=14) and that every value is a zero-padded decimal string or short keyword exactly matching `data-model.md §1`.

**Checkpoint**: Shared SSIS taxonomy ready. US1 and US2 can now proceed in parallel.

---

## Phase 3: User Story 1 — NFA Emergency Info Service (Priority: P1) MVP-parallel-a

**Goal**: Register `nfa_emergency_info_service` as a discoverable, fail-closed `GovAPITool` that returns `LookupError(reason="auth_required")` for unauthenticated sessions and raises `Layer3GateViolation` if `handle()` is reached directly.

**Independent Test**:
1. `uv run python -c "from kosmos.tools.registry import ToolRegistry; from kosmos.tools.register_all import register_all; from kosmos.tools.executor import ToolExecutor; r=ToolRegistry(); register_all(r, ToolExecutor()); assert 'nfa_emergency_info_service' in r._tools; print('OK')"` prints `OK`.
2. `uv run pytest tests/tools/nfa119 -v` passes (happy schema + error schema + Layer3GateViolation + executor auth_required + BM25 top-5).

### Implementation for User Story 1

- [ ] T010 [P] [US1] Implement `NfaEmgOperation` enum + `NfaEmergencyInfoServiceInput` in `src/kosmos/tools/nfa119/emergency_info_service.py` verbatim from `data-model.md §2`. Use `ConfigDict(extra="forbid", frozen=True)`. All 6 operations enumerated. `stmt_ym` validated with regex `^\d{6}$`. `num_of_rows` bounded `1..100`. `result_type: Literal["json"]`.
- [ ] T011 [US1] Append the 6 per-operation output item models (`NfaActivityItem`, `NfaTransferItem`, `NfaConditionItem`, `NfaFirstaidItem`, `NfaVehicleDispatchItem`, `NfaVehicleInfoItem`) and the `NfaEmergencyInfoServiceOutput` envelope to `src/kosmos/tools/nfa119/emergency_info_service.py` verbatim from `data-model.md §3.1–§3.7`. Item models use `ConfigDict(extra="allow", frozen=True)`; envelope uses `extra="forbid"`. Add `# noqa: N815` on each camelCase field name per data-model. (Depends on T010 — same file.)
- [ ] T012 [US1] Append the interface-only output stub `_NfaEmergencyInfoServiceOutputStub = RootModel[dict[str, Any]]` and the `NFA_EMERGENCY_INFO_SERVICE_TOOL: GovAPITool` registration block to `src/kosmos/tools/nfa119/emergency_info_service.py` verbatim from `data-model.md §4`. Also add an async `handle(inp: NfaEmergencyInfoServiceInput) -> dict[str, object]` function that raises `Layer3GateViolation("nfa_emergency_info_service")` (import from `kosmos.tools.errors`). `search_hint` value MUST be the exact bilingual string from `data-model.md §4` / `spec.md §4.1 search_hint` (Korean + English). (Depends on T010, T011 — same file.)
- [ ] T013 [P] [US1] Add `"nfa_emergency_info_service": "AAL1"` row to `TOOL_MIN_AAL` in `src/kosmos/security/audit.py` per `data-model.md §8`. Preserve existing rows and the `Final[dict[...]]` annotation. (Different file from T010–T012 → parallelisable.)
- [ ] T014 [US1] Import `NFA_EMERGENCY_INFO_SERVICE_TOOL` and `handle` from `kosmos.tools.nfa119.emergency_info_service` and register them in `src/kosmos/tools/register_all.py` following the existing `nmc_emergency_search` registration pattern (same call shape: `registry.register(NFA_EMERGENCY_INFO_SERVICE_TOOL, handler=handle)`). (Depends on T012 because it imports the tool constant.)
- [ ] T015 [P] [US1] Create synthetic fixture `tests/fixtures/nfa119/nfa_emergency_info_service.json` verbatim from `quickstart.md §4` (values: `충청남도소방본부`, `천안동남소방서`, `gutYm=202112`, `sptMvmnDtc=3200`, `ptntAge=60~69세`, `ruptSptmCdNm=기침`). No real PII.
- [ ] T016 [US1] Write happy + error + gate tests in `tests/tools/nfa119/test_nfa_emergency_info_service.py`:
  - happy: `NfaEmergencyInfoServiceInput.model_validate({"rsac_gut_fstt_ogid_nm": "천안동남소방서", "stmt_ym": "202112"})` succeeds and defaults `operation=activity`
  - error: `model_validate({"rsac_gut_fstt_ogid_nm": "천안동남소방서", "stmt_ym": "2021"})` raises `ValidationError` (regex mismatch)
  - error: `model_validate({"rsac_gut_fstt_ogid_nm": "천안동남소방서", "stmt_ym": "202112", "unknown": "x"})` raises `ValidationError` (`extra="forbid"`)
  - gate: `await handle(valid_input)` raises `Layer3GateViolation`
  - executor: `await executor.invoke("nfa_emergency_info_service", input=..., session_identity=None)` returns `LookupError(reason="auth_required")` and records zero upstream HTTP calls (use `respx`/`httpx_mock` to assert zero calls, or assert `LookupError` alone if the executor short-circuits before the HTTP layer — follow `tests/tools/nmc/test_emergency_search.py` pattern).
  - BM25: `lookup(mode="search", query="119 구급 출동 소방 통계 현황")` returns `nfa_emergency_info_service` in top-5 results (use the existing test helper from `tests/tools/test_lookup.py`).
  (Depends on T012, T014, T015.)
- [ ] T017 [P] [US1] Create `docs/tools/nfa119.md` documenting: provider (소방청), `tool_id`, endpoint, auth (serviceKey), 6 operations with Korean + English names, `auth_level=AAL1`, `pipa_class=non_personal`, `requires_auth=True`, `cache_ttl_seconds=86400`, reference to `research/data/nfa119/공공데이터 오픈API 활용가이드(소방청_구급정보).docx`, and the interface-only status with pointer to Epic #16/#20 for live implementation. Follow the same structure as an existing `docs/tools/<provider>.md` file if present; otherwise use the `docs/tool-adapters.md` field list as the outline.

**Checkpoint**: US1 deliverable — NFA adapter discoverable via `lookup(mode="search")`, fail-closed via Layer 3 short-circuit, V1–V6 validators green, `TOOL_MIN_AAL` row wired. Zero live `data.go.kr` calls.

---

## Phase 4: User Story 2 — MOHW Welfare Eligibility Search (Priority: P1) MVP-parallel-b

**Goal**: Register `mohw_welfare_eligibility_search` as a discoverable, fail-closed `GovAPITool` that returns `LookupError(reason="auth_required")` for unauthenticated sessions, with `is_personal_data=True`, `auth_level=AAL2`, and `dpa_reference="dpa-ssis-welfare-v1"`.

**Independent Test**:
1. Same Python one-liner as US1, but assert `'mohw_welfare_eligibility_search' in r._tools`.
2. `uv run pytest tests/tools/ssis -v` passes (happy + error + Layer3GateViolation + executor auth_required + BM25 top-5 + enum-import smoke).

### Implementation for User Story 2

- [ ] T018 [P] [US2] Implement `MohwWelfareEligibilitySearchInput` in `src/kosmos/tools/ssis/welfare_eligibility_search.py` verbatim from `data-model.md §5`. Imports `SrchKeyCode, CallType, OrderBy, LifeArrayCode, TrgterIndvdlCode, IntrsThemaCode` from `kosmos.tools.ssis.codes`. `ConfigDict(extra="forbid", frozen=True)`. `age: int | None` bounded `0..150`. `num_of_rows` bounded `1..500`. `page_no` bounded `1..1000`. (Depends on T007 — code enums must exist first.)
- [ ] T019 [US2] Append `SsisWelfareServiceItem` (`extra="allow", frozen=True`) and `MohwWelfareEligibilitySearchOutput` (`extra="forbid", frozen=True`) to `src/kosmos/tools/ssis/welfare_eligibility_search.py` verbatim from `data-model.md §6.1–§6.2`. Add `# noqa: N815` on each camelCase field. (Depends on T018 — same file.)
- [ ] T020 [US2] Append the interface-only output stub `_MohwWelfareEligibilitySearchOutputStub = RootModel[dict[str, Any]]` and the `MOHW_WELFARE_ELIGIBILITY_SEARCH_TOOL: GovAPITool` registration block to `src/kosmos/tools/ssis/welfare_eligibility_search.py` verbatim from `data-model.md §7`. Add async `handle(inp: MohwWelfareEligibilitySearchInput) -> dict[str, object]` raising `Layer3GateViolation("mohw_welfare_eligibility_search")`. `search_hint` value MUST be the exact bilingual string from `data-model.md §7` / `spec.md §4.2`. `dpa_reference="dpa-ssis-welfare-v1"` matches T008's stub file. (Depends on T018, T019 — same file; depends on T008 — DPA stub must exist for V2 traceability.)
- [ ] T021 [P] [US2] Add `"mohw_welfare_eligibility_search": "AAL2"` row to `TOOL_MIN_AAL` in `src/kosmos/security/audit.py` per `data-model.md §8`. **Coordinates with T013** — both tasks touch the same file but different lines. If T013 has landed, append the MOHW row after it. If running in parallel, one Teammate edits both rows in a single commit (swap T013/T021 into a single sequential task at dispatch time).
- [ ] T022 [US2] Import `MOHW_WELFARE_ELIGIBILITY_SEARCH_TOOL` and `handle` in `src/kosmos/tools/register_all.py` and register following the same pattern as T014. (Depends on T020. **Conflicts with T014 on the same file** — register_all.py is edited sequentially: T014 first, then T022; or one Teammate batches both.)
- [ ] T023 [P] [US2] Create synthetic fixture `tests/fixtures/ssis/mohw_welfare_eligibility_search.json` verbatim from `quickstart.md §4` (values: `servId=WLF0000001188`, `servNm=출산가정 방문서비스`, `jurMnofNm=보건복지부`, `lifeArray=임신·출산`, `intrsThemaArray=임신·출산`, `onapPsbltYn=Y`). No real PII.
- [ ] T024 [US2] Write happy + error + gate tests in `tests/tools/ssis/test_mohw_welfare_eligibility_search.py`:
  - happy: `MohwWelfareEligibilitySearchInput.model_validate({"search_wrd": "출산"})` succeeds with enum defaults (`srch_key_code=all_fields`, `order_by=popular`, `call_tp=list_`)
  - happy: `model_validate({"life_array": "007", "intrs_thema_array": "080"})` succeeds (codes accepted as enum values)
  - error: `model_validate({"life_array": "999"})` raises `ValidationError` (enum out-of-range)
  - error: `model_validate({"age": 200})` raises `ValidationError` (ge/le bound)
  - error: `model_validate({"search_wrd": "x", "unknown": "y"})` raises `ValidationError` (`extra="forbid"`)
  - gate: `await handle(valid_input)` raises `Layer3GateViolation`
  - executor: `await executor.invoke("mohw_welfare_eligibility_search", input=..., session_identity=None)` returns `LookupError(reason="auth_required")` with zero upstream HTTP calls
  - BM25: `lookup(mode="search", query="출산 보조금 복지 혜택")` returns `mohw_welfare_eligibility_search` in top-5 results
  (Depends on T020, T022, T023.)
- [ ] T025 [P] [US2] Create `docs/tools/ssis.md` documenting: provider (한국사회보장정보원 / 보건복지부), `tool_id`, endpoint, auth (serviceKey), request parameters + code-table references (link `research/data/ssis/활용가이드_중앙부처복지서비스(v2.2).doc` and `지자체복지서비스_코드표(v1.0).doc`), `auth_level=AAL2`, `pipa_class=personal`, `is_personal_data=True`, `dpa_reference=dpa-ssis-welfare-v1`, `cache_ttl_seconds=0`, and the interface-only status with pointer to Epic #16/#20.

**Checkpoint**: US2 deliverable — MOHW adapter discoverable, fail-closed, PII-gated (AAL2 + dpa_reference + is_personal_data=True), TOOL_MIN_AAL row wired. Zero live `data.go.kr` calls.

---

## Phase 5: User Story 3 — Scenario 3 E2E Enablement (Priority: P2)

**Goal**: Prove that US2's auth_required stub behaviour is the exact error shape Scenario 3's E2E test replay-asserts (spec §1 US3). No new source code — this phase is a verification + docs task, gated on US2 completion.

**Independent Test**:
- `uv run pytest tests/tools/ssis/test_mohw_welfare_eligibility_search.py::test_executor_auth_required_matches_scenario3_contract -v` passes.

### Implementation for User Story 3

- [ ] T026 [US3] Extend `tests/tools/ssis/test_mohw_welfare_eligibility_search.py` with `test_executor_auth_required_matches_scenario3_contract`: assert the `LookupError` returned by the executor for `session_identity=None` has the exact shape `{"reason": "auth_required", "retryable": False}` (or whatever the canonical Scenario 3 E2E assertion is in `specs/019-*/` if it exists; otherwise the shape mandated by `src/kosmos/tools/errors.py::LookupError`). This freezes the interface-only contract so Epic #19's E2E won't drift. (Depends on T024.)
- [ ] T027 [US3] Add a short section to `docs/tools/ssis.md` titled "Scenario 3 contract" explaining: until Layer 3 ships (Epic #16/#20), the adapter's sole externally-observable behaviour is `LookupError(reason="auth_required")`, and this is the exact shape Epic #19's E2E replays. Link to `specs/029-phase2-adapters-119-mohw/spec.md §1 User Story 3`. (Depends on T025.)

**Checkpoint**: US3 deliverable — Scenario 3 can proceed with the adapter's stub behaviour frozen as a versioned contract.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Sweeps that cover both adapters and the broader repo.

- [ ] T028 [P] Run `uv run ruff check src/kosmos/tools/nfa119 src/kosmos/tools/ssis src/kosmos/security/audit.py` and fix any findings. (Lint.)
- [ ] T029 [P] Run `uv run ruff format src/kosmos/tools/nfa119 src/kosmos/tools/ssis tests/tools/nfa119 tests/tools/ssis` to apply formatting.
- [ ] T030 [P] Run `uv run mypy src/kosmos/tools/nfa119 src/kosmos/tools/ssis` if the project has a mypy config; if not, skip. (Type-check.)
- [ ] T031 Run the full test suite `uv run pytest` from `/Users/um-yunsang/KOSMOS-15` and confirm zero regression. Attach the summary to the PR description.
- [ ] T032 Run the quickstart verification block from `specs/029-phase2-adapters-119-mohw/quickstart.md §3` (the one-liner that imports both tools into a fresh registry). Must print `OK — both tools registered`.
- [ ] T033 [P] Regenerate and verify contract schemas: re-export `specs/029-phase2-adapters-119-mohw/contracts/*.schema.json` from the final Pydantic models and diff against the committed files (they should match; if they diverge, the committed files lose).
- [ ] T034 Back-fill the NEEDS TRACKING deferred item #8 (`nfa_safety_center_lookup`) as a separate GitHub issue under Epic #15, per `research.md §1`. (`/speckit-taskstoissues` owner — flag in the analyze report.)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately. All T001–T006 are `[P]`.
- **Foundational (Phase 2)**: Depends on Setup (`__init__.py` files must exist). T007 blocks US2 only (US1 does not import from `kosmos.tools.ssis.codes`). T008 blocks US2's registration (V2 traceability). T009 depends on T007.
- **User Story 1 (Phase 3) — NFA**: Depends on Setup. Independent of Foundational (does not touch SSIS codes or DPA).
- **User Story 2 (Phase 4) — MOHW**: Depends on Setup + Foundational (T007 + T008).
- **User Story 3 (Phase 5) — Scenario 3 contract freeze**: Depends on US2 (T024, T025).
- **Polish (Phase 6)**: Depends on US1 + US2 + US3.

### Cross-Story File Conflicts

Two files are touched by both US1 and US2:

| File | US1 task | US2 task | Resolution |
|---|---|---|---|
| `src/kosmos/security/audit.py` (TOOL_MIN_AAL) | T013 | T021 | Sequential: one Teammate adds both rows, OR T013 then T021 with merge coordination. |
| `src/kosmos/tools/register_all.py` | T014 | T022 | Sequential: T014 lands first, T022 appends the second registration. |

All other US1 and US2 tasks are on disjoint files and fully parallel-safe.

### Within Each User Story

- Model files before registration block (same file → sequential edits).
- Fixture + docs before tests that read them.
- Tests after implementation for this interface-only pattern (not strict TDD — matches `nmc_emergency_search` precedent).

### Parallel Opportunities

**Setup (Phase 1)**: All 6 tasks `[P]` — 6-way parallel.

**Foundational (Phase 2)**: T007 + T008 parallel (different files). T009 waits on T007.

**User Stories 1 + 2**: Two Teammates can run in parallel after Phase 2 completes. Within US1, tasks T013/T015/T017 are `[P]` relative to T010–T012/T014/T016. Within US2, tasks T023/T025 are `[P]` relative to T018–T020/T022/T024. (T021 has a note about register_all coordination.)

**Phase 6 (Polish)**: T028/T029/T030/T033 are `[P]`. T031/T032/T034 are sequential.

---

## Parallel-Safe Task Count

**Tasks marked `[P]`** (can execute in parallel with sibling `[P]` tasks in the same phase, assuming no cross-story file conflict):

- Phase 1: T001, T002, T003, T004, T005, T006 (6)
- Phase 2: T008, T009 (2)
- US1 (Phase 3): T010, T013, T015, T017 (4)
- US2 (Phase 4): T018, T021, T023, T025 (4)
- US3 (Phase 5): 0
- Phase 6: T028, T029, T030, T033 (4)

**Total `[P]`-marked tasks**: 20 out of 34.

**Inter-story parallelism**: Phases 3 and 4 (US1 vs US2) run in parallel end-to-end (two Teammates, modulo the two shared files noted above).

---

## Parallel Example: User Story 1 (after Phase 2 complete)

```bash
# Wave 1 (parallel):
Task: "T010 NfaEmgOperation enum + NfaEmergencyInfoServiceInput in src/kosmos/tools/nfa119/emergency_info_service.py"
Task: "T013 Append nfa_emergency_info_service AAL1 row to src/kosmos/security/audit.py"
Task: "T015 Create tests/fixtures/nfa119/nfa_emergency_info_service.json"
Task: "T017 Create docs/tools/nfa119.md"

# Wave 2 (sequential on emergency_info_service.py):
Task: "T011 Append per-operation output item models"
Task: "T012 Append registration block + handle()"

# Wave 3 (sequential — depends on T012):
Task: "T014 Register NFA tool in register_all.py"
Task: "T016 Write tests/tools/nfa119/test_nfa_emergency_info_service.py"
```

---

## Implementation Strategy

### MVP Scope (recommended)

The MVP is **US1 + US2 together** — both are P1 and the Epic's primary deliverable is "two adapters registered, fail-closed, interface-only". Either adapter alone is not a shippable MVP because:
- US1 alone leaves Epic #18's fallback path un-stubbed.
- US2 alone leaves Epic #19's primary data source un-stubbed.

US3 is additive (contract freeze) and can land in the same PR or a fast follow-up.

### Two-Teammate Dispatch (the default for `/speckit-implement`)

1. Lead completes Phase 1 + Phase 2 solo or delegates Phase 1 in parallel.
2. After Phase 2 completes, dispatch:
   - **Teammate A**: Phase 3 (US1 — NFA).
   - **Teammate B**: Phase 4 (US2 — MOHW).
   - Shared-file edits (`audit.py`, `register_all.py`) resolved by convention: Teammate A lands first, Teammate B rebases and appends.
3. Lead merges, runs Phase 5 (US3) + Phase 6 (Polish).
4. PR with `Closes #15`.

### Solo Dispatch (fallback)

Linear execution 1 → 34. Estimated at ~6–8 focused hours given the interface-only pattern and the verbatim-from-data-model code body.

---

## Notes

- All source text in English (AGENTS.md hard rule). Korean only in: enum docstrings/comments, `search_hint`, `name_ko`, `category`, fixture data — never in identifier names.
- No new runtime dependencies. Stdlib `xml.etree.ElementTree` is the chosen parser for Layer 3 (deferred).
- Fixtures are synthetic; no real PII; no live `data.go.kr` calls from CI (Constitution §IV).
- `handle()` raises `Layer3GateViolation` — the executor short-circuits on `requires_auth=True` before `handle()` is reached. The raise is defence-in-depth.
- Commit after each task group. Conventional Commits. Branch `feat/15-phase2-adapters-119-mohw`. No `--force`, no `--no-verify`.
- Avoid editing `src/kosmos/tools/models.py`, `src/kosmos/tools/envelope.py`, `src/kosmos/tools/errors.py`, `src/kosmos/tools/registry.py`, `src/kosmos/tools/executor.py`, and any test not under `tests/tools/nfa119/` or `tests/tools/ssis/`. These are out of scope.
