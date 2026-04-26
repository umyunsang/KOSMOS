# Quickstart — MVP Main-Tool (Epic #507)

End-to-end walkthrough exercising the **full happy + sad path** of the two-tool facade. This is the acceptance scenario the reviewer runs to verify the MVP delivers the spec.

---

## 0. Prerequisites

### 0.1 Required environment variables

```bash
# Geocoding providers
export KOSMOS_KAKAO_REST_KEY="..."          # Kakao Local (coords + address + POI)
export KOSMOS_JUSO_CONFM_KEY="..."          # 도로명주소 API (road/jibun address)
export KOSMOS_SGIS_KEY="..."                # SGIS Consumer Key (10-digit adm_cd)
export KOSMOS_SGIS_SECRET="..."             # SGIS Consumer Secret

# data.go.kr services (KOROAD / KMA / HIRA / NMC all share the same key)
export KOSMOS_DATA_GO_KR_API_KEY="..."

# Retrieval tuning (optional; shown with defaults)
export KOSMOS_LOOKUP_TOPK=5                 # clamped [1, 20]
export KOSMOS_NMC_FRESHNESS_MINUTES=30      # clamped [1, 1440]
```

Issue publication procedure for each key is in **Discussion #508**.

### 0.2 Install

```bash
uv sync                              # pulls rank_bm25, kiwipiepy, httpx, pydantic v2, ...
uv run pytest -q                     # unit tests (no live APIs)
```

Live-API tests are gated by `@pytest.mark.live` and stay skipped in CI.

---

## 1. Launch a conversational session

```bash
uv run python -m kosmos.cli
```

The CLI starts a FriendliAI Serverless (OpenAI-compatible) session against EXAONE with the two-tool schema registered:

- `resolve_location` — places → typed identifiers
- `lookup` — cold-path adapter search + typed fetch

Registry boots with **four seed adapters**: `koroad_accident_hazard_search`, `kma_forecast_fetch`, `hira_hospital_search`, `nmc_emergency_search`.

**Startup invariant check**: any adapter with `is_personal_data=True` but `requires_auth=False` aborts the process with `RegistrationError` (Constitution §II fail-closed).

---

## 2. Walkthrough — Pattern D ("강남역에서 사고나면 가장 가까운 응급실은?")

This single exchange exercises: two-step retrieval, one-to-many coord reuse, Layer 3 PII gate, and graceful fallback. It is the spec's canonical acceptance demo.

### 2.1 User turn

```
사용자: 강남역에서 사고나면 가장 가까운 응급실은?
```

### 2.2 Tool call #1 — resolve_location

```json
{
  "name": "resolve_location",
  "arguments": {"query": "강남역", "want": "coords"}
}
```

Expected output (`CoordResult` variant):

```json
{
  "kind": "coords",
  "lat": 37.498,
  "lon": 127.028,
  "confidence": "high",
  "source": "kakao"
}
```

Provider chain: `kakao → juso → sgis` (short-circuits at first non-error result).

### 2.3 Tool call #2 — lookup.search

```json
{
  "name": "lookup",
  "arguments": {
    "mode": "search",
    "query": "응급실 실시간 병상",
    "domain": "health"
  }
}
```

Expected output (`LookupSearchResult` variant):

```json
{
  "kind": "search",
  "candidates": [
    {
      "tool_id": "nmc_emergency_search",
      "score": 9.73,
      "required_params": ["lat", "lon"],
      "search_hint": "응급실 실시간 병상 · NMC emergency bed availability (near coordinates)",
      "why_matched": "BM25 on 'emergency' + '응급실' + 'bed' + '병상'"
    },
    {
      "tool_id": "hira_hospital_search",
      "score": 7.41,
      "required_params": ["xPos", "yPos", "radius"],
      "search_hint": "병원 위치 검색 · HIRA hospital locator (within radius)",
      "why_matched": "BM25 on 'hospital' + '병원'"
    }
  ],
  "total_registry_size": 4,
  "effective_top_k": 4,
  "reason": "ok"
}
```

`effective_top_k = min(KOSMOS_LOOKUP_TOPK, 4) = 4` for MVP.

### 2.4 Tool call #3 — lookup.fetch → Layer 3 gate fires

```json
{
  "name": "lookup",
  "arguments": {
    "mode": "fetch",
    "tool_id": "nmc_emergency_search",
    "params": {"lat": 37.498, "lon": 127.028, "limit": 5}
  }
}
```

