# Quickstart: Tool Template Security Spec v1

**Feature**: 024-tool-security-v1
**Audience**: KOSMOS contributors (human or agent) shipping a tool adapter after this spec lands.
**Prereq**: Read `spec.md § Requirements` and `data-model.md § 1`.

## 1. Register a new adapter — all four new fields are mandatory

Every `GovAPITool` registration MUST populate all four new fields. Missing or inconsistent fields fail load-time.

```python
from kosmos.tools.models import GovAPITool

tool = GovAPITool(
    id="issue_certificate_resident_registration",
    name_ko="주민등록등본 발급 의뢰",
    provider="gov.mois",
    category="issue_certificate",
    endpoint="https://api.example.gov.kr/resident/issue",
    auth_type="oauth",
    input_schema=IssueResidentRegistrationInput,
    output_schema=IssueResidentRegistrationOutput,
    search_hint="주민등록등본 resident registration certificate",
    rate_limit_per_minute=10,
    llm_description="Request issuance of a resident registration certificate.",
    # NEW in spec 024 — all four required:
    auth_level="AAL3",              # MUST match TOOL_MIN_AAL row
    pipa_class="identifier",        # 고유식별정보 (PIPA §24)
    is_irreversible=True,           # issuing a certificate is an authoritative record event
    dpa_reference="DPA-MOIS-2026-01",
)
```

**Fail-closed validators enforce**:

- `pipa_class != "non_personal"` → `auth_level != "public"` (extends FR-038).
- `pipa_class != "non_personal"` → `dpa_reference is not None`.
- `auth_level` MUST equal the tool's `TOOL_MIN_AAL` row.
- `is_irreversible = True` → `auth_level != "public"`.

## 2. Emit a `ToolCallAuditRecord` — identical shape for mock and live

```python
from datetime import datetime, timezone
from kosmos.security.audit import ToolCallAuditRecord

record = ToolCallAuditRecord(
    record_version="v1",
    tool_id="issue_certificate_resident_registration",
    adapter_mode="mock",             # or "live" — this is the ONLY shape-differing field
    session_id="01J...",             # UUIDv7 recommended
    caller_identity="agent:session-opaque",
    permission_decision="allow",
    auth_level_presented="AAL3",
    pipa_class="identifier",
    dpa_reference="DPA-MOIS-2026-01",
    input_hash="a" * 64,
    output_hash="b" * 64,
    sanitized_output_hash="c" * 64,
    merkle_covered_hash="sanitized_output_hash",  # binds to sanitized when present
    merkle_leaf_id=None,              # set by the Merkle chain epic (deferred)
    timestamp=datetime.now(timezone.utc),
    cost_tokens=0,
    rate_limit_bucket="gov.mois/key-01",
    public_path_marker=False,
)
```

**Invariants `ToolCallAuditRecord` enforces**:

- `sanitized_output_hash` non-null ↔ `merkle_covered_hash == "sanitized_output_hash"`.
- `public_path_marker = True` → `tool_id == "check_eligibility"` AND `auth_level_presented == "AAL1"` AND `pipa_class == "non_personal"`.
- `pipa_class != "non_personal"` → `dpa_reference is not None`.
- `timestamp.tzinfo is not None`.

## 3. `check_eligibility` public_path — the only AAL1 PII-free exception

```python
# Citizen asks: "with these inputs, am I eligible?" — no PII exchanged either direction.
record = ToolCallAuditRecord(
    record_version="v1",
    tool_id="check_eligibility",
    adapter_mode="mock",
    session_id="01J...",
    caller_identity="anon:session-opaque",
    permission_decision="allow",
    auth_level_presented="AAL1",
    pipa_class="non_personal",
    dpa_reference=None,
    input_hash="d" * 64,
    output_hash="e" * 64,
    sanitized_output_hash=None,
    merkle_covered_hash="output_hash",     # no sanitized variant ⇒ binds raw
    merkle_leaf_id=None,
    timestamp=datetime.now(timezone.utc),
    cost_tokens=0,
    rate_limit_bucket="gov.rules-only",
    public_path_marker=True,                # MUST be set for this fallback
)
```

