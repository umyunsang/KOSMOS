# Data Model: Tool Template Security Spec v1

**Feature**: 024-tool-security-v1
**Date**: 2026-04-17
**Phase**: 1 (Design & Contracts)

## 0. Scope

This document defines the pydantic v2 models and static lookup structures the spec introduces. Every model below is a **schema contract**. Backing stores (append-only audit log, Merkle chain, delegation-token database, consent registry) are explicitly deferred — this spec only lands the typed contracts those stores will validate against.

All models use pydantic v2 with `ConfigDict(frozen=True)` unless otherwise noted. `Any` is forbidden per Constitution III.

## 1. `GovAPITool` — extended registry entry

**Location**: `src/kosmos/tools/models.py` (existing model; extended in this spec).

**Existing fields** (unchanged): `id`, `name_ko`, `provider`, `category`, `endpoint`, `auth_type`, `input_schema`, `output_schema`, `search_hint`, `requires_auth` (default `True`), `is_concurrency_safe` (default `False`), `is_personal_data` (default `True`), `cache_ttl_seconds` (default `0`), `rate_limit_per_minute`, `is_core`, `llm_description`.

**New fields added by this spec**:

| Field | Type | Required | Default | Semantics |
|---|---|---|---|---|
| `auth_level` | `Literal["public", "AAL1", "AAL2", "AAL3"]` | Yes | — | Minimum NIST SP 800-63-4 AAL required to invoke the tool. MUST match the tool's row in `TOOL_MIN_AAL`. |
| `pipa_class` | `Literal["non_personal", "personal", "sensitive", "identifier"]` | Yes | — | PIPA classification of input-or-output data. `personal` = 개인정보 (PIPA §2.1). `sensitive` = 민감정보 (PIPA §23). `identifier` = 고유식별정보 (PIPA §24). |
| `is_irreversible` | `bool` | Yes | — | True when invocation produces a side effect the citizen cannot undo via a second tool call (e.g., `pay`, `submit_application`). Drives FR-007 live-introspection requirement. |
| `dpa_reference` | `Optional[str]` | Conditional | `None` | Identifier of the DPA template governing the §26 processor chain for this tool's scope. MUST be non-null whenever `pipa_class != "non_personal"`. |

**Cross-field validators** (enforced at `ToolRegistry.register()`):

- `V1`: `pipa_class != "non_personal"` → `auth_level != "public"` (extends FR-038 invariant).
- `V2`: `pipa_class != "non_personal"` → `dpa_reference is not None` (closes PIPA §26 위탁 documentation gap).
- `V3`: `auth_level` MUST equal the tool's row in `TOOL_MIN_AAL` (single source of truth).
- `V4`: `is_irreversible = True` → `auth_level != "public"` (irreversible actions cannot run unauthenticated).

Violations raise `ValueError` at registration time — no silent defaults, no recoverable mode.

**Backwards compatibility**: All 4 new fields are required on new registrations. A migration pass annotates the 4 seed adapters (`koroad_accident_hazard_search`, `kma_forecast_fetch`, `hira_hospital_search`, `nmc_emergency_search`) plus any MVP adapters in-tree. Load-time failure is preferred over silent defaulting.

## 2. `TOOL_MIN_AAL` — static lookup table

**Location**: `src/kosmos/security/audit.py` (new module) as a `Final[dict[str, str]]` plus a dataclass for `public_path` metadata.

| Tool ID | Min AAL | `public_path` | Rationale |
|---|---|---|---|
| `lookup` | `AAL1` | — | Default search surface; PII-class inputs raise via `pipa_class` checks. |
| `resolve_location` | `AAL1` | — | Public geospatial query. |
| `check_eligibility` | `AAL2` | **Yes** — AAL1 permitted for rules-only evaluation over public inputs with no PII in request or response | Pre-decided resolution; rules-only fallback preserves public-goods use case. |
| `subscribe_alert` | `AAL2` | — | Contact information is PII. |
| `reserve_slot` | `AAL2` | — | Creates a citizen-identified reservation record. |
| `issue_certificate` | `AAL3` | — | Authoritative document issuance (주민등록등본 등). |
| `submit_application` | `AAL2` | — | Civic application with downstream legal effect. |
| `pay` | `AAL3` | — | Financial action with irrevocable consequences. |