Expected output (`LookupError` variant):

```json
{
  "kind": "error",
  "reason": "auth_required",
  "message": "nmc_emergency_search requires citizen auth (Layer 3 harness stub — no provider implemented in MVP)",
  "retryable": false,
  "meta": null
}
```

**Key observable**: zero upstream HTTP calls were issued. The stub gate short-circuits purely on `tool.is_personal_data=True`. Verify with:

```bash
uv run pytest tests/tools/test_layer3_gate.py -v
```

### 2.5 Tool call #4 — LLM falls back to HIRA

```json
{
  "name": "lookup",
  "arguments": {
    "mode": "fetch",
    "tool_id": "hira_hospital_search",
    "params": {"xPos": 127.028, "yPos": 37.498, "radius": 2000}
  }
}
```

Expected output (`LookupCollection` variant):

```json
{
  "kind": "collection",
  "items": [
    {"ykiho": "...", "yadmNm": "...", "distance_m": 412.0, ...},
    ...
  ],
  "total_count": 14,
  "next_cursor": null,
  "meta": {
    "source": "hira",
    "fetched_at": "2026-04-16T05:12:33Z",
    "request_id": "01HV...",
    "elapsed_ms": 274,
    "rate_limit_remaining": null
  }
}
```

### 2.6 Final user-facing message

```
실시간 병상 정보는 본인인증이 필요해 이번 릴리스에서는 제공하지 않습니다.
대신 강남역 반경 2km 내 응급실 가능 병원 N곳을 거리순으로 안내드립니다.
1. ... 2. ... 3. ...
```

---

## 3. Additional chain patterns (smoke)

| Pattern | Query | Key shape produced |
|---|---|---|
| A — KOROAD code-pair | "강남구 사고다발지역 알려줘" | `LookupCollection` with `spot_nm`, `tot_dth_cnt`, `geom_json` |
| B — KMA LCC grid | "서울 종로구 오늘 날씨 어때?" | `LookupTimeseries` with `temperature_c`, `pop_pct`, `interval="hour"` |
| C — KMA invalid base_time | "...at 1530" | `LookupError(reason="invalid_params", retryable=False)` |
| D — NMC Layer 3 + HIRA fallback | "강남역 응급실" | `LookupError(auth_required)` → `LookupCollection` (§2 above) |

Exhaustive patterns in `docs/design/mvp-tools.md §7`.

---

## 4. Retrieval gate — measuring BM25 quality

```bash
uv run python -m kosmos.eval.retrieval eval/retrieval_queries.yaml
```

Produces:

```
recall@1: 0.70  (pass if ≥ 0.50, secondary)
recall@5: 0.87  (pass if ≥ 0.80 / warn [0.60, 0.80) / fail < 0.60)  ✓ PASS
```

Gate wiring: CI `make eval-retrieval` job posts this as a PR check.

---

## 5. #288 refactor verification

The legacy `address_to_region` and `address_to_grid` tools have been removed. Verify:

```bash
uv run pytest tests/tools/test_legacy_geocoding_removed.py
```

Fails if any call site, registration, or schema reference to the old tool ids exists. **No compatibility shim** — #288 is a hard cutover folded into `resolve_location` + adapter-internal LCC projection.

---

## 6. Success criteria (from spec.md §Success Criteria)

- **SC-001**: Geocoding accuracy ≥ 95% on 40-query set.
- **SC-002**: Retrieval `recall@5` ≥ 80% (gate in §4 above).
- **SC-003**: Pattern D end-to-end fires Layer 3 gate with 0 upstream calls.
- **SC-004**: All `kind` discriminator values match `docs/design/mvp-tools.md §5.4` exactly.
- **SC-005**: `is_personal_data=True ⇒ requires_auth=True` invariant rejects bad registration at startup.

Full 10-criterion table in `spec.md`.

---

## 7. What this does NOT do (scope boundary)

- No identity provider (OAuth / 본인인증 / PASS / 카카오 간편인증). Layer 3 is interface-only.
- No V-World backend for `resolve_location` (tracked in Deferred Items table).
- No vector retrieval (BM25 only unless precision < 60% on eval set).
- No HIRA `MadmDtlInfoService2.7` (11-subop join deferred).
- No NMC `hv1..hv61` real-time bed fields as queryable params (surfaced in responses but not indexed).

Full list: `spec.md § Scope Boundaries & Deferred Items`.
