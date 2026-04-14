# Phase 1 Data Model: Phase 1 Live Validation Coverage Extension

**Feature**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Date**: 2026-04-14

> This epic introduces **no new production entities**. All "entities" below are in-test data structures used by the live test suite to capture state, verify structural conformance, or represent fixtures.

## Test-Only Entities

### 1. `kakao_api_key` (pytest fixture)

**Scope**: `session`
**Returns**: `str` — the Kakao REST API key.
**Source**: `os.environ["KOSMOS_KAKAO_API_KEY"]`.
**Failure mode**: `pytest.fail("set KOSMOS_KAKAO_API_KEY to run live geocoding tests")` — exact string, no parameterization.

**Consumers**: all tests in `test_live_geocoding.py`; `test_live_scenario1_from_natural_address` in `test_live_e2e.py`.

### 2. `kakao_rate_limit_delay` (pytest fixture / async helper)

**Scope**: `function` (not autouse).
**Behavior**: exposes an awaitable `sleep(200 ms)` that callers invoke between successive Kakao API calls.
**Default delay**: 200 ms (private module constant; adjustable without API change).

**Consumers**: tests in `test_live_geocoding.py` that chain multiple Kakao calls in a single test function.

### 3. `ObservabilitySnapshot` (in-test dataclass or tuple)

Captures the state of a `MetricsCollector` and `ObservabilityEventLogger` at a point in time for delta comparison.

**Fields**:

| Field | Type | Purpose |
|-------|------|---------|
| `counters` | `dict[str, int]` (shallow copy) | Snapshot of counter values keyed by metric name. |
| `histograms` | `dict[str, list[float]]` (shallow copy) | Snapshot of histogram sample lists keyed by metric name. |
| `events` | `list[Event]` (shallow copy) | Snapshot of the event logger's emitted events. |

**Lifecycle**: created twice per test (pre-call, post-call); diffed to produce deltas.

**Consumers**: all tests in `test_live_observability.py`.

### 4. `RecordedToolCallSequence` (in-test list)

An ordered list of `(tool_id, outcome)` tuples captured during an E2E test. Populated by hooking into the tool executor's call callback (or by inspecting the observability event log post-run).

**Shape**: `list[tuple[str, str]]` — e.g., `[("address_to_region", "ok"), ("koroad_accident_search", "ok")]`.

**Consumers**: `test_live_scenario1_from_natural_address` — asserts `address_to_region`/`address_to_grid` appears strictly before `koroad_accident_search`.

---

## Relationships

```text
 kakao_api_key (session)
     │
     ▼
 geocoding tests ──► kakao_rate_limit_delay (function) ──► Kakao Local API
     │
     └─► search_address / address_to_grid / address_to_region (existing src)

 observability tests ──► MetricsCollector + ObservabilityEventLogger (real)
     │                     │
     │                     ▼
     │                     ObservabilitySnapshot (pre)
     ▼
 real tool call or LLM stream
     │
     ▼
 ObservabilitySnapshot (post) ──► delta assertions

 E2E natural-address test ──► QueryEngine.run() ──► ObservabilityEventLogger
     │                                                  │
     ▼                                                  ▼
 RecordedToolCallSequence ◄───────────────────────────  events
     │
     ▼
 ordering assertion: geocoding < KOROAD
```

---

## Validation Rules (assertion catalog)

### Geocoding (Story 1)

| Entity/Field | Rule |
|---|---|
| Kakao `documents` (happy path) | `len(documents) >= 1` |
| Kakao document | contains `address_name`, `x`, `y` |
| Kakao `x` | `float(x) ∈ [124.0, 132.0]` |
| Kakao `y` | `float(y) ∈ [33.0, 39.0]` |
| Kakao `documents` (nonsense) | `len(documents) == 0` and no exception |
| Seoul landmark grid | `nx ∈ [57, 63]` and `ny ∈ [124, 130]` (60/127 ±3) |
| Busan landmark grid | `nx ∈ [95, 100]` and `ny ∈ [73, 78]` |
| Gangnam region | `sido == "SEOUL"` and `gugun == "SEOUL_GANGNAM"` |
| Busan region | `sido == "BUSAN"` |
| Unmapped region (울릉도) | tool returns a structured `ToolResult` whose output indicates unmapped status; **no exception**; payload shape matches the adapter's documented contract |

### Observability (Story 2)

| Metric / Event | Rule |
|---|---|
| `tool.calls.total` | post - pre == 1 |
| `tool.latency_ms` | post has ≥1 more sample than pre, and the new sample > 0 |
| `llm.requests.total` | post - pre ≥ 1 |
| `llm.tokens.prompt` | post has ≥1 more sample than pre, new sample > 0 |
| `llm.tokens.completion` | post has ≥1 more sample than pre, new sample > 0 |
| `tool.call.started` events | ≥1 captured; each has non-empty `tool_id`, `latency_ms` is a non-negative number, `outcome` populated |
| `tool.call.completed` events | ≥1 captured; same schema rules as above |
| `llm.stream.started` events | ≥1 captured; valid schema |
| `llm.stream.completed` events | ≥1 captured; valid schema |

### E2E Natural-Address (Story 3)

| Assertion | Rule |
|---|---|
| Tool-call ordering | first index of any `address_to_*` call < first index of `koroad_accident_search` |
| Final response non-empty | `len(response.strip()) > 0` |
| Final response contains Hangul | any char in `\u00uac00-\ud7af` present in response |
| Event chain completeness | ≥1 LLM stream pair + ≥1 geocoding tool pair + ≥1 KOROAD tool pair |

---

## Schema Stability

No production Pydantic schemas are added or modified. Tests reference the following existing schemas (assertions are structural; schema evolution in a later epic does not break these tests unless the asserted fields are removed):

- `KakaoSearchResult`, `KakaoAddressDocument`, `KakaoAddressResult` — `src/kosmos/tools/geocoding/kakao_client.py`
- `AddressToGridInput`/`Output` — `src/kosmos/tools/geocoding/address_to_grid.py`
- `AddressToRegionInput`/`Output` — `src/kosmos/tools/geocoding/address_to_region.py`
- `MetricsCollector`, `ObservabilityEventLogger`, `Event` types — `src/kosmos/observability/`
- `ToolResult` — existing tool framework.
