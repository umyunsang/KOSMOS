# Tool Adapter Guide

How to add a new `data.go.kr` API adapter to KOSMOS. Read `docs/vision.md` §Layer 2 first for the conceptual model.

## Spec cycle protocol for tool adapters

Tool adapter Epics follow the standard spec-driven workflow, with mandatory technical document analysis at each stage.

### `/speckit-specify` — Discovery

1. **Read all technical documents** under `research/data/<provider>/` for the target provider(s)
2. **Inventory every endpoint** found in each document — name, URL path, HTTP method, description
3. **Classify each endpoint**:
   - `include` — becomes a KOSMOS tool (directly serves a citizen scenario)
   - `exclude` — not useful for conversational AI (e.g., admin-only, batch export, WMS map tiles)
   - `defer` — useful but not needed in this Phase
4. **Justify** each classification in the spec (one sentence per endpoint)
5. **Identify shared parameters** — code tables (xlsx), enum values, region codes that multiple endpoints share

### `/speckit-plan` — Schema design

Phase 0 Research must:

1. **Read `docs/vision.md` § Reference materials** and map design decisions to MIT-licensed sources
2. **Read `.specify/memory/constitution.md`** for fail-closed defaults and compliance rules
3. **For each `include` endpoint**, produce:

   | Deliverable | Source |
   |---|---|
   | `tool_id` | Naming convention: `<provider>_<noun>_<verb>` |
   | `endpoint` | Exact URL from technical document |
   | `input_schema` | Request parameters table → Pydantic v2 model |
   | `output_schema` | Response fields table → Pydantic v2 model |
   | `search_hint` | Korean nouns + English glosses + ministry name |
   | Fail-closed flags | `requires_auth`, `is_personal_data`, `is_concurrency_safe`, `cache_ttl_seconds` |
   | `rate_limit_per_minute` | Conservative initial value per provider quota |
   | Code table enums | xlsx/doc code values → Python Enum or Literal types |

4. **Cross-reference code tables** — if the provider ships an xlsx codelist (e.g., `AccidentHazard_CodeList.xlsx`), the plan must specify how those codes become Pydantic Enum fields with validation
5. **Note year-dependent or region-dependent parameter quirks** (e.g., KOROAD 부천시 code changes by year, 강원도 code changed in 2023)

### `/speckit-tasks` — Task decomposition

Each task should be one of:
- **Adapter implementation** — one task per tool (or group 2-3 trivially similar tools)
- **Shared code table module** — enum definitions shared across multiple tools
- **Fixture recording** — `scripts/record_fixture.py` for each tool
- **Test suite** — happy-path + error-path per tool

Tasks that touch different providers are `parallel-safe`. Tasks within the same provider may share code tables and should be sequenced accordingly.

### `/speckit-analyze` — Constitution compliance

Verify:
- All I/O schemas use Pydantic v2, no `Any` types
- Fail-closed defaults applied (constitution § II)
- No hardcoded API keys
- `search_hint` is bilingual
- PII-handling endpoints flagged `is_personal_data=True`
- Live API calls excluded from CI tests

## Technical document registry

| Provider | Directory | Documents | Key/Secret |
|---|---|---|---|
| KOROAD (한국도로교통공단) | `research/data/koroad/` | API spec (.hwp), codelist (.xlsx) | `KOSMOS_KOROAD_API_KEY` |
| KMA (기상청) | `research/data/kma/` | API guides (.docx), zone codes (.xlsx), grid coords (.xlsx) | `KOSMOS_DATA_GO_KR_KEY` |
| NMC (국립중앙의료원) | `research/data/nmc/` | Emergency medical API guide V4 (.hwp) | `KOSMOS_DATA_GO_KR_KEY` |
| HIRA (건강보험심사평가원) | `research/data/hira/` | Hospital info guide (.docx), detail info guide (.docx) | `KOSMOS_DATA_GO_KR_KEY` |
| SSIS (한국사회보장정보원) | `research/data/ssis/` | Central welfare guide (.doc), local welfare codelist (.doc) | `KOSMOS_DATA_GO_KR_KEY` |
| Gov24 (행정안전부) | `research/data/gov24/` | Swagger-extracted API spec (.md) | `KOSMOS_DATA_GO_KR_KEY` |
| safetydata (재난안전) | — | Pending approval | `KOSMOS_SAFETYDATA_KEY` |

## Adapter shape

Each adapter is a tool module that registers a `GovAPITool` instance. The exact field names are defined by the foundation spec (`specs/001-foundation/`); the conceptual fields are:

