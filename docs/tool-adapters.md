# Tool Adapter Guide

How to add a new `data.go.kr` API adapter to KOSMOS. Read `docs/vision.md` §Layer 2 first for the conceptual model.

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
