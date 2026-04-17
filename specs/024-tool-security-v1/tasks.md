# Tasks: Tool Template Security Spec v1 — Ministry-PR-ready hardening

**Input**: Design documents from `/Users/um-yunsang/KOSMOS/specs/024-tool-security-v1/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Unit tests are IN SCOPE for this spec — see data-model.md §8. Two new test modules land with the schema models (covering FR-005, FR-009, FR-010, FR-012, SC-003, SC-004). Integration/live tests are out of scope (no network I/O introduced by this spec).

**Organization**: Tasks are grouped by user story so each story can be implemented, validated, and shipped as an independent slice.

## Format: `- [ ] [TaskID] [P?] [Story?] Description with file path`

- **[P]**: parallelizable (different files, no dependency on incomplete tasks)
- **[US1] / [US2] / [US3]**: user-story label (setup/foundational/polish tasks have NO story label)
- Every task includes an exact absolute-relative file path so another agent can execute it without context.

---

## Phase 1: Setup (shared infrastructure)

**Purpose**: Create directory scaffolding and empty module placeholders so later tasks can write into predictable locations.

- [X] T001 [P] Create `src/kosmos/security/` package with `__init__.py` exporting `audit` submodule (empty module body — downstream tasks fill it).
- [X] T002 [P] Create `docs/security/` directory and add an empty `.gitkeep` (three doc artifacts land here in US1/US2).
- [X] T003 [P] Create `tests/unit/` marker directory if absent and confirm `conftest.py` requires no new fixtures (read-only check; do not modify existing tests).

**Checkpoint**: Scaffolding only. No runtime code yet. All three tasks are parallelizable.

---

## Phase 2: Foundational (blocking prerequisites for ALL user stories)

**Purpose**: Land the single-source-of-truth `TOOL_MIN_AAL` table and the `GovAPITool` field extensions. Every downstream story depends on these.

**⚠️ CRITICAL**: No user-story phase may begin until this phase is complete.

- [X] T004 Add `TOOL_MIN_AAL: Final[dict[str, str]]` static lookup table and `PublicPathMeta` dataclass in `src/kosmos/security/audit.py` per data-model.md §2. Include docstring citing NIST SP 800-63-4 and listing all 8 canonical tools.
- [X] T005 Extend `GovAPITool` in `src/kosmos/tools/models.py` with the four new mandatory fields (`auth_level`, `pipa_class`, `is_irreversible`, `dpa_reference`) using `Literal` typing per data-model.md §1. Required (no defaults) — load-time failure is the invariant.
- [X] T006 Add cross-field validators V1–V4 to `GovAPITool` via pydantic v2 `model_validator(mode="after")` in `src/kosmos/tools/models.py`. Each validator raises `ValueError` with a message referencing the FR (V1→FR-004, V2→FR-014 documentation gap, V3→FR-001/FR-005, V4→FR-004 extension).
- [X] T007 Wire `ToolRegistry.register()` (existing call site) to import `TOOL_MIN_AAL` and enforce V3 consistency at registration time; failure path emits a structured log via stdlib `logging` and re-raises the `ValueError`. File: `src/kosmos/tools/registry.py`.
- [X] T008 Migrate the 4 existing seed adapter registrations (`koroad_accident_hazard_search`, `kma_forecast_fetch`, `hira_hospital_search`, `nmc_emergency_search`) to populate all four new fields per `TOOL_MIN_AAL` row. File: `src/kosmos/tools/adapters/` (search and edit the 4 registration sites).

**Checkpoint**: Registry now fails closed on any adapter missing the 4 new fields. All 4 seed adapters register cleanly. `uv run pytest tests/unit/test_tool_registry.py` (existing) still passes.

---

## Phase 3: User Story 1 — Ministry auditor self-serves tool-call evidence (Priority: P1) 🎯 MVP

**Story Goal**: A ministry reviewer reads only the normative spec + three artifacts (JSON Schema, OpenAPI skeleton, PR checklist) and answers the three self-serve questions from spec.md User Story 1 without code or Q&A.

**Independent Test**: An unfamiliar reviewer produces a gap assessment from documentation alone correctly identifying min-AAL per tool, audit record fields, and PIPA role split.

### Implementation tasks for US1

- [X] T009 [US1] Author `src/kosmos/security/audit.py` `ToolCallAuditRecord` pydantic v2 model with `ConfigDict(frozen=True)` per data-model.md §3 — all 18 fields typed with `Literal` where applicable, invariants I1–I4 enforced via `model_validator(mode="after")`.
- [X] T010 [P] [US1] Copy `specs/024-tool-security-v1/contracts/tool-call-audit-record.schema.json` to `docs/security/tool-call-audit-record.schema.json` (final published location; the contracts/ path remains as the spec-internal source).
- [X] T011 [P] [US1] Author the normative spec document `docs/security/tool-template-security-spec-v1.md` with sections: (1) Purpose & audience, (2) `TOOL_MIN_AAL` table with Korean+English descriptions and NIST SP 800-63-4 citations, (3) `check_eligibility` `public_path` conditions (FR-002), (4) `GovAPITool` field contract (FR-003/FR-004/FR-005), (5) Permission pipeline (FR-006/FR-007/FR-008, ASVS V4.1.5 cite), (6) Audit trail (FR-009/FR-010/FR-011/FR-012, retention citation reconciling PIPA §8 + 전자정부법 §33 to 5-year binding maximum), (7) PIPA role — §26 수탁자 default + LLM-synthesis controller-level carve-out, (8) Edge case disposition (all 7 from spec.md).
- [X] T012 [US1] Embed the 3 worked audit-record examples (authenticated allow, deny_aal, check_eligibility public_path) into `docs/security/tool-template-security-spec-v1.md` §Audit trail, copy-pasted from `quickstart.md` §2-§3 with minimum cosmetic changes. Each example MUST validate against the JSON Schema (SC-004).
- [X] T013 [US1] Author `tests/unit/test_tool_call_audit_record.py` covering: (a) minimum-valid record round-trip, (b) invariant I1 (sanitized_output_hash ↔ merkle_covered_hash), (c) invariant I2 (public_path_marker → tool_id + AAL1 + non_personal), (d) invariant I3 (pipa_class ≠ non_personal → dpa_reference non-null), (e) invariant I4 (naïve timestamp rejected), (f) the 3 worked examples from spec validate against the JSON Schema via `jsonschema` library.
- [X] T014 [US1] Add a performance assertion to `tests/unit/test_tool_call_audit_record.py`: `ToolCallAuditRecord.model_validate` runs in < 5 ms per call averaged over 1000 iterations (data-model.md §3 performance target; non-enforcing in schema, enforcing in test).

**Checkpoint**: A reviewer reading `docs/security/tool-template-security-spec-v1.md` + `docs/security/tool-call-audit-record.schema.json` can answer User Story 1's three questions. JSON Schema validates all three embedded examples in CI. SC-001, SC-003, SC-004, SC-006, SC-008 all testable.

---

## Phase 4: User Story 2 — Citizen delegates authority via OAuth 2.1 + VC skeleton (Priority: P1)

**Story Goal**: A standards-literate reviewer confirms the `/agent-delegation` OpenAPI 3.0 skeleton is implementable by any ministry adopting OAuth 2.1 + mTLS without KOSMOS-proprietary coupling, and the normative delegation section documents the citizen-revocable, scope-limited, time-bounded protocol.

**Independent Test**: The OpenAPI skeleton validates under a standard OpenAPI 3.0 linter with zero errors and every normative citation resolves to an IETF RFC, W3C recommendation, or Korean statute.

### Implementation tasks for US2

- [X] T015 [P] [US2] Copy `specs/024-tool-security-v1/contracts/agent-delegation.openapi.yaml` to `docs/security/agent-delegation.openapi.yaml` (final published location).
- [X] T016 [US2] Extend `docs/security/tool-template-security-spec-v1.md` with a new §Delegation protocol section covering: (a) OAuth 2.1 baseline + PKCE (RFC 7636) mandate, (b) Device grant flow (RFC 8628) use case, (c) Token exchange flow (RFC 8693) ministry-to-ministry hand-off, (d) JWT profile (RFC 9068) `aal_asserted` claim, (e) Introspection (RFC 7662) mandatory on every `is_irreversible=True` call per FR-007, (f) Revocation (RFC 7009) with explicit maximum cache-propagation window, (g) Consent record fields including `dpa_reference` (FR-014) and `synthesis_consent` (FR-015), (h) PASS/공동인증서 TEE-binding statement (FR-016).
- [X] T017 [P] [US2] Add `docs/security/tool-template-security-spec-v1.md` §W3C Verifiable Credentials + DID subsection citing W3C VC Data Model v2.0 and W3C DID Core v1.0 as the target posture for agent-bound credentials (referencing research.md §3.7).
- [X] T018 [US2] Run OpenAPI 3.0 lint on `docs/security/agent-delegation.openapi.yaml` locally via `npx @redocly/cli lint docs/security/agent-delegation.openapi.yaml` (or equivalent standard linter if not available; document the chosen tool in the spec doc) and fix any errors. Must pass with zero errors for SC-007.

**Checkpoint**: OpenAPI skeleton validates. Delegation section of normative doc complete. SC-007 passes (zero OpenAPI lint errors; every citation resolves to IETF/W3C/Korean statute).

---

## Phase 5: User Story 3 — Tool-adapter developer self-verifies via unified PR checklist (Priority: P2)

**Story Goal**: A KOSMOS contributor opens an adapter PR, applies the unified checklist once, and covers all six research-lane domains without lane-specific knowledge; a reviewer completes checklist-mediated review in <30 min.

**Independent Test**: A contributor unfamiliar with the six lanes applies the checklist to a representative adapter and produces a compliance report matching a senior reviewer's with at most one false-negative within 30 min.

### Implementation tasks for US3

- [X] T019 [US3] Extend `docs/tool-adapters.md` with a new §Security PR checklist (spec v1) section containing the 5 unified checklist items from `quickstart.md` §6 (AAL alignment, audit shape parity, output sanitization declaration, irreversible-action introspection, DPA + synthesis consent). Each item cross-links to the relevant FR in the normative spec and the relevant research-lane domain.
- [X] T020 [P] [US3] Author `tests/unit/test_gov_api_tool_extensions.py` covering: (a) happy-path registration of a compliant adapter, (b) V1 violation (`pipa_class=personal` + `auth_level=public` → `ValueError`), (c) V2 violation (`pipa_class=identifier` + `dpa_reference=None` → `ValueError`), (d) V3 violation (`auth_level` disagrees with `TOOL_MIN_AAL` row → `ValueError`), (e) V4 violation (`is_irreversible=True` + `auth_level=public` → `ValueError`), (f) omission of each of the 4 new fields in turn → `ValueError` at load.
- [X] T021 [US3] Add a registry-scan invariant test to `tests/unit/test_gov_api_tool_extensions.py`: load every in-tree adapter module under `src/kosmos/tools/adapters/` via `importlib` and assert each registers without raising. This guards SC-003 (100% of canonical tools carry all 4 new fields at load time).
- [X] T022 [US3] Update `docs/tool-adapters.md` existing sections (if any reference old NIST SP 800-63-3 text or describe fields without `auth_level`/`pipa_class`/`is_irreversible`/`dpa_reference`) to reflect the new contract. Do not remove existing sections; amend in place.

**Checkpoint**: Contributors have a single 5-item security checklist. Invariant tests guard the registry. SC-002 verifiable once checklist is applied to 3 representative adapters by an unfamiliar reviewer.

---

## Phase 6: Polish & cross-cutting concerns

**Purpose**: SBOM scaffolding, citation audit, and final documentation consistency passes that touch multiple stories.

- [X] T023 [P] Create `.github/workflows/sbom.yml` scaffolded workflow that on push to `main` and on tag release runs `uv` to produce SPDX 2.3 (`syft` or equivalent) and CycloneDX 1.6 (`cyclonedx-py`) artifacts from `pyproject.toml` + `uv.lock`, uploads both as workflow artifacts, and fails the build if the diff-vs-last-signed check fails (full signing is deferred per research.md §3.8; scaffold includes the comparison step with a stub signer documented as deferred).
- [X] T024 [P] Extend `docs/security/tool-template-security-spec-v1.md` with a §Supply chain & provenance section covering FR-017 (SBOM dual-format), FR-018 (SLSA L3 gap analysis: current→target), FR-019 (build-gate divergence policy). Cite SLSA v1.0, NIST SP 800-218 SSDF, SPDX 2.3, CycloneDX 1.6, sigstore/cosign.
- [X] T025 Run a citation audit on `docs/security/tool-template-security-spec-v1.md`: every control referenced MUST cite at least one of (PIPA section, 전자정부법 section, 전자서명법 section, K-ISMS-P clause, NIST SP 800-63-4 section, OWASP ASVS V#.#.#, OWASP Top 10 for LLM #, ISO 27001 control, NIST SP 800-207 section, SLSA v1.0 level, IETF RFC, W3C recommendation, eGovFramework component, Singapore IMDA MGF section, EU AI Act Annex III). Fix any missing citations. Verifies FR-021.
- [X] T026 Run a PIPA-role consistency pass on `docs/security/tool-template-security-spec-v1.md`: every occurrence of 처리자/수탁자/controller/processor MUST trace to the §26 수탁자 default + LLM-synthesis controller-level carve-out interpretation. Fix any contradictory language. Verifies SC-008.
- [X] T027 [P] Run `uv run pytest tests/unit/test_gov_api_tool_extensions.py tests/unit/test_tool_call_audit_record.py -v` and confirm all tests pass including SC-004 schema-validation of the 3 worked examples.
- [X] T028 [P] Verify `docs/security/tool-call-audit-record.schema.json` is reachable by its declared `$id` (static check — no live fetch) and matches `specs/024-tool-security-v1/contracts/tool-call-audit-record.schema.json` byte-for-byte. Files must stay in sync.
- [X] T029 Smoke-test the SBOM workflow locally via `act` (if installed) or document in `.github/workflows/sbom.yml` comment block the exact manual reproduction steps from a fresh clone (SC-005: zero-manual-step reproducibility).
- [X] T030 Final pass: update `CLAUDE.md` `## Active Technologies` bullet for `024-tool-security-v1` (already done in Phase 1 via `update-agent-context.sh`; confirm no new entries needed) and update `CLAUDE.md` `## Recent Changes` top-of-list with a one-line 024 summary.

