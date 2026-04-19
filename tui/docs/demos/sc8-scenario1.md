# SC-8 Scenario 1 — Route Safety Smoke Run Log

**Date**: 2026-04-19
**Spec**: 287-tui-ink-react-bun SC-8
**Test file**: `tests/integration/test_tui_backend_smoke.py`
**Run command**:
```
uv run pytest tests/integration/test_tui_backend_smoke.py -v --tb=short
```

## Run Output

```
============================= test session starts ==============================
platform darwin -- Python 3.12.11, pytest-9.0.3, pluggy-1.6.0
plugins: asyncio-1.3.0, cov-7.1.0, xdist-3.8.0, ...
asyncio: mode=Mode.AUTO
collected 2 items

tests/integration/test_tui_backend_smoke.py::test_sc8_scenario1_ipc_frame_sequence PASSED  [ 50%]
tests/integration/test_tui_backend_smoke.py::test_sc8_scenario1_fixture_round_trip PASSED  [100%]

============================== 2 passed in 5.00s ===============================
```

## What Was Tested

### test_sc8_scenario1_ipc_frame_sequence

Wires the QueryEngine with a scripted MockLLMClient (6-turn happy path:
resolve_location x2, lookup x4, synthesis) + httpx AsyncMock routing to
KOROAD/KMA/Kakao fixtures. Runs `engine.run("내일 강남구에서 서울역 가는데
날씨랑 사고다발지역 알려줘")` and collects QueryEvents.

Converts QueryEvents to IPC frames (ToolCallFrame, ToolResultFrame,
AssistantChunkFrame) as the stdio bridge would, then asserts:
- At least one ToolCallFrame with name in {lookup, resolve_location}.
- At least one ToolResultFrame.
- At least one AssistantChunkFrame with done=True.
- All frames survive model_dump_json + TypeAdapter.validate_json round-trip.

### test_sc8_scenario1_fixture_round_trip

Standalone fixture sanity check: loads
`tests/fixtures/koroad/accident_hazard_search_happy.json` and asserts the
expected hazard-spot fields (spot_cd, spot_nm, sido_sgg_nm, occrrnc_cnt,
la_crd, lo_crd) are present, and that at least one 강남구 spot is in the
fixture.

## Fixture Sources

- `tests/fixtures/koroad/accident_hazard_search_happy.json` — KOROAD
  `getRestFrequentzoneLg` recorded fixture (강남구 hazard spots).
- `tests/fixtures/kma/forecast_fetch_happy.json` — KMA `getVilageFcst`
  recorded fixture (temperature + precipitation forecast).
- `tests/fixtures/kakao/local_search_address_강남구.json` — Kakao geocoder
  fixture (coords for 강남구).

## Live API Status

No live data.go.kr calls. All HTTP intercepted by AsyncMock.
`KOSMOS_DATA_GO_KR_API_KEY`, `KOSMOS_KAKAO_API_KEY`, `KOSMOS_FRIENDLI_TOKEN`
set to dummy values for env guard bypass.

## IPC Frame Sequence Observed

```
[tool_call]    name=resolve_location  args={"query":"강남구","want":"coords_and_admcd"}
[tool_result]  envelope.kind=resolve_location
[tool_call]    name=resolve_location  args={"query":"서울역","want":"coords_and_admcd"}
[tool_result]  envelope.kind=resolve_location
[tool_call]    name=lookup            args={"mode":"search","query":"사고다발지역 교통사고"}
[tool_result]  envelope.kind=lookup
[tool_call]    name=lookup            args={"mode":"fetch","tool_id":"koroad_accident_hazard_search",...}
[tool_result]  envelope.kind=lookup
[tool_call]    name=lookup            args={"mode":"search","query":"날씨 예보 단기예보"}
[tool_result]  envelope.kind=lookup
[tool_call]    name=lookup            args={"mode":"fetch","tool_id":"kma_forecast_fetch",...}
[tool_result]  envelope.kind=lookup
[assistant_chunk] delta="내일 강남구에서..." done=False
[assistant_chunk] delta="" done=True   ← terminal chunk
```

All 14+ frames passed JSON round-trip validation.

## Notes

- No real TUI process spawned (Bun/Ink not required for this test tier).
- The IPC frame construction mirrors what `kosmos/ipc/stdio.py` would
  produce when wired to the real QueryEngine.
- Subprocess-based IPC soak test (FR-010 / SC-2 100+ ev/s) is out of scope
  for this smoke task.
