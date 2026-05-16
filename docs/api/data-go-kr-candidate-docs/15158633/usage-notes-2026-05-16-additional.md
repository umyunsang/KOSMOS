# 대전교통공사_부정승차정보 조회 서비스

- Source: <https://www.data.go.kr/data/15158633/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `교통물류`
- Category/provider: `` / ``
- Provider: ``
- UMMAYA primitive candidate: `send/find`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- No downloadable reference document found or the portal exposed only a blank/error download link; saved detail HTML and Swagger instead.

## Adapter-Relevant Contract

- Swagger title: 대전교통공사_부정승차정보 조회 서비스
- Host: `apis.data.go.kr/B554695/UnlawfulEntrySVC`
- Schemes: `https, http`
### `GET /getUnlawfulEntry01`

- Endpoint: `https://apis.data.go.kr/B554695/UnlawfulEntrySVC/getUnlawfulEntry01`
- Summary: 부정승차정보 조회
- Description: 기간을 설정하여 부정승차정보를 조회
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `sDate` | yes | string | 시작날짜 |
| `eDate` | yes | string | 끝날짜 |

Optional params:
- None captured in Swagger parameters. Check `swaggerOprtinVOs` in `data-go-kr-detail.html` before implementation.

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메시지`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.businessDay: 영업일자`
- `body.items.item.stationNo: 역번호(별첨 문서 참조)`
- `body.items.item.inputNo: 일련번호`
- `body.items.item.regType: 단속계도유형(별첨 문서 참조)`
- `body.items.item.regEntryType: 부정승차유형(별첨 문서 참조)`
- `body.items.item.enstationNo: 승차역(별첨 문서 참조)`
- `body.items.item.exstationNo: 하차역(별첨 문서 참조)`
- `body.items.item.payAmt: 납부운임`
- `body.items.item.addAmt: 납부부가운임`
- `body.items.item.totalPayAmt: 납부금액`
- `body.items.item.payType: 납부유형(별첨 문서 참조)`
- `body.items.item.payDay: 납부일자`
- `body.numOfRows: 한 페이지 결과 수`
- `body.pageNo: 페이지번호`
- `body.totalCount: 전체 결과 수`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