**Checkpoint**: All 8 SC items verifiable. CI has two new passing test modules. SBOM workflow scaffolded. All three docs (normative spec, JSON Schema, OpenAPI skeleton) published under `docs/security/`. `docs/tool-adapters.md` carries the 5-item unified PR checklist. `CLAUDE.md` current.

---

## Dependencies & Execution Order

```text
Setup (T001–T003)  ────────────▶  Foundational (T004–T008)
                                          │
        ┌─────────────────────────────────┼─────────────────────────────────┐
        ▼                                 ▼                                 ▼
   US1 (T009–T014)                   US2 (T015–T018)                   US3 (T019–T022)
       P1 / MVP                           P1                                 P2
        │                                 │                                  │
        └─────────────────────────────────┼──────────────────────────────────┘
                                          ▼
                                  Polish (T023–T030)
```

**Story independence**: US1, US2, US3 are mutually independent once Phase 2 is green. US1 is the MVP slice (ministry auditor self-serves) and can ship alone as a documentation-only release; US2 and US3 extend coverage and can land in either order.

**Task dependencies inside phases**:

- T004 precedes T005/T006/T007 (validator V3 reads `TOOL_MIN_AAL`).
- T005 precedes T006 (validators attach to the extended model).
- T006 precedes T007 (registry wiring invokes the validators).
- T007 precedes T008 (seed migration requires registry enforcement in place).
- T009 precedes T012/T013/T014 (examples and tests import the pydantic model).
- T011 precedes T012/T025/T026 (normative doc skeleton must exist before examples are embedded and audits run).
- T015 precedes T016/T018 (OpenAPI file must be in published location before spec doc references it and linter runs).
- T019 precedes T022 (new section lands before amendments to existing sections).
- T020/T021 depend on T004–T008 (Foundational) only.
- T023 and T024 parallelizable with each other.