| Field | Description | Default |
|---|---|---|
| `id` | Stable identifier, snake_case | required |
| `name_ko` | Korean display name | required |
| `provider` | Ministry or agency name | required |
| `category` | Topic tags (e.g., `["교통", "안전"]`) | required |
| `endpoint` | Base URL | required |
| `auth_type` | `public` \| `api_key` \| `oauth` | required |
| `input_schema` | Pydantic v2 model | required |
| `output_schema` | Pydantic v2 model | required |
| `requires_auth` | Citizen auth gate | `True` |
| `is_concurrency_safe` | Safe to call in parallel | `False` |
| `is_personal_data` | Touches PII | `True` |
| `cache_ttl_seconds` | Response cache lifetime | `0` |
| `rate_limit_per_minute` | Client-side limit | `10` |
| `search_hint` | Korean + English discovery keywords | required |
| `auth_level` | Minimum NIST SP 800-63-4 AAL required (`public` \| `AAL1` \| `AAL2` \| `AAL3`). MUST equal the tool's row in `TOOL_MIN_AAL` (validator V3). | required |
| `pipa_class` | PIPA data classification (`non_personal` \| `personal` \| `sensitive` \| `identifier`). | required |
| `is_irreversible` | `True` when invocation cannot be undone (e.g., payment, certificate issuance). Drives FR-007 live-introspection. | required |
| `dpa_reference` | DPA template identifier governing the §26 processor chain. MUST be non-null when `pipa_class != "non_personal"` (validator V2). | required |

**Fail-closed defaults**: fields with defaults (`requires_auth`, `is_personal_data`, etc.) default conservative — forgetting them never accidentally exposes personal data as public. Fields without defaults (`auth_level`, `pipa_class`, `is_irreversible`, `dpa_reference`) MUST always be declared explicitly; Pydantic rejects adapters that omit them.

## PR checklist

Every new adapter PR must include:

- [ ] Pydantic v2 input and output models
- [ ] All non-default fields declared explicitly
- [ ] `search_hint` with both Korean and English keywords
- [ ] One happy-path unit test with a recorded fixture
- [ ] One error-path unit test (4xx or 5xx from the API)
- [ ] Fixture recorded under `tests/fixtures/<provider>/<tool_id>.json`
- [ ] No hardcoded credentials — read from `KOSMOS_*` environment variables
- [ ] No `Any` types in the schemas
- [ ] Entry in `docs/tools/<provider>.md` with endpoint, rate limit, known quirks

## Recording fixtures

1. Export a scratch API key to your shell: `export KOSMOS_DATA_GO_KR_KEY=...`
2. Call the live endpoint once with `scripts/record_fixture.py <tool_id>` (script provided by the foundation spec)
3. Review the recorded JSON — redact any personal identifiers, IP addresses, or session tokens
4. Commit under `tests/fixtures/<provider>/`

Never commit a fixture that contains real citizen data. Use synthetic values (`홍길동`, `010-0000-0000`, etc.) if the API echoes inputs.

## Naming

- Tool `id`: `<provider>_<noun>_<verb>` → `koroad_accident_search`, `kma_weather_forecast`
- Module path: `src/kosmos/tools/<provider>/<tool_id>.py`
- Test path: `tests/tools/<provider>/test_<tool_id>.py`

## Search hints

The `search_hint` field drives the lazy tool discovery meta-tool. Write hints as a free-form phrase that a citizen or an LLM would plausibly use:

```python
search_hint = "교통사고 traffic accident 사망자 injury statistics KOROAD 도로교통공단"
```

Include: Korean noun, English gloss, ministry name in both languages, synonyms a citizen might use in conversation.

## Live-call discipline

- Tests marked `@pytest.mark.live` may call real APIs during local development
- `@pytest.mark.live` tests are skipped by default and never run in CI
- The default pytest run uses only recorded fixtures
- Record once, commit, replay forever

## Rate limiting and quotas

- Declare `rate_limit_per_minute` conservatively — start below the ministry's stated limit and raise only with evidence
- The query engine's budget tracker uses this field; lying about it will cause cascading 429s in production
- If a ministry publishes per-day quotas, note them in `docs/tools/<provider>.md` so the engine can warn before exhaustion

## Personal data flag

`is_personal_data=True` triggers the permission pipeline's stricter gate (Layer 3). Set to `False` only if the endpoint returns aggregate statistics with no individual records. When in doubt, leave it `True` — the default is fail-closed for a reason.

## FR-038 invariant: `is_personal_data=True` requires `requires_auth=True`

**Rule**: Any tool registered with `is_personal_data=True` must also set `requires_auth=True`. Registering a PII-flagged tool without auth enabled is a hard error enforced in `ToolRegistry.register()` at startup:

```python
# src/kosmos/tools/registry.py — enforced at registration time
if tool.is_personal_data and not tool.requires_auth:
    raise RegistrationError(
        "is_personal_data=True requires requires_auth=True (Constitution §II / FR-038)"
    )
```

This invariant is Constitution §II (fail-closed principle): personal data must never be accessible to unauthenticated sessions. The registry acts as the last line of defence against mis-configured adapters reaching production.

**PR checklist additions for PII-flagged adapters**:

- [ ] `is_personal_data=True` is paired with `requires_auth=True` — never declare one without the other
- [ ] The `llm_description` field warns the LLM that unauthenticated calls will be rejected (`auth_required`)

## Layer 3 auth-gate contract for `requires_auth=True` adapters

When `requires_auth=True`, `ToolExecutor.invoke()` short-circuits unconditionally before the adapter handler body is reached (FR-025, FR-026, SC-006):

```
session_identity is None  →  LookupError(reason="auth_required")
                              ↑ returned immediately; handle() never called
```

