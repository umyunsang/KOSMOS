# Usage Notes: Unit 05

- Dataset: `15158794`
- Title: `대전교통공사_역간 소요시간/거리/요금 조회 서비스`
- Portal URL: `https://www.data.go.kr/data/15158794/openapi.do`
- Provider: `대전교통공사`
- Classification: `교통및물류 - 철도`
- Candidate adapter id: `djtc_subway_segment_fare_time_check`
- Candidate primitive: `check`
- Application status: approved
- Application evidence: data.go.kr My Page showed `[승인] 대전교통공사_역간 소요시간/거리/요금 조회 서비스`, application date `2026-05-16`, expiry `2028-05-16`, application ref `115974597`.

## Why This Fits UMMAYA

This API is useful for direct citizen transit planning queries. It turns a common natural-language question into deterministic official facts: distance, fare, and travel time between two Daejeon Metro stations.

Expected query examples:

- `대전 지하철 대전역에서 시청역까지 얼마나 걸리고 요금은 얼마야?`
- `현충원역에서 반석역까지 지하철 거리 알려줘.`
- `아이랑 대전 지하철 타기 전에 목적지까지 비용과 시간을 확인해줘.`

Expected use frequency: moderate. It is local to Daejeon Metro Line 1, so it is not a nationwide high-volume primitive, but the query type is common and directly citizen-facing. It is a good regional `check` adapter candidate.

## API Contract

- Base URL: `https://apis.data.go.kr/B554695/TimeDistSVC`
- Operation: `GET /getTimeDist01`
- Full endpoint: `https://apis.data.go.kr/B554695/TimeDistSVC/getTimeDist01`
- Produces: `application/xml`

Required query parameters:

- `serviceKey`: public data portal authentication key
- `strstnno`: starting station number
- `endstnno`: ending station number

Response fields:

- `header.resultCode`: result code
- `header.resultMsg`: result message
- `body.items.item.distfloat`: segment distance in km
- `body.items.item.fee`: fare
- `body.items.item.min`: travel time minutes
- `body.items.item.sec`: travel time seconds

## Wrapping Plan

The adapter should expose a Korean-first `check` tool that accepts station names, not station numbers:

- Input: `origin_station_name`, `destination_station_name`
- Internal normalization: resolve Daejeon Metro station names to official station numbers before calling the API.
- API call: map normalized station numbers to `strstnno` and `endstnno`.
- Output: `distance_km`, `fare_krw`, `duration_minutes`, `duration_seconds`, plus official source citation and expiry/credential state.

Important caveat: the official API itself only accepts station numbers. The adapter must use an official station-name-to-number resolver or maintained station-code fixture before claiming natural-language station-name support.

## Saved Artefacts

- `data-go-kr-detail.html`
- `data-go-kr-inline-swagger.json`
- `gateway_swagger_guide.pdf`
- `openapi-schemaorg.json`
- `pre-application-screening-2026-05-16-unit-05.md`