---

## Parallel Execution Opportunities

**Phase 1 (Setup)**: T001, T002, T003 all parallelizable — empty scaffolding, no cross-file dependency.

**Phase 3 (US1)**:
- T010 (copy schema artifact) parallel with T011 (author normative doc draft).
- T013 and T014 sequential within the same file (`test_tool_call_audit_record.py`).

**Phase 4 (US2)**:
- T015 (copy OpenAPI artifact) parallel with T017 (VC/DID subsection).
- T018 (lint) sequential after T015 + T016 so the file is in its final form.

**Phase 5 (US3)**:
- T019 parallel with T020 (different files: `docs/tool-adapters.md` vs `tests/unit/test_gov_api_tool_extensions.py`).
- T021 appends to T020's file → sequential.
- T022 edits existing sections of `docs/tool-adapters.md` → sequential after T019.

**Phase 6 (Polish)**:
- T023 and T024 fully parallel (different files).
- T027 and T028 parallelizable (one runs tests, the other does a file-diff check).

**Across phases**: US2 and US3 tasks may interleave with US1 once Foundational is green if multiple agents work in parallel, provided each story's in-phase ordering is respected.

---

## Implementation Strategy

**MVP first (US1 alone)**: Deliver T001–T014 as the first shippable slice. This gives a ministry reviewer everything needed to self-serve the three spec.md User Story 1 questions. It is a pure-documentation + pydantic-model release with zero behavior change to the running system beyond schema validation.