Any other tool setting `public_path_marker = True` is rejected at validation time.

## 4. Consent record + delegation token (skeleton — server impl deferred)

Refer to `contracts/agent-delegation.openapi.yaml`:

- `POST /consent` — emits a `ConsentRecord` carrying `dpa_reference` (non-null for PII-bound scopes) and `synthesis_consent: bool`.
- `POST /token` — issues a `DelegationToken` (RFC 9068 JWT with `aal_asserted` claim; grant type is RFC 8628 device or RFC 8693 exchange; PKCE per RFC 7636 required).
- `POST /introspect` — RFC 7662 introspection; MUST be called before any `is_irreversible=True` invocation regardless of cache.
- `POST /revoke` — RFC 7009 revocation.

## 5. Run the new unit tests locally

```bash
uv run pytest tests/unit/test_gov_api_tool_extensions.py tests/unit/test_tool_call_audit_record.py -v
```

Expected CI steps (added in the implementation epic):

1. Invariant tests — load every in-tree adapter and confirm fail-closed behavior on field omission.
2. Schema-round-trip tests — validate three worked examples (authenticated allow, denied-AAL, check_eligibility public_path) against `contracts/tool-call-audit-record.schema.json`.
3. OpenAPI lint — `contracts/agent-delegation.openapi.yaml` validates under a standard OpenAPI 3.0 linter.
4. SBOM workflow — `.github/workflows/sbom.yml` emits SPDX 2.3 + CycloneDX 1.6 on push to `main` and every tag; build fails on divergence vs last-signed artifact.

## 6. PR checklist items — minimum 5 new unified items

When opening an adapter PR, verify each:

1. **AAL alignment**: adapter's `auth_level` matches its row in `TOOL_MIN_AAL`; `pipa_class` is one of `non_personal | personal | sensitive | identifier`; `is_irreversible` and `dpa_reference` populated per the rules in §1.
2. **Audit shape parity**: happy-path test emits a record that validates against `tool-call-audit-record.schema.json` AND an error-path (insufficient AAL) test emits a record with `permission_decision = "deny_aal"` that also validates.
3. **Output sanitization declaration**: if the adapter may return PII, it MUST produce a sanitized variant and set `sanitized_output_hash` + `merkle_covered_hash = "sanitized_output_hash"`. If it never returns PII (`pipa_class == "non_personal"`), `sanitized_output_hash` stays `None` and `merkle_covered_hash = "output_hash"`.
4. **Irreversible-action introspection**: if `is_irreversible = True`, the adapter's permission wiring invokes live introspection per RFC 7662 before handler body, regardless of cache; a test covers the expired-token rejection path.
5. **DPA + synthesis consent**: if `pipa_class != "non_personal"`, the adapter documents the `dpa_reference` it expects at call time, and any LLM-synthesis downstream of the adapter's output is gated by `synthesis_consent = True` in the originating consent record.

## 7. Where each control lives after the spec lands

| Concern | File | Status after spec 024 |
|---|---|---|
| Normative spec (ministry-facing) | `docs/security/tool-template-security-spec-v1.md` | Authored |
| `GovAPITool` field extensions | `src/kosmos/tools/models.py` | 4 new fields added, validators wired |
| `ToolCallAuditRecord` model | `src/kosmos/security/audit.py` | New module, schema-only (no storage) |
| JSON Schema artifact | `docs/security/tool-call-audit-record.schema.json` | Published, CI-validated |
| OpenAPI skeleton | `docs/security/agent-delegation.openapi.yaml` | Skeleton only; server impl deferred (D2) |
| SBOM workflow | `.github/workflows/sbom.yml` | Scaffolded; full signing deferred |
| Merkle chain | — | Deferred (D3) |
| Full 8-tool mock | — | Deferred (D1) |
| PIPC 유권해석 질의서 | — | Deferred (D4, parallel legal track) |
