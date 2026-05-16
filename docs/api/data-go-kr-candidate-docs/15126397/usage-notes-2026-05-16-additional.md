# 한국자산관리공사_국유부동산 매각현황 조회서비스 Update

- Source: <https://www.data.go.kr/data/15126397/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `재정금융`
- Category/provider: `재정금융` / `공공기관`
- Provider: `한국자산관리공사`
- UMMAYA primitive candidate: `check`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- No downloadable reference document found or the portal exposed only a blank/error download link; saved detail HTML and Swagger instead.

## Adapter-Relevant Contract

- Swagger title: 한국자산관리공사_국유부동산 매각현황 조회서비스
- Host: `apis.data.go.kr/B010003/kamcoGvwsRlstDsplPscd`
- Schemes: `https, http`
### `GET /dsplPscdInqSrvc`

- Endpoint: `https://apis.data.go.kr/B010003/kamcoGvwsRlstDsplPscd/dsplPscdInqSrvc`
- Summary: 국유재산매각현황
- Description: 국유재산매각현황을 조회한다.
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `pageNo` | yes | string | 페이지번호 |
| `numOfRows` | yes | string | 한 페이지 결과 수 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `resultType` | no | string | 호출방식 |

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메세지`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.CRTR_YMD: 기준일자`
- `body.items.item.YR: 연도`
- `body.items.item.RGN_DIV_NM: 지역구분명`
- `body.items.item.LCTN_NM: 소재지명`
- `body.items.item.PRPT_DIV_NM: 재산구분명`
- `body.items.item.PBLB_CLAND_NM: 공부지목명`
- `body.items.item.LDGR_SQMS: 대장면적`
- `body.items.item.LDGR_AMT: 대장금액`
- `body.items.item.DSPS_DIV_NM: 처분구분명`
- `body.items.item.CTRT_YMD: 계약일자`
- `body.items.item.DEPT_NM: 부서명`
- `body.items.item.TMNM: 팀명`
- `body.numOfRows: 한 페이지 결과 수    `
- `body.pageNo: 페이지번호    `
- `body.totalCount: 전체 결과 수    `
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
