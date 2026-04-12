# Implementation Plan: Phase 1 API Adapters (KOROAD, KMA, Road Risk)

**Epic**: #7
**Spec**: `specs/007-api-adapters/spec.md`
**Created**: 2026-04-13
**Layer**: Layer 2 — Tool System

---

## Phase 0: Research Findings

### Reference Source Mapping

Every design decision in this plan maps to a concrete reference per constitution § I.

| Design Decision | Primary Reference | Secondary Reference |
|---|---|---|
| Tool module shape (`GovAPITool` field contract) | Pydantic AI — schema-driven tool registry | Claude Agent SDK — tool definitions |
| Fail-closed defaults (`requires_auth=True`, etc.) | Constitution § II (already codified in `GovAPITool`) | Claude Code sourcemap — permission model |
| Adapter dispatch pipeline | `ToolExecutor` from Epic #6 (already built) | Claude Code sourcemap — tool execution flow |
| data.go.kr wire format (serviceKey, XML/JSON) | PublicDataReader (`WooilJeong/PublicDataReader`) | Official KMA/KOROAD API guides |
| XML fallback parsing | PublicDataReader — observed XML-defaulting endpoints | KOROAD guide specifying `_type=json` |
| Async HTTP with httpx | Claude Agent SDK — async generator tool loop | LangGraph `ToolNode` — async tool execution |
| Rate-limit enforcement | Existing `RateLimiter` + `ToolRegistry.get_rate_limiter()` | OpenAI Agents SDK — retry matrix |
| `asyncio.gather` for composite | Claude Agent SDK — async generator pattern | Anthropic Cookbook — orchestrator-workers |
| Pydantic v2 field validators for mixed types | LangGraph — `ValidationError` fail-closed lesson at tool boundary | Pydantic AI — strict schema |
| Bilingual `search_hint` | Korean Public APIs index (`yybmion/public-apis-4Kr`) | docs/vision.md § Layer 2 lazy discovery |
| `is_core=True` for Scenario 1 tools | docs/vision.md § Layer 2 prompt cache partitioning | Claude Code sourcemap — core tool set |

### Wire Format Observations (from PublicDataReader and official guides)

1. **KOROAD `getRestFrequentzoneLg`**: Defaults to XML. JSON requested with `_type=json`. Response wraps results in `response.body.items.item[]`. A single-result response may return an object (not array) for `item` — adapters must normalize both shapes.
2. **KMA `getPwnStatus`**: Defaults to XML. JSON requested with `dataType=JSON`. Response structure: `response.body.items.item[]`. Empty results return `items` as `""` or `null`, not an empty array — adapters must guard against this.
3. **KMA `getUltraSrtNcst`**: Same JSON request pattern as `getPwnStatus`. Returns `category/obsrValue` row-per-observation-element format. A single grid point returns 8 categories (T1H, RN1, UUU, VVV, WSD, REH, PTY, VEC). The adapter must pivot from a list of `{category, obsrValue}` rows to a flat output model.
4. **Error codes**: All three providers use `resultCode` in the `response.header`. The only success value is `"00"`. All other codes (e.g., `"03"` = no data, `"10"` = invalid key, `"30"` = data limit exceeded) must be mapped to `error_type="execution"` in `ToolResult`.

### Known Quirks Requiring Implementation Action

| Quirk | Scope | Action Required |
|---|---|---|
| `sido` code change: 42→51 (Gangwon), 45→52 (Jeonbuk) from 2023 | `SidoCode` enum + `KoroadAccidentSearchInput` validator | Cross-validator emits `ValidationError` with correction hint if old code + 2023+ year code |
| `RN1 = "-"` for no precipitation (not null, not 0) | `KmaCurrentObservationOutput.rn1` | `@field_validator` normalizes `"-"`, `null`, `"0"` all to `0.0` |
| `getUltraSrtNcst` data unavailable in first 10 min of hour | `kma_current_observation` adapter | Retry once with previous hour's `base_time` before surfacing error |
| `items` returned as `""` (empty string) vs `[]` for no-result KMA queries | Both KMA adapters | Normalize: treat empty string, null, missing as empty list |
| Single-item `item` returned as object instead of array | KOROAD adapter | `items = [items] if isinstance(items, dict) else items` normalization |

