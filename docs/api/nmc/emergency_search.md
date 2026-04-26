---
tool_id: nmc_emergency_search
primitive: lookup
tier: live
permission_tier: 3
---

# nmc_emergency_search

## Overview

Queries the National Medical Center (국립중앙의료원) real-time emergency room bed availability for the nearest ERs around a given coordinate, returning a ranked list of emergency rooms with available bed counts and freshness-validated data.

| Field | Value |
|---|---|
| Classification | Live · Permission tier 3 |
| Source | National Medical Center (NMC) / api1.odcloud.kr |
| Primitive | `lookup` |
| Module | `src/kosmos/tools/nmc/emergency_search.py` |

## Envelope

**Input model**: `NmcEmergencySearchInput` defined at `src/kosmos/tools/nmc/emergency_search.py:40–76`.

| Field | Type | Required | Description |
|---|---|---|---|
| `lat` | `float` (-90 to 90) | yes | Latitude of the search origin in decimal degrees (WGS-84). Obtain from `resolve_location(want='coords')`. Example: `37.5665` for central Seoul. |
| `lon` | `float` (-180 to 180) | yes | Longitude of the search origin in decimal degrees (WGS-84). Obtain from `resolve_location(want='coords')`. Example: `126.9780` for central Seoul. |
| `limit` | `int` (1–100) | yes | Maximum number of nearest emergency rooms to return. All three fields are required with no defaults — the LLM must supply explicit values. |

**Output model (authenticated, fresh data)**: `LookupCollection` dict returned by `handle()` at `src/kosmos/tools/nmc/emergency_search.py:147–246`.

| Field | Type | Required | Description |
|---|---|---|---|
| `kind` | `str` ("collection") | yes | Envelope type discriminator. |
| `items` | `list[dict]` | yes | Emergency room records from NMC, including bed counts and `hvidate` freshness timestamp. |
| `total_count` | `int` | yes | Total matching ER records from NMC. |
| `meta` | `dict` | yes | Freshness metadata. `{"freshness_status": "fresh"}` when data is within threshold. |

**Output model (stale data — fail-closed)**:

| Field | Type | Required | Description |
|---|---|---|---|
| `kind` | `str` ("error") | yes | Envelope type discriminator. |
| `reason` | `str` ("stale_data") | yes | `LookupErrorReason.stale_data`. |
| `message` | `str` | yes | Human-readable staleness description including data age and threshold. |
| `retryable` | `bool` (False) | yes | Stale data is not retryable — data must be refreshed upstream. |

## Search hints

- 한국어: `응급실`, `실시간 병상`, `응급의료센터`, `국립중앙의료원`, `가까운 응급실`, `응급실 현황`
- English: `emergency room`, `ER bed availability`, `nearest emergency room`, `NMC`, `real-time Korea emergency`, `응급실 찾기`

## Endpoint

- **data.go.kr endpoint**: NMC real-time beds via `api1.odcloud.kr/api/nmc/v1/realtime-beds`
- **Source URL**: https://api1.odcloud.kr/api/nmc/v1/realtime-beds
- **Authentication**: API key via `KOSMOS_DATA_GO_KR_API_KEY` (per Constitution IV)

## Freshness sub-tool

The freshness validation is implemented in `src/kosmos/tools/nmc/freshness.py` (lines 1–91). It is an internal quality-control module — not a citizen-facing tool — and is invoked automatically by `handle()` before any response is returned.

**`check_freshness(hvidate_str, threshold_minutes=None)`** (lines 26–90):
- Accepts the NMC `hvidate` field value (format: `YYYY-MM-DD HH:MM:SS` KST).
- Reads `settings.nmc_freshness_minutes` when `threshold_minutes` is `None`.
- Returns a frozen `FreshnessResult` dataclass (defined at lines 17–24) with four fields: `is_fresh`, `data_age_minutes`, `threshold_minutes`, `hvidate_raw`.
- **Fail-closed design**: missing, empty, unparseable, or future-dated `hvidate` values all return `is_fresh=False` unconditionally. This ensures that any ambiguity about data age is treated as stale rather than passed to the citizen.

**`_evaluate_freshness(items)`** (emergency_search.py lines 98–120): computes the worst-case freshness across all returned ER items. If any single item is missing `hvidate` or is stale, the entire batch is rejected. This prevents a partially-fresh mixed response from reaching the citizen.

