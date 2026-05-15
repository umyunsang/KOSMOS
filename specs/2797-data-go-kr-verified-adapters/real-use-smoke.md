# Real Terminal Verification: data.go.kr Verified Adapter Wave

Date: 2026-05-16 KST
Mode: `UMMAYA_LIVE_ADAPTER_MODE=direct`
Entrypoint smoke: `uv run ummaya --version` returned `ummaya 0.1.9`.

Secrets were loaded from local `.env` and were not printed. Required env vars
were present:

- `UMMAYA_DATA_GO_KR_API_KEY`
- `UMMAYA_KEPCO_POWER_DATA_API_KEY`
- `UMMAYA_REB_REAL_ESTATE_STATS_API_KEY`

## Direct Adapter Calls

All fourteen read-only live adapters were invoked through `ToolExecutor.invoke()`
after `register_all_tools()` populated the UMMAYA registry.

| tool_id | Result |
|---|---|
| `fsc_corporate_finance_summary` | `collection`, `items=1`, `total_count=2` |
| `airkorea_ctprvn_air_quality` | `collection`, `items=5`, `total_count=40` |
| `ftc_large_group_status` | `collection`, `items=10`, `total_count=71` |
| `ftc_public_ym_list` | `collection`, `items=1`, `total_count=1` |
| `tago_bus_route_search` | `collection`, `items=10`, `total_count=17` |
| `tago_bus_arrival_search` | `collection`, `items=0`, `total_count=0` |
| `tago_bus_location_search` | `collection`, `items=0`, `total_count=0` |
| `tago_bus_station_search` | `collection`, `items=1`, `total_count=1` |
| `kepco_contract_power_usage` | `collection`, `items=1`, `total_count=1` |
| `pps_bid_public_info` | `collection`, `items=1`, `total_count=1` |
| `reb_real_estate_stat_table` | `collection`, `items=5`, `total_count=738` |
| `bfc_funeral_area_fee` | `collection`, `items=4`, `total_count=4` |
| `kcue_finance_regional_tuition` | `collection`, `items=5`, `total_count=20` |
| `kcue_student_regional_foreign` | `collection`, `items=5`, `total_count=20` |

The two TAGO zero-result calls matched the live-probe evidence shape and are
normal successful empty collections, not errors.

## Interactive `ummaya` Terminal Run

Command:

```bash
UMMAYA_LIVE_ADAPTER_MODE=direct UMMAYA_K_EXAONE_THINKING=false uv run ummaya
```

Prompt typed into the live terminal:

```text
부산광역시 장례식장 시설 사용료 목록을 공공 API 도구로 조회해서 알려줘.
```

Final clean run result:

- UMMAYA booted into the interactive REPL and accepted the prompt from the terminal.
- The LLM selected the public-data primitive path and emitted a single tool call.
- The visible terminal tool panel rendered `도구 결과` with `성공  tool_id='find'`.
- The selected adapter was `bfc_funeral_area_fee`.
- The final answer was grounded in the observed tool result and listed four returned fee rows:
  `부산, 울산 및 경남`, `그 외 지역`, `지역 주민 (남산동, 청룡노포동, 선두구동)`,
  and `국가보훈기본법에 따른 희생·공헌자`.
- No `도구 오류`, traceback, schema mismatch, fabricated fallback, or retry prompt appeared.

Observed abnormal flows during the real terminal run and fixes applied before
the final clean run:

| Observed terminal failure | Root cause | Fix |
|---|---|---|
| FriendliAI HTTP 422 rejected `function.trigger_phrase`. | Raw registry tool dicts carried UMMAYA-only metadata into the provider payload. | Normalize every raw tool dict through `ToolDefinition.model_validate(...).model_dump()` before sending. |
| `find` / `locate` root primitive calls failed with `No adapter registered for tool`. | The Rich REPL path dispatched root primitive names directly instead of fanning out to the selected adapter id. | Add root primitive fan-out in `dispatch_tool_calls()` using the primitive input schema, then invoke the selected adapter. |
| Tool-result follow-up crashed with `Object of type datetime is not JSON serializable`. | Primitive facade output used Python-mode Pydantic dumps, leaving `datetime` values in `ToolResult.data`. | Dump primitive facade outputs with `model_dump(mode="json")`, matching IPC/session wire patterns. |
| The model called `locate` before a location-independent public-data `find` request. | Rich REPL exposed all root primitives even after BM25 selected a `find` adapter whose schema did not need coordinates or admin codes. | Add dynamic adapter context and a per-turn provider tool allow-list so this request exposes only `find`. |

## Primitive Path

The LLM-facing primitive path was exercised through `lookup()`:

1. `find(mode="search", query="부산 장례식장 시설사용료", top_k=5)` returned
   `bfc_funeral_area_fee` as the top candidate.
2. `find(mode="fetch", tool_id="bfc_funeral_area_fee", params={...})` returned
   `LookupCollection(source="bfc_funeral_area_fee", items=4, total_count=4)`.

No adapter returned `LookupError`, no schema normalization error occurred, and
no permission gate blocked the read-only flows.