---

## Constitution Compliance Check

Validated against `.specify/memory/constitution.md`:

| Rule | Status | Evidence |
|---|---|---|
| § II — `requires_auth=True` default | All four tools comply | KOROAD and KMA tools all specify `requires_auth=True`; `road_risk_score` explicitly sets `False` as a deliberate override (inner tools handle auth) |
| § II — `is_personal_data=True` default | All four tools set `False` with explicit justification | Spec FR-001 through FR-004 document aggregate-only data, no individual records |
| § II — `is_concurrency_safe=False` default | Three tools override to `True` with justification | All are read-only idempotent GETs; justified in spec |
| § III — Pydantic v2, no `Any` | Plan mandates Pydantic v2 throughout | Mixed-type fields (`rn1`, `obsrValue`) use `@field_validator` + explicit union types |
| § IV — No live API calls in CI | Fixture-based tests only; `@pytest.mark.live` for real calls | See Phase 5; all CI tests load from `tests/fixtures/` |
| § IV — No hardcoded credentials | `os.environ` / `pydantic-settings` for all keys | `ConfigurationError` raised on missing env var before any HTTP call |
| § I — Reference mapping | Fully mapped in Phase 0 above | Every decision traces to docs/vision.md § Reference materials |

---

## Architecture

### Module Structure

The spec defines module paths under `src/kosmos/tools/<provider>/`. This plan adopts those paths exactly (as required by `docs/tool-adapters.md § Naming`).

```
src/kosmos/tools/
├── __init__.py                          (existing)
├── models.py                            (existing — GovAPITool, ToolResult, etc.)
├── registry.py                          (existing — ToolRegistry)
├── executor.py                          (existing — ToolExecutor)
├── errors.py                            (existing — KosmosToolError hierarchy)
├── rate_limiter.py                      (existing)
├── search.py                            (existing)
│
├── koroad/
│   ├── __init__.py
│   ├── code_tables.py                   (FR-005: SidoCode, GugunCode, SearchYearCd, HazardType enums)
│   └── koroad_accident_search.py        (FR-001: adapter + tool definition + registration helper)
│
├── kma/
│   ├── __init__.py
│   ├── grid_coords.py                   (FR-006: REGION_TO_GRID lookup dict, LCC coordinate utility)
│   ├── kma_weather_alert_status.py      (FR-002: adapter + tool definition + registration helper)
│   └── kma_current_observation.py       (FR-003: adapter + tool definition + registration helper)
│
└── composite/
    ├── __init__.py
    └── road_risk_score.py               (FR-004: composite adapter calling inner tools via ToolExecutor)
```

### Shared HTTP Client Pattern

Each adapter receives an `httpx.AsyncClient` injected at call time (not module-level global), following the pattern from the Claude Agent SDK's async HTTP pattern. This enables test injection of a mock client without monkey-patching.

Adapter function signature:
```python
async def _call(
    params: KoroadAccidentSearchInput,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, object]:
```

When `client=None`, the adapter creates a short-lived `httpx.AsyncClient` with a 5-second timeout. Tests inject a pre-configured mock client.

### Key loading pattern

```python
import os
from kosmos.tools.errors import KosmosToolError

class ConfigurationError(KosmosToolError):
    """Required environment variable is not set."""

def _require_env(var: str) -> str:
    value = os.environ.get(var)
    if not value:
        raise ConfigurationError(
            f"Required environment variable {var!r} is not set. "
            "Export it before calling this tool."
        )
    return value
```

`ConfigurationError` is raised inside the adapter function (not at import time), so the module can be imported in CI without any keys present. The executor catches it via the broad `except Exception` in Step 5 and returns `error_type="execution"`.

### Composite Adapter Architecture

`road_risk_score` does not make HTTP calls directly. It calls the inner adapters' functions directly (not through `ToolExecutor`) to avoid double rate-limit accounting. The inner tool results are typed (`KoroadAccidentSearchOutput`, `KmaCurrentObservationOutput`) and the scoring logic operates on those typed objects.

