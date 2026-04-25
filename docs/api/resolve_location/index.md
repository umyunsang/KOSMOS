---
tool_id: resolve_location
primitive: lookup
tier: live
permission_tier: 1
---

# resolve_location

## Overview

Converts a free-text Korean place reference (address, neighborhood, administrative region, or landmark) into structured location identifiers — coordinates, 10-digit 행정동 code, road/jibun address, or a point of interest — by dispatching across three geocoding backends in a deterministic chain.

| Field | Value |
|---|---|
| Classification | Live · Permission tier 1 |
| Source | KOSMOS harness-internal meta-tool (ministry: `KOSMOS`); dispatches to three external geocoding backends |
| Primitive | `lookup` (meta-tool, always `want` = target variant) |
| Module | `src/kosmos/tools/resolve_location.py` + `src/kosmos/tools/geocoding/{kakao_client.py,juso.py,sgis.py,region_mapping.py}` |

## Envelope

**Input model**: `ResolveLocationInput` defined at `src/kosmos/tools/models.py:536–558`.

| Field | Type | Required | Description |
|---|---|---|---|
| `query` | `str` (1–200 chars) | yes | Free-text Korean or English place query, e.g. `"서울 강남구"` or `"Gwangwhamun"` |
| `want` | `Literal["coords", "adm_cd", "coords_and_admcd", "road_address", "jibun_address", "poi", "all"]` | no | Which identifier to resolve. Default `"coords_and_admcd"` returns a `ResolveBundle` |
| `near` | `tuple[float, float] | None` | no | Optional `[lat, lon]` tiebreaker for ambiguous queries |

**Output model**: `ResolveLocationOutput` — a 6-variant discriminated union on `kind` defined at `src/kosmos/tools/models.py:569–655`.

| Variant (`kind`) | Type | Description |
|---|---|---|
| `"coords"` | `CoordResult` | WGS-84 lat/lon + confidence (`high`/`medium`/`low`) + source backend |
| `"adm_cd"` | `AdmCodeResult` | 10-digit 법정동 code + administrative name + level (`sido`/`sigungu`/`eupmyeondong`) |
| `"address"` | `AddressResult` | Structured road address (도로명) and/or jibun address (지번) + postal code |
| `"poi"` | `POIResult` | Point of interest with name, category, and lat/lon |
| `"bundle"` | `ResolveBundle` | Composite result: coords + adm_cd + optional address + optional poi |
| `"error"` | `ResolveError` | Structured failure with reason code (`not_found`, `ambiguous`, `upstream_unavailable`, `invalid_query`, `empty_query`, `out_of_domain`) |

### Backend dispatch: three variants of a single tool

`resolve_location` is a single registered tool that dispatches across three geocoding backends internally. The backends are NOT exposed as separate LLM tools (FR-003). The resolver chain is deterministic and short-circuits on the first non-error result for the requested `want` type.

#### Variant A — Kakao Local API (`source: "kakao"`)

- **Endpoint**: `GET https://dapi.kakao.com/v2/local/search/address.json`
- **Source URL**: https://developers.kakao.com/docs/latest/ko/local/dev-guide
- **Authentication**: REST API key via `Authorization: KakaoAK {key}` header. Key source: `KOSMOS_KAKAO_API_KEY` environment variable.
- **Used for**: `coords`, `road_address`, `jibun_address`, `poi`, and the coords component of `coords_and_admcd` / `all`.
- **Timeout**: 5 seconds (`_DEFAULT_TIMEOUT`).
- **Pydantic models**: `KakaoSearchResult`, `KakaoAddressDocument`, `KakaoRoadAddressResult`, `KakaoAddressResult`, `KakaoSearchMeta` defined at `src/kosmos/tools/geocoding/kakao_client.py:39–168`.

#### Variant B — 행정안전부 도로명주소 API, JUSO (`source: "juso"`)

- **Endpoint**: `GET https://business.juso.go.kr/addrlink/addrLinkApi.do`
- **Source URL**: https://www.juso.go.kr/addrlink/openApi/searchApi.do
- **Authentication**: API confirm key via `confmKey` query parameter. Key source: `KOSMOS_JUSO_CONFM_KEY` environment variable.
- **Used for**: `adm_cd` (primary), `road_address` fallback.
- **Returns**: 10-digit `admCd` + `roadAddr` + `siNm` + `sggNm`. Level derived from trailing zeros in `admCd`.
- **Timeout**: 10 seconds.
- **Backend function**: `lookup_adm_cd` defined at `src/kosmos/tools/geocoding/juso.py:24–103`.

#### Variant C — 통계청 SGIS 통계지리정보 (`source: "sgis"`)

- **Endpoint**: Auth `GET https://sgisapi.kostat.go.kr/OpenAPI3/auth/authentication.json` → rgeocode `GET https://sgisapi.kostat.go.kr/OpenAPI3/addr/rgeocode.json`
- **Source URL**: https://sgis.kostat.go.kr/developer/
- **Authentication**: Two-step — consumer key + secret (`KOSMOS_SGIS_KEY`, `KOSMOS_SGIS_SECRET`) to obtain a short-lived `accessToken`, then `accessToken` on the rgeocode call.
- **Used for**: `adm_cd` fallback when JUSO fails; requires coordinates from Kakao as input.
- **Returns**: 8-digit `adm_cd` (padded to 10 digits) + `adm_nm`. Level derived from trailing zeros.
- **Timeout**: 10 seconds.
- **Backend function**: `lookup_adm_cd_by_coords` defined at `src/kosmos/tools/geocoding/sgis.py:28–127`.

