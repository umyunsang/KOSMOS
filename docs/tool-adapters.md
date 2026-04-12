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

**Fail-closed defaults**: a new adapter only declares fields that deviate from the conservative defaults. Forgetting a field never accidentally exposes personal data as public.

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
