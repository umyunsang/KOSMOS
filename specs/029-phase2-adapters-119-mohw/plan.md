# Implementation Plan: 029 Phase 2 Adapters — NFA 119 + MOHW

**Branch**: `feat/15-phase2-adapters-119-mohw` | **Date**: 2026-04-18 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `specs/029-phase2-adapters-119-mohw/spec.md`

## Summary

Register two new `GovAPITool` adapters in the KOSMOS Tool System (Layer 2) under
the interface-only pattern established by `nmc_emergency_search`:

1. **`nfa_emergency_info_service`** — NFA (소방청) `EmergencyInformationService`
   with 6 sub-endpoint operations, `api_key` + `AAL1`, `non_personal`, serving
   historical anonymized EMS records by region + fire station + month.
2. **`mohw_welfare_eligibility_search`** — SSIS (한국사회보장정보원)
   `NationalWelfarelistV001` with code-filtered search, `api_key` + `AAL2`,
   `personal` (DPA placeholder `dpa-ssis-welfare-v1`), serving the cross-ministry
   welfare service catalog.

Both adapters ship as interface-only: full pydantic v2 I/O schemas, complete
V1–V6 security metadata, registration in `register_all.py`, and a `handle()` that
raises `Layer3GateViolation` until the Layer 3 auth-gate (Epic #16 / #20) is
delivered. The executor's `requires_auth=True` short-circuit (FR-025, FR-026,
SC-006) is the primary gate; the `Layer3GateViolation` raise is the
defence-in-depth backstop. Recorded synthetic fixtures replace live
`data.go.kr` calls in CI (Constitution §IV).

## Technical Context

**Language/Version**: Python 3.12+ (existing project baseline; no bump).
**Primary Dependencies**: `pydantic >= 2.13` (I/O schemas), `httpx >= 0.27`
(deferred to Layer 3 ship; not exercised by interface-only handler),
`pytest` + `pytest-asyncio` (tests). **No new runtime dependencies** — AGENTS.md
hard rule. XML parsing (SSIS) uses stdlib `xml.etree.ElementTree` when Layer 3
lands.
**Storage**: N/A. Registry is in-memory and rebuilt at boot (spec 022 pattern).
No persistent state introduced by this spec.
**Testing**: `pytest` + `pytest-asyncio`. Live-upstream tests deferred with
Layer 3 ship and will be marked `@pytest.mark.live` (excluded from CI).
**Target Platform**: Linux server (KOSMOS backend). CLI TUI unaffected.
**Project Type**: library/backend — extends `src/kosmos/tools/` with two new
provider packages (`nfa119/`, `ssis/`).
**Performance Goals**: No new perf budget introduced. Registry boot time MUST
remain within the existing spec 022 envelope (< 200 ms for `lookup(mode=search)`
BM25 build). Two new tools add ~O(k) to BM25 index; immaterial.
**Constraints**: Fail-closed defaults (Constitution §II). Pydantic v2 strict
`extra="forbid", frozen=True` on all input models (Constitution §III). Bilingual
(Korean + English) `search_hint` required (Constitution §III). No live
`data.go.kr` calls from CI (Constitution §IV).
**Scale/Scope**: Two adapters, one shared SSIS code-table module
(`src/kosmos/tools/ssis/codes.py`), two `TOOL_MIN_AAL` additions, one DPA
placeholder stub, two documentation entries. 8 new source files, 7 new test
files, 2 modified source files. No net dependency change.

## Constitution Check

*GATE: Passed pre-Phase 0 and re-checked post-Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| I. Reference-Driven Development | PASS | `research.md §2` maps every decision to a concrete reference (NMC adapter, HIRA adapter, `GovAPITool` validators, `TOOL_MIN_AAL`, `docs/vision.md § Reference materials`). No ADR required. |
| II. Fail-Closed Security | PASS | Both adapters default `requires_auth=True`; MOHW `is_personal_data=True`; MOHW `cache_ttl_seconds=0`; `is_concurrency_safe` set to `True` only on read-only endpoints. Missing `serviceKey` returns `upstream_unavailable, retryable=False`. |
| III. Pydantic v2 Strict Typing | PASS | All input models use `ConfigDict(extra="forbid", frozen=True)`. Output models use `extra="allow"` only on upstream item schemas (forward-compat with NFA sparse fields) — the envelope itself is `extra="forbid"`. No `Any` in schema field types. Bilingual `search_hint` on both adapters. |
| IV. Government API Compliance | PASS | `research.md §7` prescribes recorded fixtures only; `rate_limit_per_minute=10` on both; `KOSMOS_DATA_GO_KR_API_KEY` reused, no hardcoded keys; happy-path + error-path tests required per spec §4. |
| V. Policy Alignment | PASS | Both adapters serve Principle 8 (single conversational window) by being discoverable through `lookup(mode=search)`. Principle 9 (Open API) is satisfied — these are data.go.kr endpoints. MOHW PII gate (PIPA §26 처리위탁 + `dpa_reference`) documented in `research.md §3 C3`. |
| VI. Deferred Work Accountability | PASS | `research.md §1` validates 8 deferred items against Epic issues. Item #8 (`nfa_safety_center_lookup`) flagged `NEEDS TRACKING` for `/speckit-taskstoissues` back-fill. §9.2–§9.4 extension-path items are future adapters, not deferrals of in-scope work (constitutional interpretation documented). |