**Incremental delivery order**:

1. **Slice 1 (MVP — US1)**: T001–T014. Ships the normative spec doc + `ToolCallAuditRecord` model + JSON Schema + 3 worked examples + unit tests. Ministry reviewer self-service achieved. Adapter PR checklist, OpenAPI skeleton, and SBOM workflow defer to later slices.

2. **Slice 2 (US2 + US3 in parallel)**: T015–T022. US2 lands the citizen-delegation OpenAPI skeleton and corresponding normative doc section. US3 lands the unified PR checklist + invariant test scanner. These stories are independent and can ship via two separate PRs.

3. **Slice 3 (Polish)**: T023–T030. SBOM workflow + citation audit + PIPA-role audit + final `CLAUDE.md` touch-up. This slice is where SC-005 (SBOM reproducibility) and SC-001/SC-006/SC-008 auditability become fully verifiable.

**Parallel-team execution**: With 3 agents post-Foundational, one owns US1 (P1 MVP), one owns US2 (P1), one owns US3 (P2). Polish phase consolidates into a single agent after all three streams merge.

---

## Task completeness validation

- [x] Every task starts with `- [ ]`, has a sequential `T###` ID, includes a file path, and carries `[US#]` exactly when inside a user-story phase (Setup/Foundational/Polish phases carry no story label, by template).
- [x] Every FR (FR-001 through FR-021) maps to at least one task:
  - FR-001 → T004, T011
  - FR-002 → T011 (public_path section)
  - FR-003 → T005
  - FR-004 → T006 (V1/V4 validators), T011
  - FR-005 → T005, T006, T007, T020, T021
  - FR-006 → T011 (permission pipeline section)
  - FR-007 → T011 (permission pipeline section), T016 (introspection citation)
  - FR-008 → T011 (deny-by-default + ASVS V4.1.5)
  - FR-009 → T009, T010
  - FR-010 → T009 (merkle_covered_hash field), T011
  - FR-011 → T011 (retention reconciliation to 5-year binding maximum)
  - FR-012 → T009 (adapter_mode enum), T011
  - FR-013 → T015, T016
  - FR-014 → T006 (V2 validator), T011, T016
  - FR-015 → T016
  - FR-016 → T016, T017
  - FR-017 → T023
  - FR-018 → T024
  - FR-019 → T023, T024
  - FR-020 → T019
  - FR-021 → T025
