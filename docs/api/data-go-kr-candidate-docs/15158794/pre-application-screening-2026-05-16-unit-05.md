# Pre-Application Screening: Unit 05

- Dataset: `15158794`
- Title: `대전교통공사_역간 소요시간/거리/요금 조회 서비스`
- Portal URL: `https://www.data.go.kr/data/15158794/openapi.do`
- Provider: `대전교통공사`
- Classification: `교통및물류 - 철도`
- Data format: `XML`
- Update cadence: `실시간`
- Traffic: `개발계정 1,000 calls`
- Approval type: `개발단계 자동승인 / 운영단계 자동승인`
- Candidate adapter id: `djtc_subway_segment_fare_time_check`
- Candidate primitive: `check`

## Selection Gate

| Citizen natural-language query | UMMAYA interpretation | API call path | Official fields used | Citizen-facing answer |
| --- | --- | --- | --- | --- |
| `대전 지하철 대전역에서 시청역까지 얼마나 걸리고 요금은 얼마야?` | Normalize the two station names to Daejeon Metro station numbers, then check segment travel facts. | `GET https://apis.data.go.kr/B554695/TimeDistSVC/getTimeDist01?serviceKey=...&strstnno=...&endstnno=...` | `distfloat`, `fee`, `min`, `sec` | Travel time in minutes/seconds, distance in km, and fare. |
| `대전 1호선 현충원역에서 반석역까지 거리 알려줘.` | Resolve station names to station numbers and query the segment distance. | Same endpoint with resolved station-number params. | `distfloat` | Segment distance in km. |
| `아이랑 대전 지하철 타려는데 목적지까지 비용과 시간을 미리 확인해줘.` | Treat as a transit pre-check before the citizen starts moving. | Same endpoint. | `fee`, `min`, `sec` | Fare and expected in-train segment duration. |

## Pass/Reject Decision

Pass with caveat. This is a direct citizen utility API: citizens often ask about subway travel time, fare, and distance before using transit. The official API has a narrow, deterministic contract and returns the exact fields needed for a `check` primitive.

Caveat: the API parameters are station numbers (`strstnno`, `endstnno`), not station names. The UMMAYA adapter must include or depend on an official Daejeon Metro station-name-to-number resolver before it can answer natural-language station-name queries reliably.

## Contract Snapshot

- Host/Base: `apis.data.go.kr/B554695/TimeDistSVC`
- Operation: `GET /getTimeDist01`
- Required query params:
  - `serviceKey`: public data portal authentication key
  - `strstnno`: starting station number
  - `endstnno`: ending station number
- Response fields:
  - `distfloat`: segment distance in km
  - `fee`: fare
  - `min`: travel time minutes
  - `sec`: travel time seconds

## Saved Artefacts

- `data-go-kr-detail.html`
- `data-go-kr-inline-swagger.json`
- `gateway_swagger_guide.pdf`
- `openapi-schemaorg.json`