Partial-failure handling:
- If KOROAD succeeds but KMA fails: score from accident data only; `data_gaps=["kma_obs"]`
- If KMA succeeds but KOROAD fails: score from weather data only; `data_gaps=["koroad"]`
- If both fail: return `error_type="execution"`; this is the only case where `road_risk_score` itself fails

---

## Data Model Summary

See `specs/007-api-adapters/data-model.md` for complete entity definitions.

**New Pydantic models** (all in `src/kosmos/tools/<subpackage>/`):

| Model | Location | Purpose |
|---|---|---|
| `KoroadAccidentSearchInput` | `koroad/koroad_accident_search.py` | Input: sido, gugun, searchYearCd, pagination |
| `KoroadAccidentSearchOutput` | `koroad/koroad_accident_search.py` | Output: total_count, hotspots list |
| `AccidentHotspot` | `koroad/koroad_accident_search.py` | Sub-model: individual hotspot record |
| `KmaWeatherAlertStatusInput` | `kma/kma_weather_alert_status.py` | Input: numOfRows, pageNo, dataType |
| `KmaWeatherAlertStatusOutput` | `kma/kma_weather_alert_status.py` | Output: total_count, warnings list |
| `WeatherWarning` | `kma/kma_weather_alert_status.py` | Sub-model: individual warning record |
| `KmaCurrentObservationInput` | `kma/kma_current_observation.py` | Input: base_date, base_time, nx, ny |
| `KmaCurrentObservationOutput` | `kma/kma_current_observation.py` | Output: T1H, RN1, WSD, etc. (pivoted from row format) |
| `RoadRiskScoreInput` | `composite/road_risk_score.py` | Input: sido, gugun, nx, ny, hazard_type |
| `RoadRiskScoreOutput` | `composite/road_risk_score.py` | Output: risk_score, risk_level, summary, data_gaps |

**New Enums** (all in `koroad/code_tables.py`):

| Enum | Values |
|---|---|
| `SidoCode` | 11 (Seoul) through 52 (Jeonbuk 2023+); includes legacy codes 42 and 45 with deprecation notes |
| `GugunCode` | Per-sido 3-digit district codes from AccidentHazard_CodeList |
| `SearchYearCd` | All valid year-category opaque codes (e.g., `"2025119"` for 2024 municipality data) |
| `HazardType` | `general`, `ice`, `pedestrian_child`, `pedestrian_elderly`, `bicycle`, `law_violation`, `holiday`, `motorcycle`, `pedestrian`, `drunk_driving`, `freight` |

---

## File Structure (All Files to be Created)

```
src/
└── kosmos/
    └── tools/
        ├── koroad/
        │   ├── __init__.py
        │   ├── code_tables.py
        │   └── koroad_accident_search.py
        ├── kma/
        │   ├── __init__.py
        │   ├── grid_coords.py
        │   ├── kma_weather_alert_status.py
        │   └── kma_current_observation.py
        └── composite/
            ├── __init__.py
            └── road_risk_score.py

tests/
├── fixtures/
│   ├── koroad/
│   │   └── koroad_accident_search.json
│   └── kma/
│       ├── kma_weather_alert_status.json
│       └── kma_current_observation.json
└── tools/
    ├── __init__.py
    ├── test_registration.py
    ├── test_search_integration.py
    ├── koroad/
    │   ├── __init__.py
    │   └── test_koroad_accident_search.py
    ├── kma/
    │   ├── __init__.py
    │   ├── test_kma_weather_alert_status.py
    │   └── test_kma_current_observation.py
    └── composite/
        ├── __init__.py
        └── test_road_risk_score.py

docs/
└── tools/
    ├── koroad.md
    └── kma.md
```

**Total new files**: 20

---

## Phases

### Phase 1: Shared Infrastructure

**Deliverables**:
- `src/kosmos/tools/koroad/__init__.py`
- `src/kosmos/tools/koroad/code_tables.py`
- `src/kosmos/tools/kma/__init__.py`
- `src/kosmos/tools/kma/grid_coords.py`
- `src/kosmos/tools/composite/__init__.py`
- `src/kosmos/tools/errors.py` update — add `ConfigurationError`