This means:

1. The handler body of an auth-gated adapter is **unreachable** for unauthenticated sessions — no HTTP call to the upstream API is ever made.
2. The adapter **implementation can be a stub** (interface-only): a full `GovAPITool` registration with valid Pydantic I/O schemas, but a `handle()` body that raises `Layer3GateViolation` as a defence-in-depth guard.
3. The stub is sufficient to satisfy the executor's adapter contract, pass the test suite, and expose the tool to the LLM for discovery — execution is gated at the platform level, not the adapter level.

### Interface-only adapter pattern (NMC reference implementation)

`src/kosmos/tools/nmc/emergency_search.py` is the canonical example. The handler raises `Layer3GateViolation` unconditionally:

```python
async def handle(inp: NmcEmergencySearchInput) -> dict[str, Any]:
    """Should never reach here — Layer 3 gate short-circuits on requires_auth=True."""
    raise Layer3GateViolation("nmc_emergency_search")
```

Use this pattern when:
- The upstream API requires citizen auth credentials not yet provisioned (e.g., NMC live auth pending)
- The output schema is not yet finalized but the tool must be discoverable and registered
- You want to assert a future implementation contract without risking an accidental unauthenticated upstream call

**When using the interface-only pattern**, the PR checklist items for "recorded fixture" and "happy-path unit test" are replaced by:

- [ ] `handle()` raises `Layer3GateViolation` unconditionally
- [ ] A unit test asserts `Layer3GateViolation` is raised when `handle()` is called directly (defence-in-depth)
- [ ] A unit test asserts the executor returns `LookupError(reason="auth_required")` when called with `session_identity=None` (gate contract)
- [ ] A `# TODO` comment in `handle()` references the Epic that will implement the real upstream call
- [ ] The placeholder `output_schema` documents why it is a stub (`RootModel[dict]` is acceptable until real schema is known)

## Security PR checklist (spec v1)

This checklist is normative for every adapter PR opened against the KOSMOS repository. It unifies the six research lanes surveyed in specs/024-tool-security-v1: Korean legal compliance (PIPA, 전자정부법, 전자서명법), international identity standards (NIST SP 800-63-4, OWASP ASVS), LLM-tool security (OWASP Top 10 for LLMs), identity and delegation (OAuth 2.1, RFC 7662, RFC 9068), public-sector security precedents (K-ISMS-P, eGovFramework, Singapore IMDA MGF), and supply-chain provenance (SLSA v1.0, NIST SP 800-218). Applying this checklist once gives a reviewer confidence across all six domains without requiring lane-specific expertise. It supersedes any ad-hoc lane-specific notes that may appear in earlier sections of this document.

- [ ] **AAL alignment**: The adapter's `auth_level` field exactly matches the tool's row in `TOOL_MIN_AAL` (validator V3 enforces this at load time). `pipa_class` is one of `non_personal | personal | sensitive | identifier` per PIPA §24 / PIPA §23 / PIPA §2.1. `is_irreversible` and `dpa_reference` are populated per the rules in quickstart.md §1. Cross-link: [FR-001, FR-005](./security/tool-template-security-spec-v1.md#govapitool-field-contract).
- [ ] **Audit shape parity**: The happy-path test emits a `ToolCallAuditRecord` that validates against `docs/security/tool-call-audit-record.schema.json`. The error-path (insufficient AAL) test emits a record with `permission_decision="deny_aal"` that also validates. Mock and live adapter modes MUST produce records that differ only in the `adapter_mode` field — all other fields must carry identical shapes. Cross-link: [FR-012](./security/tool-template-security-spec-v1.md#audit-trail).
- [ ] **Output sanitization declaration**: If the adapter may return PII (`pipa_class != "non_personal"`), it MUST produce a sanitized output variant and set `sanitized_output_hash` + `merkle_covered_hash="sanitized_output_hash"` in the emitted audit record (invariant I1). If the adapter never returns PII, `sanitized_output_hash` stays `None` and `merkle_covered_hash="output_hash"`. This declaration MUST appear as a comment in the adapter registration block. Cross-link: [FR-009, FR-010](./security/tool-template-security-spec-v1.md#audit-trail).
- [ ] **Irreversible-action introspection**: If `is_irreversible=True`, the adapter's permission wiring MUST invoke live token introspection per RFC 7662 before the handler body executes, regardless of any token cache. A test MUST cover the expired-token rejection path. This applies to every invocation — no caching exception. Cross-link: [FR-007](./security/tool-template-security-spec-v1.md#permission-pipeline), OWASP ASVS V4.1.5.
- [ ] **DPA + synthesis consent**: If `pipa_class != "non_personal"`, the adapter registration block MUST document the `dpa_reference` identifier it expects at call time (validator V2 enforces non-null). Any downstream LLM synthesis that consumes the adapter's output MUST be gated by `synthesis_consent=True` in the originating consent record (FR-015). Cross-link: [FR-014, FR-015](./security/tool-template-security-spec-v1.md#pipa-role), PIPA §26 수탁자 + LLM-synthesis controller-level carve-out.
