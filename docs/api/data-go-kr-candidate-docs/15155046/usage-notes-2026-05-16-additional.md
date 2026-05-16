# 행정안전부_안전비상벨위치정보 조회서비스

- Source: <https://www.data.go.kr/data/15155046/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `재난안전`
- Category/provider: `재난안전` / `국가행정기관`
- Provider: `행정안전부`
- UMMAYA primitive candidate: `locate/find`
- Application status: `approved_after_user_authorized_direct_submission`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- `개방자치단체코드_영업상태코드.xlsx`

## Adapter-Relevant Contract

- Swagger title: 행정안전부_안전비상벨위치정보 조회서비스
- Host: `apis.data.go.kr/1741000/emergency_call_box_info`
- Schemes: `https, http`
### `GET /info`

- Endpoint: `https://apis.data.go.kr/1741000/emergency_call_box_info/info`
- Summary: 안전비상벨위치정보 데이터 조회
- Description: 안전비상벨위치정보 데이터를 조회 하기 위한 오퍼레이션 입니다.<br/>해당 데이터는 매일 갱신되는 데이터로 2일전 기준으로 현행화 됩니다.
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `pageNo` | yes | string | 페이지번호 |
| `numOfRows` | yes | string | 한 페이지 결과 수(max: 100) |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `returnType` | no | string | 응답의 데이터 타입 |
| `cond[DAT_UPDT_PNT::GTE]` | no | string | 데이터갱신시점 이상의 값(YYYYMMDDHHMMSS) |
| `cond[DAT_UPDT_PNT::LT]` | no | string | 데이터갱신시점 미만의 값(YYYYMMDDHHMMSS) |
| `cond[LCTN_ROAD_NM_ADDR::LIKE]` | no | string | 소재지도로명주소 을(를) 포함하는 값 |
| `cond[SFTY_EMRGNCBLL_INSTL_YR::GTE]` | no | string | 안전비상벨설치연도 이상의 값 |
| `cond[OPN_ATMY_GRP_CD::EQ]` | no | string | 개방자치단체코드 |
| `cond[DAT_CRTR_YMD::GTE]` | no | string | 데이터기준일자 이상의 값(YYYYMMDD) |
| `cond[DAT_CRTR_YMD::LT]` | no | string | 데이터기준일자 미만의 값(YYYYMMDD) |

Representative response fields:
- `response: response`
- `response.header: 응답 데이터의 헤더`
- `response.header.resultCode: 응답의 결과 코드`
- `response.header.resultMsg: 응답의 결과 메세지`
- `response.body: 응답 데이터의 바디`
- `response.body.dataType: 응답의 데이터 타입`
- `response.body.numOfRows: 한 페이지 결과 수`
- `response.body.pageNo: 페이지번호`
- `response.body.totalCount: 응답 데이터의 수`
- `response.body.items: items`
- `response.body.items.item: item`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: submitted in unit `04` after the user explicitly instructed direct submission. My-page status showed `[승인] 행정안전부_안전비상벨위치정보 조회서비스`, 신청일 `2026-05-16`, 만료예정일 `2028-05-16`.