**`code_tables.py` implementation notes**:

The `SearchYearCd` enum is large (~100 members). Use string-valued enum:
```python
class SearchYearCd(str, enum.Enum):
    GENERAL_2024 = "2025119"
    GENERAL_2023 = "2024056"
    ICE_2024 = "2025113"
    # ... all values from AccidentHazard_CodeList
```

The `SidoCode` enum marks legacy codes explicitly:
```python
class SidoCode(int, enum.Enum):
    SEOUL = 11
    BUSAN = 26
    # ...
    GANGWON_LEGACY = 42   # use only for searchYearCd pre-2023
    JEONBUK_LEGACY = 45   # use only for searchYearCd pre-2023
    GANGWON = 51
    JEONBUK = 52
```

The `GugunCode` enum is scoped per-sido. Because `GugunCode` values overlap across sido (e.g., both Seoul Jongno-gu and Busan Jung-gu use code 110), the enum alone cannot validate correctness — the cross-validator in `KoroadAccidentSearchInput` handles the combination check.

**`grid_coords.py` implementation notes**:

```python
REGION_TO_GRID: dict[str, tuple[int, int]] = {
    # Key: "{sido_name}/{district_name}" or "{sido_name}" for province centroid
    "서울/중구": (60, 127),
    "서울/강남구": (61, 125),
    "서울/서초구": (61, 124),
    "부산/중구": (98, 76),
    "대전/서구": (67, 100),    # Gyeongbu corridor Daejeon section
    "천안/동남구": (63, 110),   # Gyeongbu corridor Cheonan section
    # ... minimum 17 metro city centroids required for Phase 1
}

def lookup_grid(region_name: str) -> tuple[int, int] | None:
    """Return (nx, ny) for a region name, or None if not found."""
    return REGION_TO_GRID.get(region_name)
```

The KMA LCC coordinate formula (from the C source in the technical guide) is provided as a utility function for future dynamic coordinate computation. Phase 1 uses the hard-coded lookup table.

**Dependency**: Phase 1 has no dependencies. It can start immediately.

---

### Phase 2: KOROAD Adapter

**Deliverables**:
- `src/kosmos/tools/koroad/koroad_accident_search.py`

**Implementation sequence within the file**:
1. Input/output Pydantic models (`KoroadAccidentSearchInput`, `KoroadAccidentSearchOutput`, `AccidentHotspot`)
2. Cross-validator for legacy sido + post-2022 year code combination
3. `_normalize_items()` helper: handles `item` as dict vs list
4. `_parse_response()`: maps JSON response fields to output model
5. `_call()`: async adapter function with httpx client injection
6. `KOROAD_ACCIDENT_SEARCH_TOOL`: `GovAPITool` instance declaration
7. `register(registry: ToolRegistry, executor: ToolExecutor)`: registration helper

**Key implementation detail — `_call()` skeleton**:
```python
async def _call(params: KoroadAccidentSearchInput, *, client=None) -> dict:
    api_key = _require_env("KOSMOS_KOROAD_API_KEY")
    query = {
        "serviceKey": api_key,
        "_type": "json",
        "searchYearCd": params.search_year_cd,
        "siDo": params.si_do,
        "numOfRows": params.num_of_rows,
        "pageNo": params.page_no,
    }
    if params.gu_gun is not None:
        query["guGun"] = params.gu_gun
    
    async with (client or httpx.AsyncClient(timeout=5.0)) as c:
        resp = await c.get(ENDPOINT, params=query)
        resp.raise_for_status()
    
    body = resp.json()
    # Guard: if not JSON (XML fallback), parse with ElementTree, log WARNING
    header = body["response"]["header"]
    if header["resultCode"] != "00":
        raise ToolExecutionError(...)
    
    items = _normalize_items(body["response"]["body"]["items"])
    return _parse_response(header, items)
```

**Dependency**: Requires Phase 1 (`code_tables.py`, `ConfigurationError`).

---

### Phase 3: KMA Adapters

