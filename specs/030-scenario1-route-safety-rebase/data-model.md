# Data Model: Scenario 1 E2E — Route Safety (Re-baseline)

**Date**: 2026-04-18
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

This document defines the **test-layer Pydantic v2 models** introduced by this spec. It also enumerates the **existing production models** the scenario asserts against (no production schemas change under this spec). All models live in `tests/e2e/conftest.py` unless otherwise noted.

Constitution §III compliance: every model is Pydantic v2; no `Any`; all fields are explicitly typed; discriminated unions use `Literal` tags.

---

## 1. Existing production entities the scenario asserts against

The scenario does not redefine these — it asserts them. Listed here for traceability.

| Entity | Module | Why it matters in this spec |
|---|---|---|
| `ResolveBundle` | `kosmos.tools.models` | Output of both `resolve_location` calls (Turns 1a/1b). |
| `ResolveError` | `kosmos.tools.models` | Output of `resolve_location` when `reason ∈ {not_found, ambiguous}` (edge cases). |
| `LookupSearchInput` / `LookupSearchResult` | `kosmos.tools.models` | Turns 2 and 4 (BM25 retrieval gate). |
| `LookupFetchInput` | `kosmos.tools.models` | Turns 3 and 5 (`mode="fetch"`, `tool_id`, `args`). |
| `LookupCollection` | `kosmos.tools.models` | KOROAD adapter output envelope (FR-005). |
| `LookupTimeseries` | `kosmos.tools.models` | KMA adapter output envelope (FR-006). |
| `LookupError` | `kosmos.tools.models` | Error variant of the envelope (FR-008, FR-021/022). |
| `LookupMeta` | `kosmos.tools.models` | `source`, `fetched_at`, `request_id`, `elapsed_ms` (FR-007). |
| `ToolResult` | `kosmos.tools.models` | Internal executor return. Carries `success`, `error_type`. |
| `GovAPITool` | `kosmos.tools.models` | Adapter metadata. Must satisfy V1–V6 invariants (FR-009/010). |
| `SidoCode` / `SearchYearCd` | `kosmos.tools.koroad.code_tables` | Drives the 2023 year-quirk mapping (FR-013/014). |
| `QueryState` | `kosmos.engine.models` | Carries `stop_reason` (FR-022). |
| `StreamEvent` / `TokenUsage` | `kosmos.llm.models` | MockLLMClient scripting units; FR-015 assertion surface. |
| `UsageTracker` | `kosmos.llm.usage` | Token totals (FR-015). |

---

## 2. New test-layer entities

### 2.1 `ScenarioTurn`

A single scripted entry from the mock LLM's perspective. One `ScenarioTurn` corresponds to one `StreamEvent` stream segment.

**Purpose**: Makes the 6-turn sequence in spec §Overview a typed, reviewable Python object instead of a free-form list of magic strings.

**Fields**:

| Field | Type | Required | Validation |
|---|---|---|---|
| `index` | `int` | yes | `ge=0, le=5` for the canonical happy path; unbounded for degraded/edge scenarios. |
| `kind` | `Literal["tool_call", "text_delta"]` | yes | — |
| `tool_name` | `Literal["resolve_location", "lookup"] \| None` | conditional | Required when `kind == "tool_call"`; must be `None` when `kind == "text_delta"`. |
| `tool_arguments` | `dict[str, str \| int \| float \| bool \| None] \| None` | conditional | Required when `kind == "tool_call"`. Flat primitives only — no nested mocks. |
| `text_content` | `str \| None` | conditional | Required when `kind == "text_delta"`. Final Korean synthesis string. |
| `token_usage` | `TokenUsage \| None` | optional | When present, summed into the expected `UsageTracker` total (FR-015). |

**Invariants** (Pydantic v2 `@model_validator(mode="after")`):
- I1: `kind == "tool_call"` ⇒ `tool_name` and `tool_arguments` are non-None; `text_content` is None.
- I2: `kind == "text_delta"` ⇒ `text_content` is non-None; `tool_name` and `tool_arguments` are None.
- I3: `tool_arguments`, when present, serialises to ≤ 1 KiB — keeps scripted fixtures reviewable.

### 2.2 `ScenarioScript`

A typed ordered collection of `ScenarioTurn`s plus metadata identifying the scenario variant.

**Purpose**: What the `MockLLMClient` consumes; what tests assert the turn loop replayed.

**Fields**:

| Field | Type | Required | Validation |
|---|---|---|---|
| `scenario_id` | `Literal["happy", "degraded_kma_retry", "degraded_koroad_no_retry", "both_down", "quirk_2023_gangwon", "quirk_2023_jeonbuk", "quirk_2022_control"]` | yes | Fixed set; adding a variant requires a spec amendment. |
| `turns` | `tuple[ScenarioTurn, ...]` | yes | Length ≥ 2 (at least one tool call + one synthesis). Happy path has length 6. |
| `expected_stop_reason` | `Literal["end_turn", "error_unrecoverable", "api_budget_exceeded"]` | yes | Matched against `QueryState.stop_reason` after `QueryEngine.run()`. |

### 2.3 `ObservabilitySnapshot`

A typed, test-safe view of the OTel spans captured in-memory during a scenario run.

**Purpose**: Surface for FR-017/018/019 assertions. Filtering and PII-masking checks run against this object, not against the raw OTel SDK types.

**Fields**:

| Field | Type | Required | Validation |
|---|---|---|---|
| `spans` | `tuple[CapturedSpan, ...]` | yes | Ordered by span start time; immutable. |
| `sdk_disabled` | `bool` | yes | Mirrors `os.getenv("OTEL_SDK_DISABLED") == "true"`. When `True`, `spans` MUST be empty. |

