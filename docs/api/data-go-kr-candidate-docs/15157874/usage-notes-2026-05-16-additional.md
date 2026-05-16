# 한국지역난방공사_전기판매량 조회 서비스(GW)

- Source: <https://www.data.go.kr/data/15157874/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `산업고용`
- Category/provider: `산업고용` / `공공기관`
- Provider: `한국지역난방공사`
- UMMAYA primitive candidate: `find`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- No downloadable reference document found or the portal exposed only a blank/error download link; saved detail HTML and Swagger instead.

## Adapter-Relevant Contract

- Swagger title: 한국지역난방공사_전기판매량 조회 서비스(GW)
- Host: `apis.data.go.kr/B550373/kdhcPowerSell`
- Schemes: `https, http`
### `GET /powerSell`

- Endpoint: `https://apis.data.go.kr/B550373/kdhcPowerSell/powerSell`
- Summary: 전기판매량 정보조회
- Description: 조회시작일, 조회종료일을 검색조건으로 하여 월별, 지사별 전기판매량 정보를 제공합니다.
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |
| `startDate` | no | string | 조회 시작일 |
| `endDate` | no | string | 조회 종료일 |

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메세지`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.branchId: 지사코드`
- `body.items.item.branchName: 지사명`
- `body.items.item.pwrQty: 판매량계`
- `body.items.item.pwrQtyUnit: 단위`
- `body.items.item.rnum: 순번`
- `body.items.item.yyyymm: 생산년월`
- `body.numOfRows: 한페이지 결과 수`
- `body.pageNo: 페이지 번호`
- `body.totalCount: 전체 결과 수`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
