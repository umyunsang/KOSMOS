# Implementation Plan: NMC Freshness SLO Enforcement

**Branch**: `023-nmc-freshness-slo` | **Date**: 2026-04-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/023-nmc-freshness-slo/spec.md`

## Summary

Add freshness validation to the NMC emergency room adapter: compare the `hvidate` timestamp in every NMC response against `KOSMOS_NMC_FRESHNESS_MINUTES`, return `LookupError(reason="stale_data")` when stale, and inject `freshness_status` metadata into the response envelope when fresh. No new dependencies or layers; this is a Phase 1 quality hardening of existing Tool System infrastructure.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: pydantic >= 2.13, httpx >= 0.27 (existing)
**Storage**: N/A (in-memory validation only)
**Testing**: pytest + pytest-asyncio, fixture-based (no live API calls)
**Target Platform**: Linux / macOS server
**Project Type**: Library (backend tool system module)
**Performance Goals**: Freshness check adds < 1ms overhead per response
**Constraints**: No new runtime dependencies; fail-closed on missing/unparseable hvidate
**Scale/Scope**: Single adapter (nmc_emergency_search); pattern may be reused by future adapters

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Reference-Driven Development | PASS | Freshness SLO pattern references Layer 2 Tool System (Pydantic AI schema-driven registry) and Layer 6 Error Recovery (fail-closed defaults). No new architectural pattern introduced. |
| II. Fail-Closed Security | PASS | Missing/unparseable `hvidate` → treated as stale (FR-008). `stale_data` error returned, data never silently passed. Consistent with `requires_auth=True`, `is_personal_data=True` defaults. |
| III. Pydantic v2 Strict Typing | PASS | `freshness_status` added as Literal field on `LookupMeta`. `hvidate` parsing produces typed datetime. No `Any` types. |
| IV. Government API Compliance | PASS | No live `data.go.kr` calls in CI tests. All tests use recorded fixtures. `KOSMOS_NMC_FRESHNESS_MINUTES` read from env var. |
| V. Policy Alignment | PASS | Freshness enforcement prevents delivery of stale emergency data to citizens — safety-first per Principle 8 (single conversational window quality). |
| VI. Deferred Work Accountability | PASS | No items deferred. All requirements addressed in this epic. |

## Project Structure

### Documentation (this feature)

```text
specs/023-nmc-freshness-slo/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/kosmos/
├── settings.py                          # KOSMOS_NMC_FRESHNESS_MINUTES (existing, no changes)
└── tools/
    ├── models.py                        # LookupMeta.freshness_status field (new)
    ├── envelope.py                      # No changes required
    ├── errors.py                        # LookupErrorReason.stale_data (existing, no changes)
    └── nmc/
        ├── __init__.py                  # No changes
        ├── emergency_search.py          # freshness validation logic (modified)
        └── freshness.py                 # Freshness check utility (new)

tests/
├── fixtures/nmc/
│   ├── auth_required_error.json         # Existing
│   ├── fresh_response.json              # New fixture: hvidate within threshold
│   └── stale_response.json              # New fixture: hvidate beyond threshold
└── tools/nmc/
    ├── test_emergency_search_auth_gate.py  # Existing, no changes
    └── test_freshness_validation.py        # New: freshness check unit tests
```

**Structure Decision**: Freshness validation lives in `src/kosmos/tools/nmc/freshness.py` as a standalone utility module, keeping the adapter handler (`emergency_search.py`) focused on HTTP orchestration. The utility is NMC-specific (hvidate field semantics) so it belongs in the `nmc/` package, not in the generic tool system.

## Complexity Tracking

No constitution violations. No complexity justifications needed.
