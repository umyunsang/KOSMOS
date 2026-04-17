# Implementation Plan: Tool Template Security Spec V6 — `auth_type` ↔ `auth_level` consistency invariant

**Branch**: `025-tool-security-v6` | **Date**: 2026-04-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/025-tool-security-v6/spec.md`

## Summary

Close the defense-in-depth gap identified by Codex P1 review on PR #653: a future `GovAPITool` with `auth_type="public" + auth_level="AAL2" + requires_auth=True` currently passes V1–V5 but is anonymously callable through the legacy `PermissionPipeline.dispatch()` path, which derives its access tier from `auth_type` alone. V6 adds a canonical `auth_type → {auth_level}` mapping enforced at two layers: (1) a pydantic v2 `@model_validator(mode="after")` on `GovAPITool`, and (2) an independent registry backstop in `ToolRegistry.register()` that re-checks the mapping so `model_construct` / `object.__setattr__` bypasses cannot land. The security spec document is updated to v1.1 with the canonical mapping matrix, a worked `public + AAL1 + requires_auth=True` example, and the dispatch-path rationale. No runtime dependency changes; no `PermissionPipeline.dispatch()` refactor (tracked separately).

## Technical Context

**Language/Version**: Python 3.12+ (existing project baseline; no version bump).
**Primary Dependencies**: `pydantic >= 2.13` (existing — V1–V5 use `@model_validator(mode="after")`), `pytest` + `pytest-asyncio` (existing). **No new runtime dependencies** (AGENTS.md hard rule).
**Storage**: N/A — this is a validator + backstop spec; no persistent state. The canonical mapping lives as code (validator module-level constant) and as documentation (`docs/security/tool-template-security-spec-v1.md` v1.1 matrix).
**Testing**: `pytest` unit tests in `tests/tools/test_gov_api_tool_extensions.py` (positive + negative per `(auth_type, auth_level)` pair) and `tests/tools/test_registry_invariant.py` (registry backstop + pydantic-bypass scenarios + registry-wide scan test). No `@pytest.mark.live` tests. All tests deterministic and run in the default CI suite.
**Target Platform**: Linux/macOS server (existing KOSMOS backend).
**Project Type**: Single project (Python package under `src/kosmos/`).
**Performance Goals**: Validator + backstop MUST NOT regress `GovAPITool` construction or `ToolRegistry.register()` beyond sub-millisecond per tool (pure dict/set lookup; no I/O). The registry-wide scan test MUST complete in <1 second for the current 6-adapter registry.
**Constraints**:
- Fail-closed on unknown `auth_type` or `auth_level` (FR-048, Constitution §II).
- Error message MUST name both offending fields and the allowed set (FR-041).
- Backstop error MUST be distinguishable from pydantic error (FR-043).
- V1–V5 MUST continue to run unchanged (FR-047, SC-005).
- Every existing adapter MUST pass V6 with no configuration change (FR-044, SC-001).
**Scale/Scope**: 6 existing tool adapters (KOROAD accident-hazard-search, KMA forecast-fetch, HIRA hospital-search, NMC emergency-search, `resolve_location`, `lookup`). Scope bounded to `src/kosmos/tools/models.py`, `src/kosmos/tools/registry.py`, two test modules, and one documentation file.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` v1.1.0:

| Principle | Status | Notes |
|---|---|---|
| I. Reference-Driven Development | PASS | Every V6 design decision maps to a concrete reference in `docs/vision.md § Reference materials`: (a) Pydantic v2 `@model_validator(mode="after")` pattern for FR-039 (already used by V1–V5 in `src/kosmos/tools/models.py:166-238`); (b) V3 FR-038 registry-backstop pattern for FR-042 (existing code in `src/kosmos/tools/registry.py:39-79`); (c) V1 spec document structure for FR-046 (existing `docs/security/tool-template-security-spec-v1.md`). See `research.md` for the per-decision mapping. |
| II. Fail-Closed Security (NON-NEGOTIABLE) | PASS | FR-048 mandates fail-closed on unknown `auth_type` or `auth_level` values. FR-042 registry backstop ensures pydantic-bypass cannot land an unsafe tool. No mode or shortcut can relax V6 (validator runs unconditionally in `model_validator(mode="after")`). |
| III. Pydantic v2 Strict Typing (NON-NEGOTIABLE) | PASS | V6 uses an existing `@model_validator(mode="after")` chain. No new `Any` types introduced. `auth_type: Literal["public", "api_key", "oauth"]` and `auth_level: AALLevel` remain the strict-typed fields; V6 checks their relation. |
| IV. Government API Compliance | PASS | No live API calls. All tests use constructed `GovAPITool` instances; no `@pytest.mark.live`. |
| V. Policy Alignment | PASS | V6 reinforces PIPA §26 (위탁자) safeguards by preventing a future configuration that would expose AAL2 tools as anonymous. Aligns with Principle 8 (single conversational window — must not silently anonymize AAL-gated services). |
| VI. Deferred Work Accountability | PASS | `spec.md` § Scope Boundaries explicitly tracks `PermissionPipeline.dispatch()` refactor and `dispatch/invoke` unification as `NEEDS TRACKING` → `/speckit-taskstoissues` will create placeholder issues. TUI (#287), Agent Swarm Core (#576), additional adapters (#579, #643) are explicitly referenced with issue numbers. No free-text "separate epic" prose without a table entry. |

**Gate verdict**: PASS. No violations to justify in the Complexity Tracking table.

## Project Structure

### Documentation (this feature)

```text
specs/025-tool-security-v6/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output — reference mapping + deferred-item validation
├── data-model.md        # Phase 1 output — canonical mapping table + V6 error contract
├── quickstart.md        # Phase 1 output — adapter-author quickstart for V6
├── contracts/           # Phase 1 output — V6 validator + backstop error contracts
│   └── v6-error-contract.md
├── checklists/
│   └── requirements.md  # /speckit.specify self-validation (completed)
├── spec.md              # Feature specification (approved)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
src/kosmos/
├── tools/
│   ├── models.py        # EDIT: extend _validate_security_invariants with V6 block
│   ├── registry.py      # EDIT: add V6 backstop in ToolRegistry.register() mirroring FR-038 pattern
│   └── ...              # unchanged
└── security/
    └── audit.py         # unchanged (TOOL_MIN_AAL stays the V3 SoT)

tests/
└── tools/
    ├── test_gov_api_tool_extensions.py  # EDIT: add V6 positive + negative cases for every (auth_type, auth_level) pair
    └── test_registry_invariant.py       # EDIT: add V6 backstop test + registry-wide scan test

docs/
└── security/
    └── tool-template-security-spec-v1.md  # EDIT: append "V6: auth_type ↔ auth_level consistency" section, bump to v1.1
```

**Structure Decision**: Single-project layout. V6 is a targeted extension of the existing `src/kosmos/tools/` module. No new packages, no new submodules, no new configuration surface. The changes live in exactly 5 files (2 source, 2 test, 1 doc).

## Complexity Tracking

> No Constitution Check violations. Table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |
