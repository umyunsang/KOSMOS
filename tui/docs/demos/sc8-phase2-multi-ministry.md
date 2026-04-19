# SC-8 Phase 2 Multi-Ministry Scenario — Smoke Run Log

**Date**: 2026-04-19
**Spec**: 287-tui-ink-react-bun SC-8 (Phase 2 multi-ministry)
**Test file**: `tests/integration/test_tui_multi_ministry_smoke.py`
**Run command**:
```
uv run pytest tests/integration/test_tui_multi_ministry_smoke.py -v --tb=short
```

## Run Output

```
============================= test session starts ==============================
platform darwin -- Python 3.12.11, pytest-9.0.3, pluggy-1.6.0
plugins: asyncio-1.3.0, cov-7.1.0, xdist-3.8.0, ...
asyncio: mode=Mode.AUTO
collected 1 item

tests/integration/test_tui_multi_ministry_smoke.py::test_sc8_phase2_multi_ministry_ipc_frame_sequence PASSED

============================== 1 passed in 4.26s ===============================
```

## What Was Tested

### test_sc8_phase2_multi_ministry_ipc_frame_sequence

Citizen query: `"강남구 사고 위험지역이랑 근처 병원도 알려줘"`

Wires QueryEngine with scripted MockLLMClient (5-turn + synthesis):
- Turn 1: resolve_location(강남구)   — Kakao geocoder fixture
- Turn 2: lookup(search, KOROAD)    — BM25 index search
- Turn 3: lookup(fetch, koroad_accident_hazard_search) — KOROAD fixture
- Turn 4: lookup(search, HIRA)      — BM25 index search
- Turn 5: lookup(fetch, hira_hospital_search) — HIRA fixture
- Turn 6: synthesis (Korean text, done)

httpx AsyncMock routes:
- `getRestFrequentzoneLg` → `tests/fixtures/koroad/accident_hazard_search_happy.json`
- `getHospBasisList`      → `tests/fixtures/hira/hospital_search_happy.json`
- Kakao                   → `tests/fixtures/kakao/local_search_address_강남구.json`

Asserts verified:
- resolve_location precedes all lookup calls in tool_call_order.
- ≥4 lookup calls (2 search + 2 fetch, one per ministry).
- stop_reason is end_turn.
- final_response is non-empty Korean text.
- Korean text mentions KOROAD content (강남구/개포동/삼성동/사고).
- Korean text mentions HIRA content (병원/강남세브란스/강남구).
- IPC message_order ends with AssistantChunkFrame(done=True).
- All ToolCallFrame.name values are 5-primitive names.
- All IPC frames survive JSON round-trip.

## Tool Call Order (verified)

```
resolve_location → lookup → lookup → lookup → lookup
```

Position detail:
```
[0] resolve_location  (강남구 geocoding)
[1] lookup            (search: KOROAD BM25)
[2] lookup            (fetch: koroad_accident_hazard_search)
[3] lookup            (search: HIRA BM25)
[4] lookup            (fetch: hira_hospital_search)
```

## IPC Frame Sequence Observed

```
[tool_call]    name=resolve_location  args={"query":"강남구","want":"coords_and_admcd"}
[tool_result]  envelope.kind=resolve_location
[tool_call]    name=lookup            args={"mode":"search","query":"사고다발지역 교통사고"}
[tool_result]  envelope.kind=lookup
[tool_call]    name=lookup            args={"mode":"fetch","tool_id":"koroad_accident_hazard_search",...}
[tool_result]  envelope.kind=lookup
[tool_call]    name=lookup            args={"mode":"search","query":"병원 응급실 근처"}
[tool_result]  envelope.kind=lookup
[tool_call]    name=lookup            args={"mode":"fetch","tool_id":"hira_hospital_search",...}
[tool_result]  envelope.kind=lookup
[assistant_chunk] delta="강남구 안전 정보입니다..." done=False
[assistant_chunk] delta="" done=True   ← terminal chunk
```

All frames passed JSON round-trip validation.

## Fixture Sources

- `tests/fixtures/koroad/accident_hazard_search_happy.json` — KOROAD fixture
  (강남구 개포동/삼성동 hazard spots).
- `tests/fixtures/hira/hospital_search_happy.json` — HIRA fixture
  (서울대학교병원, 보라매병원, 강남세브란스병원).
- `tests/fixtures/kakao/local_search_address_강남구.json` — Kakao geocoder
  fixture (강남구 WGS84 coords).

## Ministries Covered

| Ministry | Adapter | Data |
|----------|---------|------|
| KOROAD (도로교통공단) | `koroad_accident_hazard_search` | 교통사고 위험지점 |
| HIRA (건강보험심사평가원) | `hira_hospital_search` | 근처 병원 목록 |

## Live API Status

No live data.go.kr calls. All HTTP intercepted by extended AsyncMock
(`_build_multi_ministry_httpx_mock`).

## Notes

- HIRA `register()` is called on top of the base e2e registry so the BM25
  index includes `hira_hospital_search`.
- No Bun/Ink process spawned — this is a Python-layer IPC smoke.
- Full TUI rendering of HIRA `LookupCollection` results requires the
  `<HospitalCard />` component (FR-027, Spec 287 Sub-Epic C).