### Full resolver chain by `want` value

| `want` | Resolver chain |
|---|---|
| `"coords"` | Kakao only → error on miss |
| `"adm_cd"` | JUSO → Kakao (coords) + SGIS → error on miss |
| `"road_address"` / `"jibun_address"` | Kakao → JUSO (adm_cd name only) → error if specific address not found |
| `"poi"` | Kakao only → error on miss |
| `"coords_and_admcd"` | Kakao (coords) + JUSO → SGIS fallback → `ResolveBundle` |
| `"all"` | Single Kakao call for coords + address + poi; JUSO / SGIS for adm_cd → `ResolveBundle` |

## Search hints

- 한국어: `주소`, `위치`, `좌표`, `행정동코드`, `도로명주소`, `지번주소`, `장소검색`
- English: `geocode`, `location`, `coordinates`, `administrative code`, `address lookup`, `place search`

## Endpoint

- **data.go.kr endpoint**: N/A — this is a KOSMOS harness-internal meta-tool that calls external geocoding APIs directly (not via data.go.kr).
- **Source URL**: Kakao (https://developers.kakao.com/docs/latest/ko/local/dev-guide), JUSO (https://www.juso.go.kr/addrlink/openApi/searchApi.do), SGIS (https://sgis.kostat.go.kr/developer/)
- **Authentication**: `KOSMOS_KAKAO_API_KEY` (Kakao), `KOSMOS_JUSO_CONFM_KEY` (JUSO), `KOSMOS_SGIS_KEY` + `KOSMOS_SGIS_SECRET` (SGIS)

## Permission tier rationale

This adapter sits at permission tier 1 (green ⓵) because location resolution is a non-personal, read-only lookup. The query string is a place reference — not a citizen identifier — and the returned coordinates and administrative codes do not constitute PII under PIPA. Spec 033 defines tier 1 for public or lightly-authenticated lookups that carry no personal data. The Kakao and JUSO APIs require API keys at the service level (not at the citizen level); no OAuth or citizen identity assertion is required. The meta-tool registers under the `KOSMOS` ministry with `auth_type="api_key"` and `auth_level="AAL1"`.

## Worked example

### Input envelope

```json
{
  "mode": "fetch",
  "tool_id": "resolve_location",
  "params": {
    "query": "서울특별시 강남구 테헤란로 152",
    "want": "coords_and_admcd"
  }
}
```

### Output envelope (success)

```json
{
  "kind": "bundle",
  "source": "bundle",
  "coords": {
    "kind": "coords",
    "lat": 37.50032,
    "lon": 127.03665,
    "confidence": "high",
    "source": "kakao"
  },
  "adm_cd": {
    "kind": "adm_cd",
    "code": "1168010500",
    "name": "서울특별시 강남구",
    "level": "sigungu",
    "source": "juso"
  },
  "address": null,
  "poi": null
}
```

### Conversation snippet

```text
Citizen: 서울 강남구 테헤란로 152의 좌표와 행정동 코드를 알려줘.
KOSMOS: 해당 주소의 좌표는 위도 37.50032, 경도 127.03665이며, 행정동 코드는 서울특별시 강남구(1168010500)입니다.
```

## Constraints

- **Rate limit**:
  - Kakao Local API: free tier 100,000 calls/day; `Authorization: KakaoAK` header required. HTTP 429 is propagated as `httpx.HTTPStatusError` and surfaced by the recovery classifier.
  - JUSO API: public free tier approximately 10,000 calls/month (varies by service key tier); heavy usage requires upgrade at https://www.juso.go.kr/.
  - SGIS API: access-token TTL is short-lived (typically minutes); each token fetch consumes one authentication call against the daily quota.
- **Freshness window**: Kakao geocoding data reflects the Kakao map data refresh cycle (irregular, typically monthly). JUSO address data follows the 행정안전부 road-address registry update cycle (roughly quarterly). SGIS region data follows the 통계청 행정구역 코드 table, updated annually.
- **Fixture coverage gaps**: This is a live-tier tool; there are no static fixtures. Test injection is available by passing an `httpx.AsyncClient` mock to `resolve_location(inp, client=mock_client)`.
- **Error envelope examples**:
  - Tier-1 fail (not found): `{"kind": "error", "reason": "not_found", "message": "Could not resolve coordinates for query '존재하지않는주소'."}`
  - Tier-2 / Tier-3 (auth) fail — Kakao 401: `httpx.HTTPStatusError` with `response.status_code == 401`; recovery classifier maps to `{"kind": "error", "reason": "upstream_unavailable", "message": "Kakao API authentication expired — check KOSMOS_KAKAO_API_KEY"}`.
  - Kakao rate limit (429): `httpx.HTTPStatusError` with `response.status_code == 429`; recovery classifier maps to `{"kind": "error", "reason": "upstream_unavailable", "message": "Kakao API rate limit exceeded"}`.
  - Network timeout: `httpx.TimeoutException` propagated from any backend; mapped to `{"kind": "error", "reason": "upstream_unavailable", "message": "geocoding backend did not respond within 10s"}`.
  - JUSO key not configured: `resolve_location` silently skips JUSO (`KOSMOS_JUSO_CONFM_KEY` not set → `_juso_adm_cd` returns `None`) and falls through to SGIS; if all backends miss, surfaces `not_found`.
