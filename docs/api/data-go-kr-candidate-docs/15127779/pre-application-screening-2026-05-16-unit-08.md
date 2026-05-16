# Unit 08 Pre-Application Screening

- Dataset ID: `15127779`
- Title: `해양수산부_실시간 해양수질자동측정망 관측소 측정자료정보`
- Source: <https://www.data.go.kr/data/15127779/openapi.do>
- Provider: `해양수산부`
- Classification: `환경 - 해양환경`
- Format / type: REST, XML
- Approval: development auto-approval, operation auto-approval
- Development traffic: `10,000`
- Update cycle: realtime
- Candidate adapter ID: `mof_ocean_water_quality_check`
- Candidate primitive: `check`

## Selection Logic

This is a good UMMAYA candidate because it maps natural citizen questions about coastal water quality to official, realtime Ministry of Oceans and Fisheries measurements rather than general weather or static environmental summaries.

| Citizen natural-language query | UMMAYA interpretation | API use | Citizen-facing answer |
| --- | --- | --- | --- |
| `부산 수영 쪽 바닷물 수질 괜찮아?` | Check a named marine water-quality station. | Map `부산수영` to `SEA3003`, call the realtime measurement endpoint, summarize pH, turbidity, dissolved oxygen, salinity, and water temperature. | "부산수영 정점의 최근 측정값은 pH X, 탁도 Y, 용존산소 Z입니다." |
| `울산 온산 앞바다 용존산소 낮아?` | Check a risk-sensitive metric at a specific station. | Map `울산온산` to `SEA7001`, request recent rows and compare `rtmWqDoxn`. | Report latest dissolved oxygen with timestamp and caution that the API provides measurements, not medical or disaster advice. |
| `마산 봉암 수질 최근 며칠 변화 보여줘` | Check station time range. | Use `rtm_wq_wtch_sta_cd=SEA2005`, `wtch_dt_start`, `wtch_dt_end`, `pageNo`, and `numOfRows`. | Return a compact trend for temperature, pH, turbidity, and dissolved oxygen. |
| `낚시 가기 전에 광양만 수질 좀 확인해줘` | Check nearby known marine station before an outdoor activity. | Map `광양망덕/초남/적량` to `SEA5001/SEA5002/SEA5003` and fetch current measurements. | Summarize whether recent measured values look normal and cite MOF as the source. |

## Fit Assessment

- UMMAYA domain fit: high for coastal environment, fishery, marine leisure, and local safety-adjacent queries.
- Primitive fit: `check` is primary; `locate` can be layered later by resolving a coastal place to the nearest known station code.
- Expected usage: low to medium in normal periods, higher during algae blooms, heat waves, heavy rain, coastal tourism season, or fishery incidents.
- Wrapping value: the raw API requires station codes and field-name knowledge; an adapter can hide the station-code lookup and produce a plain-language water-quality summary.

## Official Contract Evidence

- Base URL: `https://apis.data.go.kr/1192000/OceansWemoObvpRtmInfoService`
- Operation: `GET /OceansWemoObvpRtmInfo`
- Required parameters: `serviceKey`, `_type`, `numOfRows`, `pageNo`
- Optional parameters: `rtm_wq_wtch_sta_cd`, `wtch_dt_start`, `wtch_dt_end`
- Note: portal Swagger renders the station-code parameter as `rtm_wq_wtch_sta_cd ` with a trailing space, while the downloaded XLSX reference document lists `rtm_wq_wtch_sta_cd` without the trailing space. Treat the XLSX spelling as the adapter-facing normalized parameter name and preserve this caveat in implementation notes.
- Reference document: `실시간_해양수질자동측정망_정점정보_API문서.xlsx`

## Station Seed Values From Reference Document

`SEA1002` 시화조력, `SEA1005` 시화반월, `SEA1006` 인천송도, `SEA1007` 인천강화, `SEA2004` 마산삼귀, `SEA2005` 마산봉암, `SEA2006` 마산양덕, `SEA2007` 마산월영, `SEA3003` 부산수영, `SEA5001` 광양망덕, `SEA5002` 광양초남, `SEA5003` 광양적량, `SEA7001` 울산온산.
