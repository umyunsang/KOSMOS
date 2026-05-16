# Usage Notes: Unit 06

- Dataset: `15096040`
- Title: `충청남도 계룡시_장애인 전동보장구 충전 장소 API`
- Portal URL: `https://www.data.go.kr/data/15096040/openapi.do`
- Provider: `충청남도 계룡시`
- Classification: `사회복지 - 사회복지일반`
- Candidate adapter id: `gyeryong_assistive_device_charging_place_locate`
- Candidate primitive: `locate`
- Application status: approved
- Application evidence: data.go.kr My Page showed `[승인] 충청남도 계룡시_장애인 전동보장구 충전 장소 API`, application date `2026-05-16`, expiry `2028-05-16`, application ref `115975296`.

## Why This Fits UMMAYA

This API supports accessibility and mobility-infrastructure queries. A citizen can ask where to charge an electric wheelchair or other assistive device, and UMMAYA can return official installation place, in-building location, usable hours, and indoor/outdoor status.

Expected query examples:

- `계룡시에 전동휠체어 충전할 수 있는 곳 찾아줘.`
- `실내 전동보장구 충전 장소만 알려줘.`
- `계룡시청에 전동휠체어 충전기가 있는지 확인해줘.`

Expected use frequency: low to moderate. The API is local to Gyeryong, but the need is practical and high-value for mobility support. It is useful as a regional `locate` adapter and can share a common output shape with other wheelchair-charging APIs.

## API Contract

- Base URL: `https://apis.data.go.kr/5580000/dspsnElectrAsstnDeviceElctcPlaceService`
- Operation: `GET /getdspsnElectrAsstnDeviceElctcPlace`
- Full endpoint: `https://apis.data.go.kr/5580000/dspsnElectrAsstnDeviceElctcPlaceService/getdspsnElectrAsstnDeviceElctcPlace`
- Produces: `application/json`

Required query parameters:

- `serviceKey`: public data portal authentication key
- `currentPage`: page number
- `perPage`: number of results per page

Optional query parameters:

- `INDOOR_OTDR`: indoor/outdoor filter, sample `실내`

Response fields:

- `resultCode`: result code
- `resultMsg`: result message
- `totalRows`: total row count
- `currentPage`: page number
- `perPage`: results per page
- `INSTL_PLACE`: installation place
- `INSTL_LC`: installation location
- `USE_POSBL_TIME`: usable hours
- `INDOOR_OTDR`: indoor/outdoor classification

## Wrapping Plan

The adapter should expose a Korean-first `locate` tool:

- Input: `area_name`, optional `indoor_outdoor`, optional `facility_name`.
- API call: map pagination to `currentPage` and `perPage`; map indoor/outdoor intent to `INDOOR_OTDR` when present.
- Output: structured charging-place records with installation place, exact location, usable hours, indoor/outdoor status, official source citation, and credential state.
- Local post-filter: match `facility_name` against `INSTL_PLACE` for questions about a specific building such as `계룡시청`.

Important caveat: the official data has facility-level locations, not geocoded coordinates. If a citizen asks for “near me,” the adapter needs a separate geocoder or a broader wheelchair-charger dataset before it can rank by distance.

## Saved Artefacts

- `data-go-kr-detail.html`
- `gateway_swagger_guide.pdf`
- `openapi-schemaorg.json`
- `OpenAPI활용가이드_계룡시_장애인 전동보장구 충전 장소 API_v1.0.docx`
- `pre-application-screening-2026-05-16-unit-06.md`