**Deliverables**:
- `src/kosmos/tools/kma/kma_weather_alert_status.py`
- `src/kosmos/tools/kma/kma_current_observation.py`

**`kma_weather_alert_status.py` notes**:
- Input model is minimal (no required fields); `numOfRows` defaults to 2000 to get all active warnings in one page
- Guard against `items = ""` or `items = null` in the response when no warnings are active
- `WeatherWarning.cancel` should filter: if `cancel=1`, the warning is cancelled and should not be in the active list. The adapter filters these out before returning.

**`kma_current_observation.py` notes**:
- The response returns a list of `{category, obsrValue}` rows. The adapter must pivot these into a flat dict before validating against `KmaCurrentObservationOutput`.
- The `rn1` field validator handles three normalized forms: `"-"`, `None`/missing, numeric string.
- The base-time retry logic (EC-002): if `resultCode != "00"` on first call, decrement `base_time` by one hour and retry exactly once.
- `base_time` must be an exact hour (e.g., `"0600"`, not `"0610"`). The adapter normalizes `base_time` input by stripping minutes: `f"{hour:02d}00"`.

**Dependency**: Requires Phase 1 (`grid_coords.py`, `ConfigurationError`). Independent of Phase 2.

---

### Phase 4: Road Risk Composite Adapter

**Deliverables**:
- `src/kosmos/tools/composite/road_risk_score.py`

**Implementation notes**:

The composite adapter imports the inner adapter functions directly:
```python
from kosmos.tools.koroad.koroad_accident_search import _call as _koroad_call
from kosmos.tools.kma.kma_current_observation import _call as _kma_obs_call
```

It does NOT import `kma_weather_alert_status` — the scoring algorithm in the spec uses `active_weather_warnings` count, but the spec's `RoadRiskScoreInput` does not take a KMA alert filter. The composite tool uses only `koroad_accident_search` + `kma_current_observation` for the scoring formula, and queries `kma_weather_alert_status` separately to count active warnings in the vicinity.

Revised design: the composite calls all three inner adapters concurrently:
```python
koroad_result, kma_alert_result, kma_obs_result = await asyncio.gather(
    _koroad_call(koroad_params),
    _kma_alert_call(kma_alert_params),
    _kma_obs_call(kma_obs_params),
    return_exceptions=True,
)
```

Results that are exceptions are treated as data gaps. The scoring algorithm then operates on available data.

**Scoring algorithm** (from spec FR-004, unchanged):
```
base_score = 0.0

# Accident density component (weight 0.5)
hotspot_count → +0.15 / +0.3 / +0.5

# Weather component (weight 0.5)  
active_warnings >= 1 → +0.3
precipitation_mm >= 20 → +0.2; >= 5 → +0.15; >= 1 → +0.05
precipitation_type == 3 (snow) → +0.1

risk_score = min(1.0, base_score)
risk_level: [0, 0.3) = low; [0.3, 0.6) = moderate; [0.6, 0.8) = high; [0.8, 1.0] = severe
```

**Dependency**: Requires Phases 2 and 3.

---

### Phase 5: Tests and Fixture Recording

**Deliverables**:
- `tests/tools/__init__.py`
- `tests/tools/test_registration.py` — SC-001: all four tools register without error
- `tests/tools/test_search_integration.py` — SC-010: `road_risk_score` appears in search results for Scenario 1 query
- `tests/tools/koroad/__init__.py`
- `tests/tools/koroad/test_koroad_accident_search.py`
- `tests/tools/kma/__init__.py`
- `tests/tools/kma/test_kma_weather_alert_status.py`
- `tests/tools/kma/test_kma_current_observation.py`
- `tests/tools/composite/__init__.py`
- `tests/tools/composite/test_road_risk_score.py`
- `tests/fixtures/koroad/koroad_accident_search.json`
- `tests/fixtures/kma/kma_weather_alert_status.json`
- `tests/fixtures/kma/kma_current_observation.json`
- `docs/tools/koroad.md`
- `docs/tools/kma.md`