- [x] Every SC (SC-001 through SC-008) maps to at least one verification task:
  - SC-001 → T025 (citation audit with resolution traces)
  - SC-002 → T019 + manual 30-min timing test (documented as manual)
  - SC-003 → T021
  - SC-004 → T013, T027
  - SC-005 → T023, T029
  - SC-006 → T011, T012, T017 (blind-review exercise documented at acceptance)
  - SC-007 → T018
  - SC-008 → T026
- [x] Every user story has at least one implementation task and one test/verification task.
- [x] The MVP (User Story 1) is independently shippable (Slice 1 above).

---

## Summary

- **Total tasks**: 30
- **Setup phase**: 3 tasks (T001–T003), all parallelizable
- **Foundational phase**: 5 tasks (T004–T008), mostly sequential
- **US1 (Ministry auditor, P1, MVP)**: 6 tasks (T009–T014)
- **US2 (Citizen delegation, P1)**: 4 tasks (T015–T018)
- **US3 (Adapter developer, P2)**: 4 tasks (T019–T022)
- **Polish phase**: 8 tasks (T023–T030)
- **Parallel-marked tasks**: 10 (T001, T002, T003, T010, T011, T015, T017, T020, T023, T024, T027, T028)
- **MVP suggested scope**: T001–T014 (Setup + Foundational + US1)
