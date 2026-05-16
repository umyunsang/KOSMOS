# 행정안전부_안전비상벨위치정보 조회서비스

- Unit: `04`
- Source: <https://www.data.go.kr/data/15155046/openapi.do>
- data.go.kr ID: `15155046`
- Provider: 행정안전부
- Category: 공공질서및안전 - 안전관리
- Discovery path: data.go.kr main category navigation -> `재난안전` -> Open API list
- UMMAYA candidate adapter id: `mois_emergency_call_box_lookup`
- UMMAYA primitive: `find`, with `locate` pre-processing
- Application status: approved
- Application evidence: data.go.kr my-page status showed `[승인] 행정안전부_안전비상벨위치정보 조회서비스`
- Application date: `2026-05-16`
- Expiration date: `2028-05-16`
- My-page application reference observed in link: `115974105`

## Why This API Fits UMMAYA

This API can answer direct citizen safety-location questions that a UMMAYA user would naturally ask:

| Citizen query | How UMMAYA would answer with this API |
|---|---|
| "내 주변 비상벨 위치 알려줘." | Resolve the citizen's address/area, call `GET /info` using road-address fragments or local-government code, then return nearby emergency bell installation positions, addresses, coordinates, and managing agency contact. |
| "밤길에 경찰 연계 비상벨 있는 곳 찾아줘." | Filter returned items by `POLC_LINK_EN`, explain whether each nearby bell is police-linked, and include link method or extra functions when recorded. |
| "아이 통학길 주변에 방범용 비상벨이 있는지 확인해줘." | Query each resolved route-area address fragment, de-duplicate by management number, and summarize installation purpose, location type, latest inspection date, and latest inspection result. |

Expected usage is moderate but important: night walking, child-route, campus, housing-area, and local safety questions are common citizen intents, and this is a nationwide standard dataset rather than a one-off municipal file.

## Official Contract

- Host: `apis.data.go.kr/1741000/emergency_call_box_info`
- Base endpoint: `https://apis.data.go.kr/1741000/emergency_call_box_info`
- Operation: `GET /info`
- Full endpoint: `https://apis.data.go.kr/1741000/emergency_call_box_info/info`
- Produces: `application/json`, `application/xml`
- Development traffic shown by portal: `10,000` calls/day
- Update frequency shown by portal: daily
- Official operation description: data is refreshed daily and current as of two days before the query.

### Required Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `serviceKey` | string | 공공데이터포털에서 받은 인증키 |
| `pageNo` | string | 페이지번호 |
| `numOfRows` | string | 한 페이지 결과 수, max `100` |

### Optional Query Parameters

| Parameter | Type | Description |
|---|---|---|
| `returnType` | string | 응답의 데이터 타입 |
| `cond[DAT_UPDT_PNT::GTE]` | string | 데이터갱신시점 이상의 값, `YYYYMMDDHHMMSS` |
| `cond[DAT_UPDT_PNT::LT]` | string | 데이터갱신시점 미만의 값, `YYYYMMDDHHMMSS` |
| `cond[LCTN_ROAD_NM_ADDR::LIKE]` | string | 소재지도로명주소 포함 검색 |
| `cond[SFTY_EMRGNCBLL_INSTL_YR::GTE]` | string | 안전비상벨설치연도 이상의 값 |
| `cond[OPN_ATMY_GRP_CD::EQ]` | string | 개방자치단체코드 |
| `cond[DAT_CRTR_YMD::GTE]` | string | 데이터기준일자 이상의 값, `YYYYMMDD` |
| `cond[DAT_CRTR_YMD::LT]` | string | 데이터기준일자 미만의 값, `YYYYMMDD` |

### Response Fields Relevant to Wrapping

| Field | Meaning |
|---|---|
| `OPN_ATMY_GRP_CD` | 개방자치단체코드 |
| `MNG_NO` | 관리번호 |
| `SFTY_EMRGNCBLL_MNG_NO` | 안전비상벨관리번호 |
| `INSTL_PRPS` | 설치목적 |
| `INSTL_PLC_TYPE` | 설치장소유형 |
| `INSTL_PSTN` | 설치위치 |
| `LCTN_ROAD_NM_ADDR` | 소재지도로명주소 |
| `LCTN_LOTNO_ADDR` | 소재지지번주소 |
| `WGS84_LAT` | WGS84 위도 |
| `WGS84_LOT` | WGS84 경도 |
| `LINK_MTH` | 연계방식 |
| `POLC_LINK_EN` | 경찰연계유무 |
| `SECCO_LINK_EN` | 경비업체연계유무 |
| `MNGOFC_LINK_EN` | 관리사무소연계유무 |
| `EXTRA_FWK` | 부가기능 |
| `SFTY_EMRGNCBLL_INSTL_YR` | 안전비상벨설치연도 |
| `LAST_CHCK_YMD` | 최종점검일자 |
| `LAST_CHCK_RSLT_SE` | 최종점검결과구분 |
| `MNG_INST_NM` | 관리기관명 |
| `MNG_INST_TELNO` | 관리기관전화번호 |
| `DAT_CRTR_YMD` | 데이터 기준일자 |

## Adapter Notes

- Address-first behavior: use `locate` to normalize a citizen address or named place, then query with `cond[LCTN_ROAD_NM_ADDR::LIKE]` and/or `cond[OPN_ATMY_GRP_CD::EQ]`.
- Ranking: rank by address match and WGS84 coordinates when available; de-duplicate with `SFTY_EMRGNCBLL_MNG_NO` or `MNG_NO`.
- Output: return location, install purpose, link method, police/security/office linkage, latest inspection status, managing agency, and phone number.
- Coordinate caveat: the portal description mentions EPSG:5174 while the schema exposes `WGS84_LAT` and `WGS84_LOT`. A future live adapter must validate coordinate semantics with sanitized `curl` evidence before claiming map accuracy.
- CI rule: never call this live endpoint from CI; record sanitized fixtures locally.

## Captured Artifacts

- `data-go-kr-detail.html`
- `data-go-kr-inline-swagger.json`
- `gateway_swagger_guide.pdf`
- `openapi-schemaorg.json`
- `개방자치단체코드_영업상태코드.xlsx`
- `pre-application-screening-2026-05-16-unit-04.md`
