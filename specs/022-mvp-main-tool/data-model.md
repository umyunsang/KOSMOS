# Phase 1 Data Model — MVP Main-Tool

**Feature**: 022-mvp-main-tool | **Date**: 2026-04-16
All models are Pydantic v2. `Any` is forbidden (Constitution §III). Discriminator names are frozen per `docs/design/mvp-tools.md` §4 and §5.4 and MUST NOT be renamed.

## 1. `resolve_location` — Input

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

WantField = Literal["coords", "adm_cd", "coords_and_admcd",
                    "road_address", "jibun_address", "poi", "all"]

class ResolveLocationInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(min_length=1, max_length=200)
    want: WantField = "coords_and_admcd"
    near: tuple[float, float] | None = None  # (lat, lon) ambiguity tiebreaker
```

**Validation rules**:
- `query` stripped of leading/trailing whitespace at validator layer; empty after strip → `ResolveError(reason="empty_query")`
- `near` when present: `-90 ≤ lat ≤ 90`, `-180 ≤ lon ≤ 180`

## 2. `resolve_location` — Output (discriminated union)

All variants share a `kind` discriminator and a `source: Literal["kakao","juso","sgis","bundle"]` provenance field.

```python
class CoordResult(BaseModel):
    kind: Literal["coords"] = "coords"
    lat: float
    lon: float
    confidence: Literal["high","medium","low"]
    source: Literal["kakao","juso","sgis"]

class AdmCodeResult(BaseModel):
    kind: Literal["adm_cd"] = "adm_cd"
    code: str                                # 10-digit 법정동 code
    name: str                                # "서울특별시 강남구"
    level: Literal["sido","sigungu","eupmyeondong"]
    source: Literal["sgis","juso"]

class AddressResult(BaseModel):
    kind: Literal["address"] = "address"
    road_address: str | None
    jibun_address: str | None
    postal_code: str | None
    source: Literal["kakao","juso"]

class POIResult(BaseModel):
    kind: Literal["poi"] = "poi"
    name: str
    category: str
    lat: float
    lon: float
    source: Literal["kakao"]

class ResolveBundle(BaseModel):
    kind: Literal["bundle"] = "bundle"
    coords: CoordResult | None = None
    adm_cd: AdmCodeResult | None = None
    address: AddressResult | None = None
    poi: POIResult | None = None
    source: Literal["bundle"] = "bundle"     # aggregated; child results carry true provenance

class ResolveError(BaseModel):
    kind: Literal["error"] = "error"
    reason: Literal["not_found","ambiguous","upstream_unavailable",
                    "invalid_query","empty_query","out_of_domain"]
    message: str
    candidates: list[CoordResult | AdmCodeResult | AddressResult | POIResult] = []

ResolveLocationOutput = (CoordResult | AdmCodeResult | AddressResult |
                         POIResult | ResolveBundle | ResolveError)
```

## 3. `lookup` — Input (discriminated on `mode`)

```python
class LookupSearchInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    mode: Literal["search"] = "search"
    query: str = Field(min_length=1, max_length=200)
    domain: str | None = None                # optional facet filter on GovAPITool.category
    top_k: int | None = None                 # per-call override; server clamps [1, 20]

class LookupFetchInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    mode: Literal["fetch"] = "fetch"
    tool_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    params: dict[str, object]                # validated against target adapter's input_schema
    page: int | None = Field(default=None, ge=1)

LookupInput = LookupSearchInput | LookupFetchInput       # Pydantic discriminated union on `mode`
```

**`params` note**: `dict[str, object]` is the single intentionally loose field (Constitution §III carve-out documented in frozen §5.2). It is validated at fetch time against `GovAPITool.input_schema` before the handler runs; validation failure → `LookupError(reason="invalid_params")`.

## 4. `lookup` — Output (discriminated union)

All four `mode="fetch"` shapes carry a `meta` block; `mode="search"` returns `LookupSearchResult`.

```python
class LookupMeta(BaseModel):
    model_config = ConfigDict(frozen=True)
    source: str                              # adapter's upstream provider label
    fetched_at: str                          # UTC ISO-8601
    request_id: str                          # UUID v4
    elapsed_ms: int                          # wall-clock for the fetch
    rate_limit_remaining: int | None = None  # provider-reported, if any

class AdapterCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)
    tool_id: str
    score: float                             # BM25 score, ≥ 0
    required_params: list[str]
    search_hint: str                         # echo of registry value
    why_matched: str                         # short rationale (token overlap)

class LookupSearchResult(BaseModel):
    kind: Literal["search"] = "search"
    candidates: list[AdapterCandidate]
    total_registry_size: int
    effective_top_k: int
    reason: Literal["ok","empty_registry","below_threshold"] = "ok"

