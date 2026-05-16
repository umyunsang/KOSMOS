# Pre-Application Screening: Unit 07

- Dataset: `15000652`
- Title: `국립중앙의료원_전국 자동심장충격기(AED) 정보 조회 서비스`
- Portal URL: `https://www.data.go.kr/data/15000652/openapi.do`
- Provider: `국립중앙의료원`
- Classification: `보건 - 보건의료`
- Data format: `XML`
- Update cadence: `실시간`
- Traffic: `개발계정 1,000 calls per detailed function`
- Approval type: `개발단계 자동승인 / 운영단계 자동승인`
- Candidate adapter id: `nmc_aed_site_locate`
- Candidate primitive: `locate`

## Selection Gate

| Citizen natural-language query | UMMAYA interpretation | API call path | Official fields used | Citizen-facing answer |
| --- | --- | --- | --- | --- |
| `지금 내 근처 자동심장충격기 어디 있어?` | Resolve the citizen's place or coordinates, then locate nearby AED records from the national NMC source. | `GET https://apis.data.go.kr/B552657/AEDInfoInqireService/getAedLcinfoInqire?serviceKey=...&WGS84_LON=127.085156592737&WGS84_LAT=37.4881325624879&pageNo=1&numOfRows=10` | `org`, `buildAddress`, `buildPlace`, `wgs84Lat`, `wgs84Lon`, weekday/holiday usable time fields | Nearby AED locations with facility name, address, in-building placement, coordinates, and availability-time hints. |
| `종로구 자동제세동기 위치 알려줘.` | Resolve area to official city/district terms and query by address fields. | `GET https://apis.data.go.kr/B552657/AEDInfoInqireService/getEgytAedManageInfoInqire?serviceKey=...&Q0=서울특별시&Q1=종로구&pageNo=1&numOfRows=10` | `org`, `buildAddress`, `buildPlace`, `managerTel`, `clerkTel`, `wgs84Lat`, `wgs84Lon` | District-level AED list with official facility/address/contact fields. |
| `AED 전체 데이터를 받아서 사전 색인을 만들 수 있어?` | Use the full download endpoint for a fixture/cache builder, not for every citizen query. | `GET https://apis.data.go.kr/B552657/AEDInfoInqireService/getAedFullDown?serviceKey=...&pageNo=1&numOfRows=100` | `serialSeq`, `sido`, `gugun`, `org`, `buildAddress`, `buildPlace`, `wgs84Lat`, `wgs84Lon`, weekly availability fields | A local searchable index that can answer follow-up location queries faster while citing NMC. |

## Pass/Reject Decision

Pass. This is a national emergency-location API with direct civic value. It covers a frequent and safety-critical natural-language query class: finding an AED near a citizen's current location or in a named district. The endpoint exposes official coordinates, facility names, address fields, placement descriptions, contacts, and opening-time fields, which map cleanly to a `locate` adapter.

Expected use frequency: moderate. AED searches are not daily for every citizen, but the query has high urgency and broad national coverage. The API is more valuable than a local AED dataset because it can support national lookup, local indexing, and location-based ranking through the same adapter.

Important caveat: the application page warns that services using location information may require location-service permission/reporting under Korean location-information law when used as a business service. UMMAYA should record this as an implementation/compliance caveat and expose the official portal warning in adapter documentation.

## Contract Snapshot

- Host/Base: `apis.data.go.kr/B552657/AEDInfoInqireService`
- Operation 1: `GET /getEgytAedManageInfoInqire`
  - Required params: `serviceKey`, `Q0`, `Q1`
  - Optional params: `pageNo`, `numOfRows`
  - Description: query AED management records by `Q0` city/province and `Q1` district/county.
- Operation 2: `GET /getAedLcinfoInqire`
  - Required params: `serviceKey`, `WGS84_LON`, `WGS84_LAT`
  - Optional params: `pageNo`, `numOfRows`, `Q0`, `Q1`
  - Description: query AED location records around WGS84 coordinates, with optional area codes.
- Operation 3: `GET /getAedFullDown`
  - Required params: `serviceKey`
  - Optional params: `pageNo`, `numOfRows`
  - Description: full AED data download for indexing or fixture-building.
- Response fields include: `serialSeq`, `sido`, `gugun`, `org`, `buildAddress`, `buildPlace`, `clerkTel`, `manager`, `managerTel`, `mfg`, `model`, `wgs84Lat`, `wgs84Lon`, `zipcode1`, `zipcode2`, weekday/holiday start/end time fields, and Sunday week availability flags.

## Saved Artefacts

- `data-go-kr-detail.html`
- `gateway_swagger_guide.pdf`
- `openapi-schemaorg.json`
- `NIA-IFT-OpenAPI활용가이드-01.국립중앙의료원-자동심장충격기정보조회서비스(AED).hwp`
- `NIA-IFT-OpenAPI활용가이드-01.국립중앙의료원-자동심장충격기정보조회서비스(AED).hwp.html`
- `NIA-IFT-OpenAPI활용가이드-01.국립중앙의료원-자동심장충격기정보조회서비스(AED).hwp.txt`
- `NIA-IFT-OpenAPI활용가이드-01.국립중앙의료원-자동심장충격기정보조회서비스(AED).hwp.normalized.txt`