The freshness threshold is configurable via `KOSMOS_NMC_FRESHNESS_MINUTES` (default from `settings.nmc_freshness_minutes`). The threshold is visible in every stale-data error message so the LLM can relay the exact age and threshold to the citizen.

## Permission tier rationale

This adapter is classified as Permission tier 3 because real-time emergency room bed availability, when combined with a citizen's session identity, constitutes location-linked health-context data (`pipa_class="personal"`, `is_personal_data=True`, `auth_level="AAL2"`). Under PIPA §23 and the KOSMOS security spec (Spec 033 §2), personal health-context data requires explicit citizen authentication before retrieval. The Layer 3 auth-gate in `executor.invoke()` short-circuits all unauthenticated calls to `LookupError(reason="auth_required")` before `handle()` is ever reached (FR-025, FR-026, SC-006). A `dpa_reference="dpa-nmc-v1"` is required per Spec 024 for PIPA-personal tools. The adapter also enforces a freshness SLO: stale ER data in an emergency context would be actively harmful, so the response is rejected (not degraded) when data exceeds the freshness threshold.

## Worked example

### Input envelope

```json
{
  "mode": "fetch",
  "tool_id": "nmc_emergency_search",
  "params": {
    "lat": 37.5665,
    "lon": 126.9780,
    "limit": 3
  }
}
```

### Output envelope (success — authenticated, fresh data)

```json
{
  "tool_id": "nmc_emergency_search",
  "result": {
    "kind": "collection",
    "items": [
      {
        "dutyName": "서울특별시 중앙응급의료센터",
        "hvidate": "2026-04-26 09:45:00",
        "hvgc": 4,
        "hvec": 2
      }
    ],
    "total_count": 1,
    "meta": {
      "freshness_status": "fresh"
    }
  }
}
```

### Output envelope (unauthenticated — fail-closed)

When the caller has no valid session identity, the Layer 3 auth-gate rejects the call before `handle()` is reached:

```json
{
  "tool_id": "nmc_emergency_search",
  "result": {
    "kind": "error",
    "reason": "auth_required",
    "message": "nmc_emergency_search requires citizen authentication (requires_auth=True). Please log in to continue.",
    "retryable": false
  }
}
```

### Output envelope (stale data — fail-closed)

```json
{
  "tool_id": "nmc_emergency_search",
  "result": {
    "kind": "error",
    "reason": "stale_data",
    "message": "NMC data is stale: 35 min old (threshold: 30 min)",
    "retryable": false
  }
}
```

### Conversation snippet

```text
Citizen: 지금 근처 응급실 병상 현황을 알려주세요.
KOSMOS: 현재 위치(서울 중심부) 기준 가장 가까운 응급실 정보를 조회했습니다. '서울특별시 중앙응급의료센터'에 일반 병상 4개, 중환자 병상 2개가 가용 중입니다. 데이터는 09시 45분 기준으로 신선합니다. (주의: 이 기능은 본인 인증이 필요합니다.)
```

## Constraints

- **Rate limit**: `rate_limit_per_minute=10`; NMC API quota applies per service key.
- **Freshness window**: `cache_ttl_seconds=0` — no client-side caching. Freshness threshold is controlled by `KOSMOS_NMC_FRESHNESS_MINUTES` (see Freshness sub-tool section above). Stale responses are rejected rather than degraded.
- **Fixture coverage gaps**: Live NMC auth is provisioned at the API level; the handler is implemented. CI tests do not call the live endpoint (AGENTS.md hard rule: never call live `data.go.kr` APIs from CI). Fixture shapes for ER-specific fields (e.g., `hvgc`, `hvec`, `hvidate`) are derived from NMC published schema; exact field names depend on the NMC wire format version.
- **Error envelope examples**:
  - Unauthenticated call (Layer 3 gate): `{"kind": "error", "reason": "auth_required", "message": "...", "retryable": false}`.
  - Stale data (freshness SLO): `{"kind": "error", "reason": "stale_data", "message": "NMC data is stale: N min old (threshold: M min)", "retryable": false}`.
  - Missing API key: `{"kind": "error", "reason": "upstream_unavailable", "message": "KOSMOS_DATA_GO_KR_API_KEY is not configured", "retryable": false}`.
  - Non-JSON upstream response: `{"kind": "error", "reason": "upstream_unavailable", "message": "NMC API returned non-JSON content-type: ...", "retryable": true}`.
  - NMC API error code: `{"kind": "error", "reason": "upstream_unavailable", "message": "NMC API error: resultCode=...", "retryable": true}`.