class LookupRecord(BaseModel):
    kind: Literal["record"] = "record"
    item: dict[str, object]                  # single typed row (shape defined by adapter.output_schema)
    meta: LookupMeta

class LookupCollection(BaseModel):
    kind: Literal["collection"] = "collection"
    items: list[dict[str, object]]
    total_count: int | None = None
    next_cursor: str | None = None
    meta: LookupMeta

class LookupTimeseries(BaseModel):
    kind: Literal["timeseries"] = "timeseries"
    points: list[dict[str, object]]          # each has 'ts' + N value fields per adapter schema
    interval: Literal["minute","hour","day"]
    meta: LookupMeta

class LookupError(BaseModel):
    kind: Literal["error"] = "error"
    reason: Literal["auth_required","stale_data","timeout","upstream_unavailable",
                    "unknown_tool","invalid_params","out_of_domain","empty_registry"]
    message: str
    upstream_code: str | None = None
    upstream_message: str | None = None
    retryable: bool = False
    meta: LookupMeta | None = None           # present when the error was raised post-handler-entry

LookupOutput = (LookupSearchResult | LookupRecord | LookupCollection |
                LookupTimeseries | LookupError)
```

## 5. `GovAPITool` (registry record — extends existing model)

The existing `src/kosmos/tools/models.py:GovAPITool` already matches Constitution §II defaults. No breaking change; additions:

- `category: list[str]` is already present — the domain facet filter in `LookupSearchInput.domain` filters on this
- `rate_limit_per_minute: int` already present
- `handler: Callable[..., Awaitable[LookupOutput]]` — coroutine contract is new and will be enforced at registration (FR-037)

**Registration invariant (FR-038)**: `is_personal_data=True` ⇒ `requires_auth=True`. Violation raises `RegistrationError` at `ToolRegistry.register(tool)` startup, not at runtime.

## 6. `EvalRetrievalSet` (30-query file schema)

```python
class EvalQuery(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(pattern=r"^Q\d{3}$")
    query: str = Field(min_length=1)
    expected_tool_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    notes: str | None = None

class EvalRetrievalSet(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: int = 1
    queries: list[EvalQuery] = Field(min_length=30, max_length=30)
```

The YAML at `eval/retrieval_queries.yaml` is loaded and validated into `EvalRetrievalSet` at CI time. Gate evaluation is pure-function over `EvalRetrievalSet` × `ToolRegistry`.

## 7. `Layer3AuthGate` (envelope-layer short-circuit)

Not a data model per se — a function signature contract implemented in `src/kosmos/tools/envelope.py`:

```python
async def maybe_auth_short_circuit(
    tool: GovAPITool,
    session: Session | None,
) -> LookupError | None:
    """Return LookupError(reason='auth_required') iff the gate fires.
    Return None iff the handler may proceed.
    In MVP, `session is None` is always True → any tool with
    requires_auth=True short-circuits. Unconditional per FR-026."""
```

**MVP invariant**: no code path may pass `session != None` to this function; the session model is tracked under deferred item #16. The gate is keyed solely off `tool.requires_auth` + `tool.is_personal_data`.

## 8. State Transitions

- `ToolRegistry` lifecycle: `empty → registered → indexed` (BM25 rebuild on each register); registration is idempotent-by-id; duplicate id → `DuplicateToolError`.
- `lookup(mode="fetch")` lifecycle: `input_received → input_validated → auth_gated → rate_limited → handler_invoked → envelope_normalized → returned_to_llm`. Any stage failure short-circuits to the appropriate `LookupError` reason.
- `resolve_location` lifecycle: dispatch chain `kakao_try → juso_try → sgis_try → bundle_or_error` (deterministic order). First backend producing all requested `want` fields wins; backends with partial matches contribute to the `ResolveBundle`.

## 9. Relationships

```
ResolveLocationOutput  (CoordResult|AdmCodeResult|AddressResult|POIResult|ResolveBundle|ResolveError)
        │ feeds into (via LLM planning, not in-code chaining)
        ▼
LookupSearchInput  ──search──▶  LookupSearchResult (candidates: list[AdapterCandidate])
                                        │
                                        ▼ (LLM picks one tool_id)
LookupFetchInput   ──fetch───▶  LookupRecord|Collection|Timeseries|Error (from GovAPITool.handler)
                                        │
                                        ▼ (pre-handler gate)
                                 Layer3AuthGate → LookupError(auth_required)  [if PII-flagged]
```

## 10. Non-Goals (Explicit)

- No ORM / no persistence layer — registry is in-memory per process
- No caching layer in this spec (cache_ttl_seconds=0 for all four seeds; caching is deferred item)
- No retry logic at the envelope layer (wrapping only — retry is deferred)
- No `kind="compound"` or multi-adapter composition in `mode="fetch"` (deferred)