**Fixture recording procedure** (requires live API keys, run once locally):
```bash
export KOSMOS_KOROAD_API_KEY=<key>
export KOSMOS_DATA_GO_KR_KEY=<key>
uv run python scripts/record_fixture.py koroad_accident_search
uv run python scripts/record_fixture.py kma_weather_alert_status
uv run python scripts/record_fixture.py kma_current_observation
```

Fixtures must be committed under `tests/fixtures/`. Review each fixture before committing to confirm no PII is present.

**Per-adapter test structure**:

Each test module provides exactly:
1. `test_happy_path_from_fixture()` — loads fixture JSON, calls `_parse_response()`, validates against output schema
2. `test_error_path_bad_input()` — passes invalid `sido=99` / out-of-range grid, expects `ValidationError` before HTTP call
3. `test_missing_api_key()` — unsets env var with `monkeypatch.delenv`, calls `_call()`, expects `ConfigurationError`
4. `@pytest.mark.live` test — calls live API, skipped in CI

**`test_road_risk_score.py` structure** (uses mocked inner calls):
1. `test_high_risk_scenario()` — mock: 5 hotspots + 20mm precipitation → assert `risk_level="high"`
2. `test_low_risk_scenario()` — mock: 0 hotspots + 0mm → assert `risk_level="low"`
3. `test_partial_failure_kma()` — mock: KOROAD succeeds + KMA fails → assert partial result with `data_gaps=["kma_obs"]`
4. `test_total_failure()` — mock: both inner adapters fail → assert `error_type="execution"` in return

**Dependency**: Requires Phases 1–4.

---

## Task Decomposition (for `speckit-tasks`)

Proposed task groupings for `tasks.md`:

| Task | Phase | Parallel-safe? | Size |
|---|---|---|---|
| T1: Shared infrastructure (`code_tables.py`, `grid_coords.py`, `ConfigurationError`) | 1 | Yes (no deps) | M |
| T2: KOROAD adapter (`koroad_accident_search.py` + models) | 2 | Yes (after T1) | M |
| T3: KMA WeatherAlert adapter (`kma_weather_alert_status.py` + models) | 3 | Yes (after T1, parallel with T2) | M |
| T4: KMA CurrentObservation adapter (`kma_current_observation.py` + models) | 3 | Yes (after T1, parallel with T2 and T3) | M |
| T5: Road Risk composite adapter (`road_risk_score.py`) | 4 | No (after T2, T3, T4) | M |
| T6: Tests, fixtures, and documentation | 5 | No (after T2–T5) | L |

T2, T3, T4 are fully parallel-safe (different providers, no shared files). T5 must wait for all three adapters. T6 must wait for T5.

---

## Open Questions / Risks

### Resolved

- **Q: Does the KOROAD endpoint accept `guGun` as optional?** A: Yes, spec FR-001 and the official guide both confirm it. Province-level results are returned when `guGun` is omitted.
- **Q: What grid coordinates cover the Gyeongbu Expressway?** A: Spec FR-006 provides Daejeon section (67, 100) and Cheonan section (63, 110). Sufficient for Phase 1.
- **Q: Is `road_risk_score` a genuine `GovAPITool` or just a Python function?** A: It is a `GovAPITool` with `auth_type="public"` and `endpoint=""`. This lets the LLM discover and call it through the standard tool dispatch path.

### Remaining (Low Risk)

- **R1**: The KMA warning zone codes (`areaCode`) format (e.g., `"S1151300"`) is not fully documented in the converted guide. The `WeatherWarning.area_code` field is typed as `str` (not enum) — this is correct; the LLM interprets the Korean `area_name` rather than the opaque code.
- **R2**: The `road_risk_score` composite currently does NOT call `kma_weather_alert_status` to count active warnings (it was not in the original scoring algorithm inputs). The spec's output field `active_weather_warnings` implies it should. Resolution: include `kma_weather_alert_status` as a third inner call in `road_risk_score` (see Phase 4 above). This is a deliberate spec clarification, not a gap.
- **R3**: The `scripts/record_fixture.py` script is promised by the foundation spec (Epic #6) but may not exist yet. If absent, fixtures must be recorded manually with `httpx` or `curl`. This does not block implementation — fixtures can be hand-crafted for CI using realistic synthetic data.
