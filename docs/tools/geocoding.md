# Geocoding Tool Adapters

주소→좌표/지역코드 변환 (Address Geocoding — Kakao Local API)

## Overview

The geocoding adapters convert free-form Korean address strings into structured
location data used by other KOSMOS tools. Both adapters call the Kakao Local API
(`dapi.kakao.com`) as the primary geocoding source and fall back to built-in
static tables when the API is unavailable or returns no results.

| Tool ID | Korean Name (`name_ko`) | Primary Output | Downstream Use |
|---------|-------------------------|----------------|---------------|
| [`address_to_region`](#address_to_region) | 주소→지역코드 변환 (시도/구군) | KOROAD `SidoCode` + `GugunCode` | `koroad_accident_search` |
| [`address_to_grid`](#address_to_grid) | 주소→기상청 격자좌표 변환 (nx/ny) | KMA grid (nx, ny) | `kma_*` weather adapters |

## Prerequisites

Both adapters share a single environment variable:

```
KOSMOS_KAKAO_API_KEY
```

This is the **REST API key** issued by Kakao Developers. It is sent as:

```
Authorization: KakaoAK {KOSMOS_KAKAO_API_KEY}
```

Before using either adapter, activate the Kakao Local API in Kakao Developers:

```
앱 설정 → 제품 설정 → 카카오맵 → 사용 설정 → 상태 ON
```

Platform registration (Android/iOS) is **not** required for server-side REST
calls. Obtain the REST API key at [developers.kakao.com](https://developers.kakao.com/).

If `KOSMOS_KAKAO_API_KEY` is not set, both adapters raise
`ConfigurationError: KOSMOS_KAKAO_API_KEY not set` before any HTTP call is made.

---

## `address_to_region`

주소→지역코드 변환 (시도/구군)

### Overview

| Field | Value |
|-------|-------|
| Tool ID | `address_to_region` |
| Korean Name (`name_ko`) | 주소→지역코드 변환 (시도/구군) |
| Provider | 카카오 (Kakao) |
| Endpoint | `https://dapi.kakao.com/v2/local/search/address.json` |
| Auth Type | `api_key` — `KOSMOS_KAKAO_API_KEY` |
| Rate Limit | 30 calls / minute (client-side) |
| Cache TTL | 86400 seconds (24 hours) |
| Personal Data | No |
| Concurrency Safe | Yes |

Resolves a free-form Korean address to the KOROAD province (`SidoCode`) and
district (`GugunCode`) integer codes. These codes are the required inputs for
`koroad_accident_search`. The district lookup is **province-aware**: ambiguous
district names such as "중구" or "남구" appear in multiple cities and are
resolved against the already-resolved `SidoCode`.

**Execution flow:**
1. Call `dapi.kakao.com/v2/local/search/address.json` with the address string.
2. Extract `region_1depth_name` and `region_2depth_name` from the first document,
   preferring the `road_address` block over the legacy `address` block.
3. Map names to `SidoCode` and `GugunCode` via the built-in region mapping table.
4. Return codes together with canonical address string and WGS-84 coordinates.

### Input Schema (`AddressToRegionInput`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `address` | `str` (min length 1) | Yes | Free-form Korean address string (e.g. "서울특별시 강남구 테헤란로 152") |

### Output Schema (`AddressToRegionOutput`)

| Field | Type | Description |
|-------|------|-------------|
| `resolved_address` | `str` | Canonical address as returned by Kakao. Empty string when no match |
| `latitude` | `float \| None` | WGS-84 latitude; `None` when no match |
| `longitude` | `float \| None` | WGS-84 longitude; `None` when no match |
| `region_1depth` | `str` | Province/city name (시도) from Kakao (e.g. "서울특별시") |
| `region_2depth` | `str` | District name (구군) from Kakao (e.g. "강남구") |
| `sido_code` | `int \| None` | KOROAD `SidoCode` integer; `None` when no match or unmapped |
| `gugun_code` | `int \| None` | KOROAD `GugunCode` integer; `None` when unmapped |

### Fail-Closed Behavior

| Condition | Behavior |
|-----------|----------|
| `KOSMOS_KAKAO_API_KEY` not set | Raises `ConfigurationError` immediately |
| Kakao returns no documents | Raises `ToolExecutionError("Address not found")` |
| Kakao returns multiple documents | Raises `ToolExecutionError("Ambiguous address")` |
| Province name not in mapping table | `sido_code=None` (fail-closed, not guessed) |
| District not modelled for province | `gugun_code=None` (fail-closed, not guessed) |
| HTTP 401 | `httpx.HTTPStatusError` propagated (auth_expired path) |
| HTTP 429 | `httpx.HTTPStatusError` propagated (rate_limit path) |
| Timeout | `httpx.TimeoutException` propagated |

> **Note on unmapped districts**: Province-level 도 districts (e.g. "수원시" in
> Gyeonggi) are intentionally not modelled — Kakao returns a city name at
> `region_2depth_name` which does not map 1-to-1 to a KOROAD gugun code. The
> adapter returns `gugun_code=None` rather than guessing.

### Region Mapping Coverage

The built-in mapping table covers all 17 시도 values, including post-2023 names:

| Province name forms mapped | SidoCode |
|----------------------------|----------|
| "서울", "서울시", "서울특별시" | `SEOUL` (11) |
| "부산", "부산시", "부산광역시" | `BUSAN` (26) |
| "강원", "강원도", "강원특별자치도" | `GANGWON` (51) |
| "전북", "전라북도", "전북특별자치도" | `JEONBUK` (52) |
| … (all 17 sido, short + long forms) | — |

District tables (구군) are modelled for Seoul and all 6 metropolitan cities
(Busan, Daegu, Incheon, Gwangju, Daejeon, Ulsan). Province-level cities fall
through to `gugun_code=None`.

Full mapping source:
[`src/kosmos/tools/geocoding/region_mapping.py`](../../src/kosmos/tools/geocoding/region_mapping.py)

### Usage Example

```python
import asyncio
from kosmos.tools.geocoding.address_to_region import _call, AddressToRegionInput

async def get_region_codes():
    params = AddressToRegionInput(address="서울특별시 강남구 테헤란로 152")
    result = await _call(params)
    print(f"sido_code={result['sido_code']}, gugun_code={result['gugun_code']}")
    # → sido_code=11, gugun_code=680

asyncio.run(get_region_codes())
```

If `KOSMOS_KAKAO_API_KEY` is not set, this raises
`ConfigurationError: KOSMOS_KAKAO_API_KEY not set`.

---

## `address_to_grid`

주소→기상청 격자좌표 변환 (nx/ny)

### Overview

| Field | Value |
|-------|-------|
| Tool ID | `address_to_grid` |
| Korean Name (`name_ko`) | 주소→기상청 격자좌표 변환 (nx/ny) |
| Provider | 카카오 (Kakao) + 기상청 (KMA) |
| Endpoint | `https://dapi.kakao.com/v2/local/search/address.json` |
| Auth Type | `api_key` — `KOSMOS_KAKAO_API_KEY` |
| Rate Limit | 30 calls / minute (client-side) |
| Cache TTL | 86400 seconds (24 hours) |
| Personal Data | No |
| Concurrency Safe | Yes |

Resolves a free-form Korean address to KMA 5 km grid (`nx`, `ny`) coordinates
used by KMA weather APIs (초단기실황, 단기예보, 초단기예보). The grid is computed
via the KMA Lambert Conformal Conic (LCC) projection. When the Kakao API times
out or returns no results, the adapter falls back to the built-in KMA region
static table.

**Execution flow:**
1. Call `dapi.kakao.com/v2/local/search/address.json` with the address string.
2. Extract `(latitude, longitude)` from `doc.y` / `doc.x` of the first document.
3. Convert (lat, lon) to (nx, ny) using the KMA LCC projection
   (`kosmos.tools.kma.grid_coords.latlon_to_grid`).
4. On Kakao timeout or zero results, fall back to
   `kosmos.tools.kma.grid_coords.lookup_grid` using progressively shorter
   prefix tokens of the raw address string.
5. If neither resolves, raise `ToolExecutionError`.

### Input Schema (`AddressToGridInput`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `address` | `str` (min length 1) | Yes | Free-form Korean address string (e.g. "서울특별시 서초구 반포대로 201") |

### Output Schema (`AddressToGridOutput`)

| Field | Type | Description |
|-------|------|-------------|
| `resolved_address` | `str` | Canonical address as returned by Kakao. Empty string when not found |
| `latitude` | `float \| None` | WGS-84 latitude; `None` when not found |
| `longitude` | `float \| None` | WGS-84 longitude; `None` when not found |
| `nx` | `int \| None` | KMA grid X coordinate; `None` when address could not be resolved |
| `ny` | `int \| None` | KMA grid Y coordinate; `None` when address could not be resolved |
| `source` | `str` | Resolution method (see table below) |

#### `source` values

| Value | Meaning |
|-------|---------|
| `"kakao_latlon"` | Resolved via Kakao API + KMA LCC projection |
| `"table_fallback"` | Kakao timed out or returned no results; static KMA table used |
| `"not_found"` | Neither Kakao nor the static table matched — this triggers `ToolExecutionError` |

### Fail-Closed Behavior

| Condition | Behavior |
|-----------|----------|
| `KOSMOS_KAKAO_API_KEY` not set | Raises `ConfigurationError` immediately |
| Kakao returns multiple documents | Raises `ToolExecutionError("Ambiguous address")` |
| Kakao times out | Falls back to static KMA table automatically |
| Kakao returns no results | Falls back to static KMA table automatically |
| Both Kakao and static table fail | Raises `ToolExecutionError("Address not found")` |
| HTTP 401 | `httpx.HTTPStatusError` propagated (auth_expired path) |
| HTTP 429 | `httpx.HTTPStatusError` propagated (rate_limit path) |
| Invalid coordinates in Kakao response | Returns `source="not_found"`, triggers error |

> **Key difference from `address_to_region`**: On Kakao timeout, `address_to_grid`
> silently falls back to the static KMA table rather than raising immediately.
> This is intentional — the static table is sufficient for coarse weather grid
> lookups where a district-level match is acceptable.

### Reference Grid Points

| Location | Coordinates | KMA Grid (nx, ny) |
|----------|-------------|-------------------|
| Seoul City Hall | 37.5665, 126.9780 | ~(60, 127) |
| Seocho-gu | 37.5039, 127.0089 | ~(61, 124) |
| Gangnam-gu | 37.5002, 127.0362 | ~(61, 125) |
| Busan Haeundae | 35.1588, 129.1603 | ~(99, 76) |
| Jeju Island | 33.4890, 126.4983 | ~(52, 38) |

### Usage Example

```python
import asyncio
from kosmos.tools.geocoding.address_to_grid import _call, AddressToGridInput

async def get_weather_grid():
    params = AddressToGridInput(address="부산광역시 해운대구 해운대해변로 264")
    result = await _call(params)
    print(f"nx={result['nx']}, ny={result['ny']}, source={result['source']}")
    # → nx=97, ny=74, source=kakao_latlon (approximately)

asyncio.run(get_weather_grid())
```

---

## Rate Limits

| Service | Limit | Notes |
|---------|-------|-------|
| Kakao Local API | 30 calls / minute (KOSMOS client-side) | Kakao's actual server-side quota is higher but varies by plan |
| Kakao API daily quota | Varies by plan | Check Kakao Developers dashboard |

Both adapters share the same upstream endpoint. Run them concurrently with care
when fanning out to multiple addresses.

---

## Error Handling Reference

Unlike `data.go.kr` adapters, the Kakao API returns proper HTTP status codes
for errors (no `resultCode` field in the body).

| HTTP Status | Meaning | Adapter behavior |
|-------------|---------|-----------------|
| `200` | Success | Parse and return data |
| `400` | Bad request (missing required parameter) | `httpx.HTTPStatusError` propagated |
| `401` | Unauthorized (invalid or missing REST API key) | `httpx.HTTPStatusError` propagated — maps to `auth_expired` in recovery classifier |
| `429` | Too Many Requests (rate limit exceeded) | `httpx.HTTPStatusError` propagated — maps to `rate_limit` in recovery classifier |
| `5xx` | Kakao server error | `httpx.HTTPStatusError` propagated |
| Timeout | Connection/read timeout | `httpx.TimeoutException` propagated; `address_to_grid` automatically tries static fallback |

All HTTP errors are propagated directly (not wrapped in `ToolExecutionError`) so
the KOSMOS recovery classifier can recognise and route them correctly.

---

## Testing

### Unit tests (mock-based, always run)

| File | Coverage |
|------|----------|
| `tests/tools/geocoding/test_address_to_region.py` | `address_to_region` happy path, no-results, ambiguous, missing key |
| `tests/tools/geocoding/test_address_to_grid.py` | `address_to_grid` Kakao path, timeout fallback, static table, missing key |
| `tests/tools/geocoding/test_kakao_client.py` | `search_address` HTTP layer, auth header, error propagation |
| `tests/tools/geocoding/test_grid_conversion.py` | `latlon_to_grid` LCC projection against known reference points |
| `tests/tools/geocoding/test_region_mapping.py` | `region1_to_sido` / `region2_to_gugun` mapping table completeness |

Recorded fixtures are under `tests/tools/geocoding/fixtures/`:
- `address_to_region_gangnam.json` — Seoul/Gangnam canonical response
- `address_to_region_busan.json` — Busan/Haeundae response
- `address_to_region_nonsense.json` — empty-results response
- `address_to_grid_seocho.json` — Seoul/Seocho grid resolution
- `address_to_grid_haeundae.json` — Busan/Haeundae grid resolution

### Live tests (opt-in, require `KOSMOS_KAKAO_API_KEY`)

```bash
uv run pytest tests/live/test_live_geocoding.py -m live -v
```

| Test ID | What it verifies |
|---------|-----------------|
| T005 | `search_address` happy path — at least one document, coordinates in Korea bounding box |
| T006 | `search_address` nonsense query — empty documents list, no exception |
| T007 | `address_to_grid` Seoul landmark — nx in [57, 63], ny in [124, 130] |
| T008 | `address_to_grid` Busan landmark — nx in [95, 100], ny in [73, 78] |
| T009 | `address_to_region` Gangnam — `sido_code=11`, `gugun_code=680` |
| T010 | `address_to_region` Busan — `sido_code=26` |
| T011 | `address_to_region` unmapped region (울릉도) — structured output or `ToolExecutionError`, no crash |

Live tests are never run in CI. They require activating the Kakao Local API
service in Kakao Developers before running.

---

## References

- [Kakao Developers — Local API](https://developers.kakao.com/docs/latest/ko/local/dev-guide)
- [Kakao Local API — `search/address.json`](https://developers.kakao.com/docs/latest/ko/local/dev-guide#address-coord)
- KMA LCC projection implementation: [`src/kosmos/tools/kma/grid_coords.py`](../../src/kosmos/tools/kma/grid_coords.py)
- KOROAD code tables: [`src/kosmos/tools/koroad/code_tables.py`](../../src/kosmos/tools/koroad/code_tables.py)
- Region mapping table: [`src/kosmos/tools/geocoding/region_mapping.py`](../../src/kosmos/tools/geocoding/region_mapping.py)
- Downstream tool that consumes `address_to_region`: [`koroad.md`](koroad.md)
- Downstream tools that consume `address_to_grid`: [`kma-observation.md`](kma-observation.md), [`kma-short-term-forecast.md`](kma-short-term-forecast.md), [`kma-ultra-short-term-forecast.md`](kma-ultra-short-term-forecast.md)
