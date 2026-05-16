# Usage Notes: Unit 08

- Dataset: `15127779`
- Title: `해양수산부_실시간 해양수질자동측정망 관측소 측정자료정보`
- Portal URL: `https://www.data.go.kr/data/15127779/openapi.do`
- Provider: `해양수산부`
- Classification: `환경 - 해양환경`
- Candidate adapter id: `mof_ocean_water_quality_check`
- Candidate primitive: `check`
- Application status: approved
- Application evidence: data.go.kr My Page showed `[승인] 해양수산부_실시간 해양수질자동측정망 관측소 측정자료정보`, application date `2026-05-16`, expiry `2028-05-16`, application ref `115976412`.

## Why This Fits UMMAYA

This API supports citizen-facing checks for marine water quality conditions at official coastal monitoring stations. A citizen can ask whether a bay or harbor area has current water-quality issues, compare nearby station readings, or ask UMMAYA to explain salinity, dissolved oxygen, pH, turbidity, and chlorophyll readings from an official source.

Expected query examples:

- `마산만 해양 수질 지금 괜찮아?`
- `부산 수영 쪽 바닷물 pH랑 용존산소 최근 값 알려줘.`
- `광양만 실시간 해양수질 관측값을 날짜 범위로 확인해줘.`

Expected use frequency: moderate. Marine water quality is not a daily universal query, but it is high-value for coastal residents, fishery workers, marine leisure users, local environment monitoring, and disaster/environment watch workflows. It also fills an infrastructure gap that weather-only adapters cannot cover because the response contains station-level chemical and physical water-quality measurements.

Selection logic: this fits UMMAYA's `check` primitive because the user intent is a status/condition check, not a document lookup or form submission. The adapter can translate natural-language place names into known station codes, call the official endpoint with a station code and time range, then summarize the official measurements with source citation and units.

Compliance caveat: the portal application page warns that services using location information may require location-service permission/reporting under Korean law when operated as a business service. This adapter should avoid silently collecting GPS; when UMMAYA later resolves nearest stations from user location, the adapter documentation should preserve this warning and route through explicit permission UX.

## API Contract

- Base URL: `https://apis.data.go.kr/1192000/OceansWemoObvpRtmInfoService`
- Produces: `application/xml`

### Operation: `GET /OceansWemoObvpRtmInfo`

- Full endpoint: `https://apis.data.go.kr/1192000/OceansWemoObvpRtmInfoService/OceansWemoObvpRtmInfo`
- Purpose: query realtime marine water-quality monitoring station measurements.

Required query parameters:

- `serviceKey`: public data portal authentication key
- `_type`: response document type, sample `xml`
- `numOfRows`: result count, sample `10`
- `pageNo`: page number, sample `1`

Optional query parameters:

- `rtm_wq_wtch_sta_cd`: realtime water-quality monitoring station code, sample `SEA2006`
- `wtch_dt_start`: measurement start datetime/date
- `wtch_dt_end`: measurement end datetime/date

Parameter caveat: the portal inline Swagger renders the station parameter as `rtm_wq_wtch_sta_cd ` with a trailing space, while the downloaded XLSX specification lists `rtm_wq_wtch_sta_cd` without the trailing space. The adapter-facing schema should use the normalized XLSX spelling and record the portal mismatch in tests/fixtures.

Response fields:

- `resultCode`: result code
- `resultMsg`: result message
- `items.item.num`: row number
- `items.item.rtmWqWtchStaCd`: realtime water-quality monitoring station code
- `items.item.rtmWqWtchDtlDt`: measurement detail datetime
- `items.item.rtmWtchWtem`: water temperature
- `items.item.rtmWqCndctv`: conductivity
- `items.item.ph`: pH
- `items.item.rtmWqDoxn`: dissolved oxygen
- `items.item.rtmWqTu`: turbidity
- `items.item.rtmWqBgalgsQy`: blue-green algae quantity
- `items.item.rtmWqChpla`: chlorophyll-a
- `items.item.rtmWqSlnty`: salinity
- `numOfRows`: result count
- `pageNo`: page number
- `totalCount`: total result count

Seed station codes from the downloaded XLSX:

- `SEA1002`: 시화조력
- `SEA1005`: 시화반월
- `SEA1006`: 인천송도
- `SEA1007`: 인천강화
- `SEA2004`: 마산삼귀
- `SEA2005`: 마산봉암
- `SEA2006`: 마산양덕
- `SEA2007`: 마산월영
- `SEA3003`: 부산수영
- `SEA5001`: 광양망덕
- `SEA5002`: 광양초남
- `SEA5003`: 광양적량
- `SEA7001`: 울산온산

## Wrapping Plan

The adapter should expose a Korean-first `check` tool:

- Input: `station_code` or `place_query`, optional `start_datetime`, `end_datetime`, optional `limit`.
- Location resolution: map common coastal place names and station names to `rtm_wq_wtch_sta_cd`; if only a broad area is supplied, return candidate stations for user confirmation or use deterministic nearest-station lookup from a maintained station table.
- API call: call `/OceansWemoObvpRtmInfo` with `serviceKey`, `_type=xml`, `numOfRows`, `pageNo`, and station/time-range filters when available.
- Output: official station code, measurement time, water temperature, conductivity, pH, dissolved oxygen, turbidity, algae quantity, chlorophyll-a, salinity, source citation, and a short explanation that these are monitoring readings rather than health/safety certification.
- Error handling: fail closed when the station code is unknown, the date range is invalid, or the API returns no measurements.

## Saved Artefacts

- `data-go-kr-detail.html`
- `gateway_swagger_guide.pdf`
- `openapi-schemaorg.json`
- `data-go-kr-inline-swagger.json`
- `실시간_해양수질자동측정망_정점정보_API문서.xlsx`
- `실시간_해양수질자동측정망_정점정보_API문서.xlsx.txt`
- `pre-application-screening-2026-05-16-unit-08.md`
