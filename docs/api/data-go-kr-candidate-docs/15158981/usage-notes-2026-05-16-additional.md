# 대구광역시_유량정보 조회 서비스_GW

- Source: <https://www.data.go.kr/data/15158981/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `환경기상`
- Category/provider: `환경기상` / `자치행정기관`
- Provider: `대구광역시`
- UMMAYA primitive candidate: `check`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- No downloadable reference document found or the portal exposed only a blank/error download link; saved detail HTML and Swagger instead.

## Adapter-Relevant Contract

- Swagger title: 대구광역시_유량정보 조회 서비스_GW
- Host: `apis.data.go.kr/6270000/openData_2`
- Schemes: `https, http`
### `GET /FltpltYearData`

- Endpoint: `https://apis.data.go.kr/6270000/openData_2/FltpltYearData`
- Summary: 정수장운영년보 정보 조회
- Description: 정수장운영년보 정보를 제공하는 서비스
- Produces: `application/json`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `searchDate` | yes | string | 년도 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `deptId` | no | string | 정수장 |

Representative response fields:
- `rsMsg: 결과정보`
- `rsMsg.statusCode: 결과코드`
- `rsMsg.message: 결과메시지`
- `header: 항목구분`
- `list: 목록`
- `list.gubun: 용수구분`
- `list.deptnm: 정수장명`
- `list.month: 월`
- `list.intake: 취수량`
- `list.out: 송수량`

### `GET /WaterRateByYear`

- Endpoint: `https://apis.data.go.kr/6270000/openData_2/WaterRateByYear`
- Summary: 년도별유수율실적 정보 조회
- Description: 년도별유수율실적 정보를 제공하는 서비스
- Produces: `application/json`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `searchDate` | yes | string | 년도 |
| `startMonth` | yes | string | 시작월 |
| `endMonth` | yes | string | 종료월 |

Optional params:
- None captured in Swagger parameters. Check `swaggerOprtinVOs` in `data-go-kr-detail.html` before implementation.

Representative response fields:
- `rsMsg: 결과정보`
- `rsMsg.statusCode: 결과코드`
- `rsMsg.message: 결과메시지`
- `header: 항목구분`
- `list: 목록`
- `list.year: 년도`
- `list.month: 월`
- `list.supplyamt: 생산량(㎥)`
- `list.ctlamt: 조정량(㎥)`
- `list.fluxrate: 유수율(%)`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
