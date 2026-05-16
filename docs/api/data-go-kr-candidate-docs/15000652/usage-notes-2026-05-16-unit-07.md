# Usage Notes: Unit 07

- Dataset: `15000652`
- Title: `국립중앙의료원_전국 자동심장충격기(AED) 정보 조회 서비스`
- Portal URL: `https://www.data.go.kr/data/15000652/openapi.do`
- Provider: `국립중앙의료원`
- Classification: `보건 - 보건의료`
- Candidate adapter id: `nmc_aed_site_locate`
- Candidate primitive: `locate`
- Application status: approved
- Application evidence: data.go.kr My Page showed `[승인] 국립중앙의료원_전국 자동심장충격기(AED) 정보 조회 서비스`, application date `2026-05-16`, expiry `2028-05-16`, application ref `115975807`.

## Why This Fits UMMAYA

This API supports emergency public-infrastructure lookup. A citizen can ask where the nearest AED is, ask for AEDs in a named district, or allow UMMAYA to build an official AED index for fast lookup. It fits the `locate` primitive because the official response includes facility name, address, placement, coordinates, contact fields, and availability-time fields.

Expected query examples:

- `지금 내 근처 자동심장충격기 어디 있어?`
- `종로구 자동제세동기 위치 알려줘.`
- `경희의료원 근처 AED 위치랑 몇 층에 있는지 알려줘.`

Expected use frequency: moderate. The query is urgent and high-value, with national coverage and practical emergency relevance. It should be prioritized over local-only AED datasets because one adapter can cover national address lookup, coordinate lookup, and full-data indexing.

Compliance caveat: the portal application page warns that services using location information may require location-service permission/reporting under Korean law when operated as a business service. UMMAYA should preserve that warning in adapter docs and distinguish research/demo use from deployed location-based service operation.

## API Contract

- Base URL: `https://apis.data.go.kr/B552657/AEDInfoInqireService`
- Produces: `application/xml`

### Operation: `GET /getEgytAedManageInfoInqire`

- Full endpoint: `https://apis.data.go.kr/B552657/AEDInfoInqireService/getEgytAedManageInfoInqire`
- Purpose: query AED management records by city/province and district/county.

Required query parameters:

- `serviceKey`: public data portal authentication key
- `Q0`: address city/province, sample `서울특별시`
- `Q1`: address district/county, sample `종로구`

Optional query parameters:

- `pageNo`: page number, sample `1`
- `numOfRows`: result count, sample `10`

### Operation: `GET /getAedLcinfoInqire`

- Full endpoint: `https://apis.data.go.kr/B552657/AEDInfoInqireService/getAedLcinfoInqire`
- Purpose: query AED locations around a WGS84 coordinate.

Required query parameters:

- `serviceKey`: public data portal authentication key
- `WGS84_LON`: longitude, sample `127.085156592737`
- `WGS84_LAT`: latitude, sample `37.4881325624879`

Optional query parameters:

- `pageNo`: page number, sample `1`
- `numOfRows`: result count, sample `10`
- `Q0`: city/province code, sample `11`
- `Q1`: district/county code, sample `1101`

### Operation: `GET /getAedFullDown`

- Full endpoint: `https://apis.data.go.kr/B552657/AEDInfoInqireService/getAedFullDown`
- Purpose: download full AED records for indexing, fixture-building, or cache refresh.

Required query parameters:

- `serviceKey`: public data portal authentication key

Optional query parameters:

- `pageNo`: page number
- `numOfRows`: result count

Response fields:

- `resultCode`: result code
- `resultMsg`: result message
- `totalCount`: total result count
- `pageNo`: page number
- `numOfRows`: result count
- `serialSeq`: AED serial sequence
- `sido`: city/province
- `gugun`: district/county
- `org`: facility or organization name
- `buildAddress`: address
- `buildPlace`: in-building AED placement
- `clerkTel`: clerk/contact phone
- `manager`: manager name, masked in examples
- `managerTel`: manager phone
- `mfg`: manufacturer
- `model`: AED model
- `wgs84Lat`: latitude
- `wgs84Lon`: longitude
- `zipcode1`, `zipcode2`: postal code parts
- `monSttTme`, `monEndTme`, `tueSttTme`, `tueEndTme`, `wedSttTme`, `wedEndTme`, `thuSttTme`, `thuEndTme`, `friSttTme`, `friEndTme`, `satSttTme`, `satEndTme`, `sunSttTme`, `sunEndTme`, `holSttTme`, `holEndTme`: weekly and holiday usable time fields
- `sunFrtYon`, `sunScdYon`, `sunThiYon`, `sunFurYon`, `sunFifYon`: Sunday week availability flags

## Wrapping Plan

The adapter should expose a Korean-first `locate` tool:

- Input: `place_query` or `lat/lon`, optional `sido`, `gugun`, optional `facility_name`, optional `use_full_index`.
- API call: use `getAedLcinfoInqire` when coordinates are available; otherwise map the resolved administrative area to `Q0`/`Q1` and call `getEgytAedManageInfoInqire`.
- Indexing mode: use `getAedFullDown` only for periodic cache/fixture generation, not per citizen request.
- Output: official AED records with facility name, address, placement, coordinates, contact fields, usable-time summary, source citation, and location-law caveat.
- Ranking: when coordinates are provided, rank by returned distance if available or compute distance from `wgs84Lat`/`wgs84Lon` locally.

## Saved Artefacts

- `data-go-kr-detail.html`
- `gateway_swagger_guide.pdf`
- `openapi-schemaorg.json`
- `NIA-IFT-OpenAPI활용가이드-01.국립중앙의료원-자동심장충격기정보조회서비스(AED).hwp`
- `NIA-IFT-OpenAPI활용가이드-01.국립중앙의료원-자동심장충격기정보조회서비스(AED).hwp.html`
- `NIA-IFT-OpenAPI활용가이드-01.국립중앙의료원-자동심장충격기정보조회서비스(AED).hwp.txt`
- `NIA-IFT-OpenAPI활용가이드-01.국립중앙의료원-자동심장충격기정보조회서비스(AED).hwp.normalized.txt`
- `pre-application-screening-2026-05-16-unit-07.md`
