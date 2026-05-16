# 부산시설공단_한마음스포츠센터 생활체육 프로그램 정보 조회 서비스

- Source: <https://www.data.go.kr/data/15157491/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `문화관광`
- Category/provider: `문화관광` / `공공기관`
- Provider: `부산시설공단`
- UMMAYA primitive candidate: `check`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- No downloadable reference document found or the portal exposed only a blank/error download link; saved detail HTML and Swagger instead.

## Adapter-Relevant Contract

- Swagger title: 부산시설공단_한마음스포츠센터 생활체육 프로그램 정보 조회 서비스
- Host: `apis.data.go.kr/B552587/GetProgramInfoService_v2`
- Schemes: `https, http`
### `GET /pPROGRAMList_v2`

- Endpoint: `https://apis.data.go.kr/B552587/GetProgramInfoService_v2/pPROGRAMList_v2`
- Summary: 프로그램정보조회
- Description: 한마음스포츠센터 수강 신청 가능한 프로그램 목록 실시간 조회
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
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메세지`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.yearmonth: 프로그램 년월`
- `body.items.item.capacity: 정원`
- `body.items.item.classname: 반`
- `body.items.item.fee: 수강료`
- `body.items.item.programname: 프로그램명`
- `body.items.item.registration: 등록수`
- `body.items.item.remark: 비고`
- `body.items.item.roomname: 진행장소`
- `body.items.item.state: 등록상태`
- `body.items.item.targetname: 수강대상`
- `body.items.item.time: 시간`
- `body.items.item.trainingdate: 수업일자(요일)`
- `body.totalCount: 데이터 총 개수`
- `body.numOfRows: 한 페이지 결과 수`
- `body.pageNo: 페이지 수`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
