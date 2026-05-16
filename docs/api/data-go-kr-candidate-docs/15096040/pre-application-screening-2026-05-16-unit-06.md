# Pre-Application Screening: Unit 06

- Dataset: `15096040`
- Title: `충청남도 계룡시_장애인 전동보장구 충전 장소 API`
- Portal URL: `https://www.data.go.kr/data/15096040/openapi.do`
- Provider: `충청남도 계룡시`
- Classification: `사회복지 - 사회복지일반`
- Data format: `JSON`
- Update cadence: `실시간`
- Traffic: `개발계정 10,000 calls`
- Approval type: `개발단계 자동승인 / 운영단계 자동승인`
- Candidate adapter id: `gyeryong_assistive_device_charging_place_locate`
- Candidate primitive: `locate`

## Selection Gate

| Citizen natural-language query | UMMAYA interpretation | API call path | Official fields used | Citizen-facing answer |
| --- | --- | --- | --- | --- |
| `계룡시에 전동휠체어 충전할 수 있는 곳 찾아줘.` | Locate assistive-device charging places in Gyeryong and return official facility facts. | `GET https://apis.data.go.kr/5580000/dspsnElectrAsstnDeviceElctcPlaceService/getdspsnElectrAsstnDeviceElctcPlace?serviceKey=...&currentPage=1&perPage=10` | `INSTL_PLACE`, `INSTL_LC`, `USE_POSBL_TIME`, `INDOOR_OTDR` | List of charging places with building/location, usable hours, and indoor/outdoor status. |
| `실내 전동보장구 충전 장소만 알려줘.` | Filter by indoor/outdoor classification before answering. | Same endpoint with `INDOOR_OTDR=실내`. | `INSTL_PLACE`, `INSTL_LC`, `USE_POSBL_TIME`, `INDOOR_OTDR` | Indoor-only charging places and usable hours. |
| `계룡시청에 전동휠체어 충전기가 있는지 확인해줘.` | Search returned places for a specific facility name. | Same endpoint, then local exact/contains matching on `INSTL_PLACE`. | `INSTL_PLACE`, `INSTL_LC`, `USE_POSBL_TIME` | Whether the facility appears in official data, plus its in-building location and time. |

## Pass/Reject Decision

Pass. This is a direct social-welfare and mobility-infrastructure API. It supports urgent, practical citizen questions about where a wheelchair or electric assistive device can be charged, and its official response fields map cleanly to a `locate` primitive.

Expected use frequency: low to moderate. The geographic scope is local to Gyeryong, but the query type is important for accessibility and mobility support. It is suitable as a regional adapter candidate and may later share an abstraction with other wheelchair-charger APIs.

## Contract Snapshot

- Host/Base: `apis.data.go.kr/5580000/dspsnElectrAsstnDeviceElctcPlaceService`
- Operation: `GET /getdspsnElectrAsstnDeviceElctcPlace`
- Required query params:
  - `serviceKey`: public data portal authentication key
  - `currentPage`: page number
  - `perPage`: number of results per page
- Optional query params:
  - `INDOOR_OTDR`: indoor/outdoor filter, sample `실내`
- Response fields:
  - `resultCode`: result code
  - `resultMsg`: result message
  - `totalRows`: total row count
  - `currentPage`: page number
  - `perPage`: results per page
  - `INSTL_PLACE`: installation place
  - `INSTL_LC`: installation location
  - `USE_POSBL_TIME`: usable hours
  - `INDOOR_OTDR`: indoor/outdoor classification

## Saved Artefacts

- `data-go-kr-detail.html`
- `gateway_swagger_guide.pdf`
- `openapi-schemaorg.json`
- `OpenAPI활용가이드_계룡시_장애인 전동보장구 충전 장소 API_v1.0.docx`
