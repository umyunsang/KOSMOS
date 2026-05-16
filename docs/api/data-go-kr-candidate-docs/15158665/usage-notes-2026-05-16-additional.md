# 한국대학교육협의회_대학 및 전문대학정보_GW

- Source: <https://www.data.go.kr/data/15158665/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `교육`
- Category/provider: `교육` / `공공기관`
- Provider: `한국대학교육협의회`
- UMMAYA primitive candidate: `find`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- No downloadable reference document found or the portal exposed only a blank/error download link; saved detail HTML and Swagger instead.

## Adapter-Relevant Contract

- Swagger title: 한국대학교육협의회_대학 및 전문대학정보_GW
- Host: `apis.data.go.kr/B340014/SchoolInfoService`
- Schemes: `https, http`
### `GET /getSchoolInfo`

- Endpoint: `https://apis.data.go.kr/B340014/SchoolInfoService/getSchoolInfo`
- Summary: 한국대학교육협의회_대학 및 전문대학정보
- Description: 한국대학교육협의회 대학 및 전문대학정보 제공(저작권에 위배되지 않는 정보)
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `svyYr` | yes | string | 조사년도 |
| `schlKrnNm` | yes | string | 학교명 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |
| `schlId` | no | string | 학교코드 |

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메시지`
- `body: body`
- `body.totalCount: 전체 결과 수`
- `body.pageNo: 페이지번호`
- `body.numOfRows: 한 페이지 결과 수`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.lstUpdtDtm: 최종수정일`
- `body.items.item.pbnfAreaCd: 시도코드`
- `body.items.item.pbnfAreaNm: 시도명`
- `body.items.item.postNo: 도로명우편번호`
- `body.items.item.postNoAdrs: 소재지도로명주소`
- `body.items.item.psbsDivNm: 본분교명`
- `body.items.item.schlDivNm: 대학구분명`
- `body.items.item.schlEngNm: 학교영문명`
- `body.items.item.schlEstbDivNm: 설립형태구분명`
- `body.items.item.schlEstbDt: 설립일자`
- `body.items.item.schlId: 학교ID`
- `body.items.item.schlKndNm: 학교구분명`
- `body.items.item.schlNm: 학교명`
- `body.items.item.schlRepFxNoCtnt: 대표팩스번호`
- `body.items.item.schlRepTpNoCtnt: 대표전화번호`
- `body.items.item.schlUrlAdrs: 홈페이지주소`
- `body.items.item.svyYr: 조사연도`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