**Consistency invariant**: every `GovAPITool.auth_level` MUST equal its row here (V3 above). Drift is a load-time failure.

## 3. `ToolCallAuditRecord` — immutable evidence artifact

**Location**: `src/kosmos/security/audit.py` (new module).

**Model shape** (pydantic v2, `frozen=True`):

| Field | Type | Required | Notes |
|---|---|---|---|
| `record_version` | `Literal["v1"]` | Yes | Schema version lock. |
| `tool_id` | `str` | Yes | Matches `GovAPITool.id`. |
| `adapter_mode` | `Literal["mock", "live"]` | Yes | Only permitted shape-differing field between mock and live (FR-012). |
| `session_id` | `str` | Yes | Opaque session identifier (UUIDv7 recommended; not mandated at schema level). |
| `caller_identity` | `str` | Yes | Opaque identity token — NOT a resident registration number. |
| `permission_decision` | `Literal["allow", "deny_aal", "deny_scope", "deny_irreversible_introspect_failed", "deny_deny_by_default"]` | Yes | Deny variants are first-class to satisfy FR-006 evidentiary parity. |
| `auth_level_presented` | `Literal["public", "AAL1", "AAL2", "AAL3"]` | Yes | What the caller proved, not what the tool required. |
| `pipa_class` | `Literal["non_personal", "personal", "sensitive", "identifier"]` | Yes | Classification of THIS call's payload, not the adapter default. |
| `dpa_reference` | `Optional[str]` | Conditional | Non-null whenever `pipa_class != "non_personal"`. |
| `input_hash` | `str` | Yes | Hex-encoded SHA-256 of the canonicalized input payload. |
| `output_hash` | `str` | Yes | Hex-encoded SHA-256 of the raw output payload. |
| `sanitized_output_hash` | `Optional[str]` | No | Hex-encoded SHA-256 of the sanitized output, when sanitization ran. |
| `merkle_covered_hash` | `Literal["sanitized_output_hash", "output_hash"]` | Yes | Declares which hash the Merkle leaf binds. `sanitized_output_hash` when present, `output_hash` otherwise. |
| `merkle_leaf_id` | `Optional[str]` | No | Leaf identifier in the external Merkle chain (chain construction is deferred). |
| `timestamp` | `datetime` | Yes | RFC 3339 with timezone (pydantic enforces via `datetime` with `tzinfo`). |
| `cost_tokens` | `int` | Yes | LLM token cost if applicable; `0` for pure-tool calls. |
| `rate_limit_bucket` | `str` | Yes | Bucket identifier for per-provider/per-key quota accounting. |
| `public_path_marker` | `bool` | Yes | `True` only for `check_eligibility` AAL1 rules-only evaluations. |

**Invariants** (pydantic `model_validator`):

- `I1`: `sanitized_output_hash is not None` ↔ `merkle_covered_hash == "sanitized_output_hash"`.
- `I2`: `public_path_marker = True` → `tool_id == "check_eligibility"` AND `auth_level_presented == "AAL1"` AND `pipa_class == "non_personal"`.
- `I3`: `pipa_class != "non_personal"` → `dpa_reference is not None`.
- `I4`: `timestamp.tzinfo is not None` (RFC 3339 naïve timestamps rejected).

**Mock/live parity**: a mock call and a live call for the same tool MUST produce records identical in shape. Only `adapter_mode` differs.

**Performance**: `ToolCallAuditRecord.model_validate` target < 5 ms per record (validated in unit test, not enforced in schema).

## 4. `DelegationToken` — delegated-authority artifact

**Location**: OpenAPI skeleton only (`contracts/agent-delegation.openapi.yaml`). Pydantic model implementation is deferred to the `/agent-delegation` endpoint epic (D2).

**Fields** (documented here for schema completeness; no in-tree pydantic model lands in this spec):

