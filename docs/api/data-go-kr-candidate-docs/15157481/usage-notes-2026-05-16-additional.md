# 부산시설공단_공원시설 현황 조회 서비스

- Source: <https://www.data.go.kr/data/15157481/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `문화관광`
- Category/provider: `문화관광` / `공공기관`
- Provider: `부산시설공단`
- UMMAYA primitive candidate: `find`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- No downloadable reference document found or the portal exposed only a blank/error download link; saved detail HTML and Swagger instead.

## Adapter-Relevant Contract

- Swagger title: 부산시설공단_공원시설 현황 조회 서비스
- Host: `apis.data.go.kr/B552587/ParkInfoService_v2`
- Schemes: `https, http`
### `GET /getParkProgramList_v2`

- Endpoint: `https://apis.data.go.kr/B552587/ParkInfoService_v2/getParkProgramList_v2`
- Summary: 공원시설 프로그램 조회
- Description: 부산시설공단에서 관리중인 공원시설 프로그램 및 문화행사 프로그램(행사)명,기간, 장소, 연락처, 세부내용 안내 홈페이지 링크 등의 목록을 조회한다.
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
| `resultType` | no | string | 응답 포맷: json 또는 xml (기본값: xml) |

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메세지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.totalCount: 데이터 총 개수`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.pgterm: 행사 기간`
- `body.items.item.pgtime: 행사 시간`
- `body.items.item.detaillink: 프로그램 및 문화행사의 세부정보를 볼수 있는 홈페이지 링크`
- `body.items.item.pgname: 프로그램 또는 문화행사의 명칭`
- `body.items.item.pgpark: 공원명칭`
- `body.items.item.pgphone: 프로그램 관련 문의처(전화번호)`
- `body.items.item.pgplace: 프로그램 또는 문화행사의 장소`
- `body.items.item.pgtarget: 프로그램의 대상`
- `body.numOfRows: 한 페이지 결과 수\t`
- `body.pageNo: 페이지 수`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