### 2.4 `CapturedSpan`

Per-span snapshot. Narrow by design — only the fields this spec asserts on are surfaced.

**Fields**:

| Field | Type | Required | Validation |
|---|---|---|---|
| `name` | `str` | yes | Must start with `"execute_tool "` for any tool span. |
| `operation_name` | `Literal["execute_tool"] \| None` | yes | Value of `gen_ai.operation.name` attribute, or None. |
| `tool_name` | `str` | yes | Value of `gen_ai.tool.name`. |
| `tool_call_id` | `str \| None` | yes | Value of `gen_ai.tool.call.id`. |
| `outcome` | `Literal["ok", "error"]` | yes | Value of `kosmos.tool.outcome` (FR-017). Absence ⇒ assertion failure. |
| `adapter_id` | `str \| None` | yes | Value of `kosmos.tool.adapter` (FR-018). Present iff span corresponds to `lookup(mode="fetch")`. |
| `error_type` | `str \| None` | conditional | Required when `outcome == "error"`. Maps from `error.type` attribute. |
| `status_code` | `Literal["UNSET", "OK", "ERROR"]` | yes | Span `Status`. |
| `attribute_keys` | `frozenset[str]` | yes | Full set of attribute names. Used by FR-019 to assert no Korean citizen string appears. |

**Invariants**:
- I4: `outcome == "error"` ⇒ `status_code == "ERROR"` and `error_type` is non-None.
- I5: `adapter_id is not None` ⇒ `tool_name == "lookup"` (FR-018 gate; `resolve_location` / `search` spans never carry `kosmos.tool.adapter`).
- I6: No attribute value may equal the citizen trigger query string `"내일 강남구에서 서울역 가는데 날씨랑 사고다발지역 알려줘"` nor the `query=` argument of any `resolve_location` call (FR-019). Enforced by the span assertion helper, not by the model itself.

### 2.5 `RunReport`

The top-level artifact every scenario test produces. Serves as both assertion surface and optional JSON export.

**Purpose**: One Pydantic v2 aggregate that fully describes what happened — what the mock LLM scripted, what the engine executed, what the observability stack captured. Consumed by assertion helpers and (optionally) written to disk under `KOSMOS_E2E_DUMP_DIR`.

**Fields**:

| Field | Type | Required | Validation |
|---|---|---|---|
| `scenario_id` | `Literal[...]` | yes | Mirrors `ScenarioScript.scenario_id`. |
| `trigger_query` | `str` | yes | The citizen-facing Korean query. |
| `tool_call_order` | `tuple[str, ...]` | yes | Ordered names of tool calls actually dispatched (e.g., `("resolve_location", "resolve_location", "lookup", "lookup", "lookup", "lookup")`). |
| `fetched_adapter_ids` | `tuple[str, ...]` | yes | In order — e.g., `("koroad_accident_hazard_search", "kma_forecast_fetch")`. FR-001 / FR-002. |
| `final_response` | `str \| None` | conditional | Korean synthesis string; `None` when `stop_reason != "end_turn"`. FR-023. |
| `stop_reason` | `Literal["end_turn", "error_unrecoverable", "api_budget_exceeded"]` | yes | Matched against `ScenarioScript.expected_stop_reason`. |
| `usage_totals` | `TokenUsage` | yes | `UsageTracker.total_input_tokens` / `total_output_tokens` at run end (FR-015). |
| `observability` | `ObservabilitySnapshot` | yes | All tool spans for the run. |
| `adapter_rate_limit_hits` | `dict[str, int]` | yes | `{adapter_id: call_count}`; exactly one per adapter in happy path (FR-016). |
| `schema_version` | `Literal["030-runreport-v1"]` | yes | Frozen; future spec revisions bump this. Used by `contracts/eval-output.schema.json`. |
| `elapsed_ms` | `int` | yes | `ge=0`; wall-clock ms for the full run. Advisory — not asserted. |

**Invariants**:
- I7: `len(fetched_adapter_ids)` equals the count of `CapturedSpan`s whose `adapter_id is not None` (FR-017/018 cross-check).
- I8: `stop_reason == "end_turn"` ⇒ `final_response` is non-empty.
- I9: `stop_reason == "error_unrecoverable"` ⇒ `final_response is None` OR `final_response` is a graceful Korean error message (FR-022) — which the assertion helper, not the model, distinguishes.

---

## 3. State transitions

Scenario test runs are short and linear. No long-lived state machine. The happy-path transition graph:

```
 [START]
    │
    ▼
 [resolve 강남구]  ──ok──▶  [resolve 서울역]  ──ok──▶  [lookup search #1]
                                                          │
                                                          ▼
                                                    [lookup fetch koroad]
                                                          │
                                      ok ──────────────── ▼ ──── error (retryable)
                                      │                         │
                                      ▼                         ▼
                               [lookup search #2]       [lookup fetch koroad] (one retry)
                                      │                         │
                                      ▼                         │
                               [lookup fetch kma]  ◀────────────┘
                                      │
                                      ▼
                               [synthesize (Korean)] ──▶ [END stop_reason=end_turn]
```

Degraded paths replace one `ok` transition with a retryable error; both-down paths terminate at `stop_reason=error_unrecoverable`. Quirk paths take the same graph but with different adapter-input values (`siDo=51` vs `siDo=42`).

---

## 4. Validation rule sources

Every validation rule above traces to one of:
- Spec 030 FR-xxx (this feature).
- Spec 022 (`LookupCollection` / `LookupTimeseries` frozen envelopes).
- Spec 021 (OTel span schema, PII masking).
- Spec 025 (V1–V6 security invariants).
- Constitution §III (Pydantic v2 strict typing; no `Any`).

No rule is invented by this data model in isolation.
