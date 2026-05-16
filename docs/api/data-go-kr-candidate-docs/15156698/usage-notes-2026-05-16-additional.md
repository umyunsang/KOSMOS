# 한국서부발전(주)_(AI친화)AI 디지털트윈 개발용 플랜트 운전 정보 조회 서비스

- Source: <https://www.data.go.kr/data/15156698/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `산업고용`
- Category/provider: `산업고용` / `공공기관`
- Provider: `한국서부발전(주)`
- UMMAYA primitive candidate: `check`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- No downloadable reference document found or the portal exposed only a blank/error download link; saved detail HTML and Swagger instead.

## Adapter-Relevant Contract

- Swagger title: 한국서부발전(주)_(AI친화)AI 디지털트윈 개발용 플랜트 운전 정보 조회 서비스
- Host: `apis.data.go.kr/B552522/AiDigitalTwinPlantService`
- Schemes: `https, http`
### `GET /getAiDigitalTwinPlantService`

- Endpoint: `https://apis.data.go.kr/B552522/AiDigitalTwinPlantService/getAiDigitalTwinPlantService`
- Summary: AI 디지털트윈 개발용 플랜트 운전 정보 조회
- Description: 발전소명, 호기명, 태그명 및 태그 데이터 생성시간을 기준으로 단위, 태그 값, 센서타입, flag코드를 조회한다.
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey ` | yes | string | 공공데이터포털에서 받은 인증키 |
| `fromDate` | yes | string | 시작날짜 |
| `toDate` | yes | string | 종료날짜 |
| `plant` | yes | string | 발전소명 |
| `clsf_cd` | yes | string | 분류 코드 |
| `hogi` | yes | string | 호기명 |
| `tag` | yes | string | 태그명 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |
| `type` | no | string | 응답데이터 포맷 |

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메시지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.totalCount: 전체 결과 수`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.pwst_nm: 발전소 명`
- `body.items.item.tag_data_nvl: 태그 값`
- `body.items.item.meno_nm: 호기 명`
- `body.items.item.tag_data_crt_hr: 태그 데이터 생성 시간`
- `body.items.item.description: 태그 설명`
- `body.items.item.flag_cd: FLAG`
- `body.items.item.tag_nm: 태그명`
- `body.pageNo: 페이지번호`
- `body.numOfRows: 한 페이지 결과 수`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