**Complexity Tracking**: No violations. No entries in the Complexity Tracking
table below.

## Project Structure

### Documentation (this feature)

```text
specs/029-phase2-adapters-119-mohw/
├── spec.md              # /speckit-specify output (706 lines)
├── plan.md              # this file
├── research.md          # Phase 0 output — deferred-items gate, reference map, C1/C2/C3 resolutions
├── data-model.md        # Phase 1 output — shared SSIS codes, NFA/MOHW I/O models, registration blocks, TOOL_MIN_AAL diff, file manifest
├── quickstart.md        # Phase 1 output — local dev setup + test runbook
├── contracts/           # Phase 1 output — JSON Schema exports for both adapters
│   ├── nfa_emergency_info_service.input.schema.json
│   ├── nfa_emergency_info_service.output.schema.json
│   ├── mohw_welfare_eligibility_search.input.schema.json
│   └── mohw_welfare_eligibility_search.output.schema.json
└── tasks.md             # /speckit-tasks output — NOT created here
```

### Source Code (repository root — KOSMOS single-project layout)

The project is a **single-project Python library + backend** (no `backend/` +
`frontend/` split; TUI lives in its own repo). Source tree touched by this spec:

```text
src/kosmos/
├── tools/
│   ├── nfa119/                              # NEW package
│   │   ├── __init__.py                      # NEW
│   │   └── emergency_info_service.py        # NEW — NfaEmergencyInfoServiceInput + NFA_EMERGENCY_INFO_SERVICE_TOOL + interface-only handle()
│   ├── ssis/                                # NEW package
│   │   ├── __init__.py                      # NEW
│   │   ├── codes.py                         # NEW — shared LifeArrayCode / TrgterIndvdlCode / IntrsThemaCode / SrchKeyCode / OrderBy / CallType enums
│   │   └── welfare_eligibility_search.py    # NEW — MohwWelfareEligibilitySearchInput + MOHW_WELFARE_ELIGIBILITY_SEARCH_TOOL + interface-only handle()
│   ├── register_all.py                      # MOD — add register() calls for both new adapters
│   ├── errors.py                            # unchanged (Layer3GateViolation already present)
│   ├── envelope.py                          # unchanged
│   └── models.py                            # unchanged (V1–V6 validators fire on new tool construction)
├── security/
│   └── audit.py                             # MOD — TOOL_MIN_AAL adds two rows (nfa AAL1, mohw AAL2)
docs/
├── tools/
│   ├── nfa119.md                            # NEW — provider-level documentation entry
│   └── ssis.md                              # NEW — provider-level documentation entry
└── security/
    └── dpa/
        └── dpa-ssis-welfare-v1.md           # NEW — placeholder stub reserving validator V2 identifier

tests/
├── tools/
│   ├── nfa119/
│   │   ├── __init__.py                      # NEW
│   │   └── test_nfa_emergency_info_service.py   # NEW — schema happy + error, Layer3GateViolation, executor auth_required short-circuit, BM25 top-5
│   └── ssis/
│       ├── __init__.py                      # NEW
│       ├── test_codes.py                    # NEW — enum coverage
│       └── test_mohw_welfare_eligibility_search.py  # NEW — same shape as NFA
└── fixtures/
    ├── nfa119/
    │   └── nfa_emergency_info_service.json  # NEW — synthetic (docx sample values: 충청남도소방본부 / 천안동남소방서 / 202112 / 기침 / 60~69세)
    └── ssis/
        └── mohw_welfare_eligibility_search.json  # NEW — synthetic (WLF0000001188 / 출산가정 방문서비스 / 보건복지부)
```

**Structure Decision**: KOSMOS single-project Python backend with the existing
`src/kosmos/tools/<provider>/` convention (same shape as `nmc/`, `hira/`,
`kma/`, `koroad/`). No new top-level layout. No new module naming pattern.
The shared SSIS codes module (`src/kosmos/tools/ssis/codes.py`) anticipates the
future `ssis_welfare_detail_fetch` adapter (spec §9.2) and prevents enum
duplication from day one.

## Complexity Tracking

> No Constitution violations. This table is intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |
