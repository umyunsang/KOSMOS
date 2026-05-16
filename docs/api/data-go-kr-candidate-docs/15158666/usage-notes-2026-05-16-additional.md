# 한국대학교육협의회_대학별 학과정보_GW

- Source: <https://www.data.go.kr/data/15158666/openapi.do>
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

- Swagger title: 한국대학교육협의회_대학별 학과정보_GW
- Host: `apis.data.go.kr/B340014/SchoolMajorInfoService`
- Schemes: `https, http`
### `GET /getSchoolMajorInfo`

- Endpoint: `https://apis.data.go.kr/B340014/SchoolMajorInfoService/getSchoolMajorInfo`
- Summary: 한국대학교육협의회_대학별 학과정보
- Description: 한국대학교육협의회_대학별 학과정보(저작권에 위배되지 않는 정보)
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
- `body.items.item.clgNm: 단과대학명`
- `body.items.item.dghtDivNm: 주야과정명`
- `body.items.item.edcCrseLtrCtnt: 교육과정`
- `body.items.item.eschlPscpNum: 입학정원수`
- `body.items.item.grdtNum: 졸업자수`
- `body.items.item.kediMjrId: 학과코드(7대계열)`
- `body.items.item.korMjrNm: 학과명`
- `body.items.item.lsnTrmNm: 수업연한`
- `body.items.item.lstUpdtDtm: 데이터기준일자`
- `body.items.item.mjrAreaCd: 시도코드`
- `body.items.item.mjrAreaNm: 시도명`
- `body.items.item.mjrAreaSignguCd: 시군구코드`
- `body.items.item.mjrAreaSignguNm: 시군구명`
- `body.items.item.mjrUpdtDtm: 수정일자`
- `body.items.item.onsfSrsClftNm: 대학자체계열명`
- `body.items.item.pbnfDgriCrseDivNm: 학위과정명`
- `body.items.item.pwayEmplLtrCtnt: 관련직업명`
- `body.items.item.schlKndNm: 학교구분명`
- `body.items.item.schlMjrCharNm: 학교학과특성명`
- `body.items.item.schlMjrStatNm: 학과상태명`
- `body.items.item.schlNm: 학교명`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
