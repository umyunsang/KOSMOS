# Implementation Plan: Tool Template Security Spec v1 — Ministry-PR-ready hardening

**Branch**: `024-tool-security-v1` | **Date**: 2026-04-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/024-tool-security-v1/spec.md`

## Summary

Synthesize six security research lanes (Epic #605) plus the cross-lane consistency review into a single normative Tool Template Security Spec v1, hardened to a level a Korean ministry reviewer can accept for a PR/trial partnership.

**Primary outputs** (spec-deliverable layer):

1. Normative document `docs/security/tool-template-security-spec-v1.md` — threats, controls, invariants, PR checklist diff, with every control citing at least one Korean statutory artifact (PIPA, 전자정부법, 전자서명법, K-ISMS-P) and at least one international standard (NIST SP 800-63-4, OWASP ASVS 4.0, OWASP Top 10 for LLM, ISO 27001, NIST SP 800-207).
2. Pydantic v2 `ToolCallAuditRecord` model + JSON Schema Draft 2020-12 artifact under `docs/security/` (schema) and `src/kosmos/security/audit.py` (model seed).
3. `GovAPITool` schema extension at `src/kosmos/tools/models.py` adding four mandatory fields: `auth_level`, `pipa_class`, `is_irreversible`, `dpa_reference`.
4. OpenAPI 3.0 skeleton `docs/security/agent-delegation.openapi.yaml` covering consent creation, token issuance/refresh/introspection/revocation, grounded only in IETF RFCs (8628, 8693, 9068, 7636, 7662, 7009) and W3C VC Data Model v2.0 / DID Core.
5. `docs/tool-adapters.md` PR checklist extension — minimum 5 new unified items covering the six research-lane domains.
6. GitHub Actions SBOM workflow scaffold `.github/workflows/sbom.yml` — emits SPDX 2.3 and CycloneDX 1.6 on every push to `main` and every tag, with build-gate behavior on divergence.

**Pre-decided design inputs** (not re-litigated during planning):

- `check_eligibility` min AAL = **AAL2** with explicit `public_path` marker for rules-only AAL1 fallback over public inputs with no PII either direction.
- NIST citations migrate from withdrawn SP 800-63-3 to **SP 800-63-4**.
- Audit retention = **5 years** (binding maximum of PIPA 안전조치 고시 §8 two-year floor and 전자정부법 §33 five-year floor).
- `ToolCallAuditRecord` includes `sanitized_output_hash: Optional[str]` plus `merkle_covered_hash` declaration field.
- PIPA role = **§26 수탁자 default** + **LLM 합성 단계 controller-level carve-out**, documented; PIPC 유권해석 질의서 tracked as a parallel legal track, not a v1 blocker.

**What this spec is NOT**: full mock-tool implementation, full Merkle chain construction, full `/agent-delegation` server-side implementation, full PIPC 유권해석 drafting. These are deferred with `NEEDS TRACKING` markers.

## Technical Context

**Language/Version**: Python 3.12+ (existing project baseline; no version bump required for this spec).
**Primary Dependencies**: Pydantic v2 (existing), `httpx >=0.27` (existing, not exercised by this spec's code seed), `pytest` + `pytest-asyncio` (existing). No new runtime dependencies introduced. JSON Schema Draft 2020-12 and OpenAPI 3.0 are specification targets, not dependencies; they are validated externally.
**Storage**: N/A at this layer. `ToolCallAuditRecord` is a schema contract. Actual append-only audit storage and Merkle chain construction are explicitly deferred.
**Testing**: `pytest` unit tests for the extended `GovAPITool` registration invariants and the `ToolCallAuditRecord` round-trip validation. `@pytest.mark.live` is not exercised — the spec does not call external systems. JSON Schema validation of three worked audit-record examples is a CI step.
**Target Platform**: Linux CI runner for SBOM workflow; macOS/Linux dev machines for Python-side changes. Pure-documentation artifacts are platform-agnostic.
**Project Type**: Single project (spec + code seed within existing `src/kosmos/` tree). No new deployable surface.
**Performance Goals**: None for the normative spec itself. The `ToolCallAuditRecord` model MUST validate in < 5 ms per record under pydantic v2 `model_validate` to ensure per-call overhead is negligible when the Merkle chain construction per Deferred Items row "Full Merkle audit chain implementation" lands.
**Constraints**: Strict fail-closed semantics at `ToolRegistry.register()` — any missing or inconsistent new `GovAPITool` field raises at load time. No silent defaults for `auth_level`, `pipa_class`, `is_irreversible`, or `dpa_reference`.
**Scale/Scope**: Covers 8 canonical tools (`lookup`, `pay`, `issue_certificate`, `submit_application`, `reserve_slot`, `subscribe_alert`, `resolve_location`, `check_eligibility`) — the full KOSMOS Tool Template surface. Spec length estimate: 2,500-3,500 lines of normative prose plus artifacts.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Justification |
|---|---|---|
| **I. Reference-Driven Development** | PASS | Every control traces to a concrete reference. Layer 3 (Permission Pipeline) maps to OpenAI Agents SDK guardrail pipeline (primary) + Claude Code reconstructed permission model (secondary) per `docs/vision.md § Reference materials`. Supply-chain controls cite SLSA v1.0 and sigstore/Rekor. Audit record schema cites RFC 9162 Sunlight Merkle and Google Trillian patterns. Identity/delegation cites IETF RFCs and W3C VC/DID recommendations only. |
| **II. Fail-Closed Security (NON-NEGOTIABLE)** | PASS | FR-004 preserves and extends the FR-038 invariant: `pipa_class != non_personal → auth_level != public`. FR-005 rejects registration of any tool missing the four new fields. FR-006 mandates deny-by-default at the permission pipeline. FR-007 requires live token introspection for irreversible actions regardless of cache. |
| **III. Pydantic v2 Strict Typing (NON-NEGOTIABLE)** | PASS | `ToolCallAuditRecord` uses Pydantic v2 with `ConfigDict(frozen=True)`. `GovAPITool` extension uses existing pydantic-v2 patterns. All four new fields use `Literal` / typed enums / `Optional[str]`; no `Any` introduced anywhere. |
| **IV. Government API Compliance** | PASS | Spec adds controls on top of the existing compliance baseline without relaxing any. No live API calls are introduced by this spec; audit record testing uses synthetic fixtures. |
| **V. Policy Alignment** | PASS | Spec materially advances Principle 8 (single conversational window) by codifying a ministry-acceptable trust model; Principle 9 (Open API / OpenMCP) by standing up an IETF/W3C-only delegation protocol any ministry can adopt; Principle 5 (consent-based access) by adding `dpa_reference` and `synthesis_consent` to every PII-bound consent record. Public AI Impact Assessment (과제 54) addressed via FR-008 deny-by-default and FR-010 tamper-evident audit. |
| **VI. Deferred Work Accountability** | PASS | 7 deferred items tabulated with `NEEDS TRACKING` markers for resolution at `/speckit-taskstoissues`. 3 permanent out-of-scope items listed with justification. Grep-verified: zero unregistered "separate epic" / "future phase" / "v2" patterns in spec prose. |

**Gate result**: all 6 principles PASS. No complexity-tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/024-tool-security-v1/
├── plan.md                 # This file (/speckit-plan output)
├── spec.md                 # /speckit-specify output (done)
├── research.md             # Phase 0 output (/speckit-plan)
├── data-model.md           # Phase 1 output (/speckit-plan)
├── quickstart.md           # Phase 1 output (/speckit-plan)
├── contracts/
│   ├── tool-call-audit-record.schema.json   # Phase 1 (JSON Schema Draft 2020-12)
│   └── agent-delegation.openapi.yaml        # Phase 1 (OpenAPI 3.0 skeleton)
├── checklists/
│   └── requirements.md     # /speckit-specify output (done, all PASS)
└── tasks.md                # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/kosmos/
├── tools/
│   └── models.py           # EXTEND: add auth_level, pipa_class, is_irreversible, dpa_reference to GovAPITool
├── security/               # NEW module for this spec
│   └── audit.py            # NEW: ToolCallAuditRecord pydantic v2 model + Merkle coverage helpers (schema-only, no storage)
└── permissions/
    └── (unchanged — full permission pipeline wiring is deferred per the Deferred Items row "Full permission pipeline wiring"; this spec only lands the model contract)

docs/
├── security/               # NEW directory for this spec
│   ├── tool-template-security-spec-v1.md       # NEW: normative spec
│   ├── tool-call-audit-record.schema.json      # NEW: JSON Schema artifact (mirrors contracts/)
│   └── agent-delegation.openapi.yaml           # NEW: OpenAPI 3.0 skeleton (mirrors contracts/)
└── tool-adapters.md        # EXTEND: PR checklist +5 unified items

tests/
├── unit/
│   ├── test_gov_api_tool_extensions.py     # NEW: fail-closed registration invariants
│   └── test_tool_call_audit_record.py      # NEW: round-trip + schema validation for 3 worked examples
└── (integration/live unchanged — this spec does not add cross-boundary tests)

.github/workflows/
└── sbom.yml                # NEW: SPDX 2.3 + CycloneDX 1.6 generation on push to main + tag release
```

**Structure Decision**: Single project (Option 1). The spec extends the existing `src/kosmos/` tree with a new `security/` submodule for audit-record typing and extends `tools/models.py` for the `GovAPITool` field additions. Documentation lands under a new `docs/security/` directory. No new top-level projects, no new deployable services, no TypeScript surface. This keeps the spec's code footprint minimal (the model contract plus registration invariants) while the full enforcement pipeline, Merkle chain construction, and delegation endpoint implementation land in separate epics per the Deferred Items table.

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.
