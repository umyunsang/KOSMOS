# Contract: Live Test Interfaces

**Feature**: [spec.md](../spec.md) · **Plan**: [plan.md](../plan.md)

Defines the public signatures and assertion contracts for the 12 new live tests. Implementation bodies are the responsibility of `/speckit-implement`; this contract pins what each test promises to verify.

---

## Module: `tests/live/test_live_geocoding.py` (Story 1)

All tests carry `@pytest.mark.live` and `@pytest.mark.asyncio`.

| Test | Fixtures consumed | Assertions |
|---|---|---|
| `test_live_kakao_search_address_happy` | `kakao_api_key`, `kakao_rate_limit_delay`, `live_http_client` | `len(documents) >= 1`; each of `{"address_name","x","y"}` present; `float(x) ∈ [124,132]`, `float(y) ∈ [33,39]` |
| `test_live_kakao_search_address_nonsense` | same | `documents == []`, no exception raised |
| `test_live_address_to_grid_seoul_landmark` | `kakao_api_key`, `kakao_rate_limit_delay` | `nx ∈ [57,63]`, `ny ∈ [124,130]` |
| `test_live_address_to_grid_busan_landmark` | `kakao_api_key`, `kakao_rate_limit_delay` | `nx ∈ [95,100]`, `ny ∈ [73,78]` |
| `test_live_address_to_region_gangnam` | `kakao_api_key`, `kakao_rate_limit_delay` | `sido == "SEOUL"` and `gugun == "SEOUL_GANGNAM"` |
| `test_live_address_to_region_busan` | `kakao_api_key`, `kakao_rate_limit_delay` | `sido == "BUSAN"` |
| `test_live_address_to_region_unmapped_region` | `kakao_api_key`, `kakao_rate_limit_delay` | tool returns structured unmapped `ToolResult` (no exception); payload shape matches adapter's fail-closed contract |

**Traceability**: FR-001, FR-006, FR-008, FR-009, FR-010, FR-011, FR-014 · SC-001

---

## Module: `tests/live/test_live_observability.py` (Story 2)

All tests carry `@pytest.mark.live` and `@pytest.mark.asyncio`.

| Test | Fixtures consumed | Pre-state → Act → Post-state | Assertions |
|---|---|---|---|
| `test_live_metrics_collector_under_live_tool_call` | `koroad_api_key` | snapshot collector → real KOROAD call through tool executor → snapshot collector | `tool.calls.total` delta == 1; `tool.latency_ms` has ≥1 new sample > 0 |
| `test_live_metrics_collector_under_live_llm_stream` | `friendli_token` | snapshot collector → real LLM streaming completion → snapshot collector | `llm.requests.total` delta ≥ 1; `llm.tokens.prompt` + `llm.tokens.completion` each have ≥1 new sample > 0 |
| `test_live_event_logger_emits_tool_events` | `koroad_api_key` | snapshot event log → real KOROAD call → snapshot event log | ≥1 `tool.call.started`, ≥1 `tool.call.completed`; each has non-empty `tool_id`, numeric non-negative `latency_ms`, populated `outcome` |
| `test_live_event_logger_emits_llm_events` | `friendli_token` | snapshot event log → real LLM stream → snapshot event log | ≥1 `llm.stream.started`, ≥1 `llm.stream.completed`; valid schema |

**Traceability**: FR-002, FR-006, FR-008, FR-009, FR-011, FR-013 · SC-002

---

## Module: `tests/live/test_live_e2e.py` (Story 3)

Single new test appended to the existing module.

### `test_live_scenario1_from_natural_address`

**Decorators**: `@pytest.mark.live`, `@pytest.mark.asyncio`.

**Fixtures consumed**: `kakao_api_key`, `koroad_api_key`, `friendli_token`, `kakao_rate_limit_delay`.

**Flow**:
1. Build a `QueryEngine` with the real LLM client, real tool registry (including geocoding + KOROAD adapters), and a real `ObservabilityEventLogger` wired in.
2. Drive `engine.run()` (or equivalent) with user message `"강남역 근처 사고 정보 알려줘"`.
3. Collect the recorded tool-call sequence and the final response text.
4. Inspect the observability event log.

**Assertions**:

| # | Assertion |
|---|---|
| 1 | Tool-call sequence contains at least one of `{"address_to_region","address_to_grid"}` and exactly one `"koroad_accident_search"` call. |
| 2 | First index of any geocoding call < first index of the KOROAD call. |
| 3 | `len(final_response.strip()) > 0`. |
| 4 | Final response contains at least one Hangul character (Unicode range `\uac00-\ud7af`). |
| 5 | Event log contains ≥1 `llm.stream.{started,completed}` pair, ≥1 geocoding `tool.call.{started,completed}` pair, ≥1 KOROAD `tool.call.{started,completed}` pair. |

**Traceability**: FR-003, FR-006, FR-008 · SC-003

---

## Non-assertions (intentional)

None of these tests assert on:

- Specific Kakao document IDs, building names, zone numbers, or road addresses.
- Specific KOROAD accident counts, event IDs, or location strings.
- Specific LLM-generated text content, word choice, or length.
- Specific counter values (only deltas), specific histogram bucket boundaries, or specific token counts (only positivity).

These non-assertions are a hard policy (FR-009, D6). Any PR that tightens an assertion toward specific values violates the contract.