| Field | Type | Required | Notes |
|---|---|---|---|
| `token_id` | `str` | Yes | Opaque identifier. |
| `aal_asserted` | `Literal["AAL1", "AAL2", "AAL3"]` | Yes | AAL of the underlying citizen authentication event. |
| `scope` | `list[str]` | Yes | Each entry has shape `<tool_id>:<verb>[:resource]` (e.g., `issue_certificate:resident_registration`). |
| `expires_at` | `datetime` | Yes | RFC 3339 timezone-aware. |
| `introspection_endpoint` | `str (URI)` | Yes | Per RFC 7662. |
| `revocation_endpoint` | `str (URI)` | Yes | Per RFC 7009. |
| `issuer` | `str` | Yes | Ministry or KOSMOS-as-broker identifier. |
| `audience` | `str` | Yes | `kosmos-agent` for the default agent audience. |
| `dpa_reference` | `Optional[str]` | Conditional | Non-null when any scope entry is PII-bound. |

## 5. `ConsentRecord` — citizen consent artifact

**Location**: OpenAPI skeleton only (same deferral as §4).

**Fields**:

| Field | Type | Required | Notes |
|---|---|---|---|
| `consent_id` | `str` | Yes | Opaque identifier. |
| `citizen_identity` | `str` | Yes | Opaque citizen identifier bound by PASS/공동인증서 at collection time; not re-exported. |
| `scopes` | `list[str]` | Yes | Same shape as `DelegationToken.scope`. |
| `dpa_reference` | `Optional[str]` | Conditional | Non-null when any scope is PII-bound. |
| `synthesis_consent` | `bool` | Yes | Separate consent for LLM-synthesis carve-out. |
| `collected_at` | `datetime` | Yes | RFC 3339 timezone-aware. |
| `expires_at` | `datetime` | Yes | RFC 3339 timezone-aware. |
| `revoked_at` | `Optional[datetime]` | No | Set by revocation flow per RFC 7009. |

**Invariants**: `any(scope is PII-bound for scope in scopes) → dpa_reference is not None`.

## 6. `SBOMArtifact` — build-time provenance record

**Location**: `.github/workflows/sbom.yml` (workflow artifact declaration). No in-tree pydantic model — this is a CI artifact pair, not a runtime object.

**Shape**:

| Attribute | Value |
|---|---|
| Formats | SPDX 2.3 **and** CycloneDX 1.6 (both MUST be produced) |
| Triggers | push to `main`, tag release |
| Source inputs | `pyproject.toml` + `uv.lock` |
| Signing | sigstore/cosign (target posture; CI scaffold in this spec, full signing is deferred per the Deferred Items row "Full SBOM signing (sigstore/cosign end-to-end)") |
| Divergence policy | Build fails on SBOM diff vs last-signed artifact; recovery requires signed regeneration + reviewer note |

## 7. Entity relationships

```text
GovAPITool  ─(registers)─▶  ToolRegistry
     │                            │
     │ auth_level matches         │
     ▼                            ▼
TOOL_MIN_AAL                  (at call time)
                                  │
                                  ▼
DelegationToken ─(authorizes)─▶ permission pipeline
     │                            │
     │ references                 │ emits
     ▼                            ▼
ConsentRecord ─(dpa_reference)─▶ ToolCallAuditRecord
                                  │
                                  │ merkle_covered_hash binds
                                  ▼
                            external Merkle chain (deferred)

SBOMArtifact ── (independent, build-time) ── CI workflow
```

## 8. Validation surface (tests)

Two new test modules under `tests/unit/`:

- `test_gov_api_tool_extensions.py` — covers FR-003, FR-004, FR-005, and validators V1-V4. Every existing adapter in-tree MUST register cleanly with the new fields populated; a test fixture deliberately omits each of the 4 new fields in turn and asserts load-time rejection.
- `test_tool_call_audit_record.py` — covers FR-009, FR-010, FR-012, invariants I1-I4. Includes three worked example records satisfying SC-004: (a) successful authenticated call, (b) rejected-for-insufficient-AAL call, (c) `check_eligibility` `public_path` call. Each example also validates against `contracts/tool-call-audit-record.schema.json` in CI.

JSON Schema validation is run via `jsonschema` (already a transitive dep; verified in Phase 2 if not, fallback is a test-only extra).
