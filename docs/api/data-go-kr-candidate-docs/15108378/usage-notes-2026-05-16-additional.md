# 국토교통부_마이홈포털 예비입주자 대기현황 조회서비스

- Source: <https://www.data.go.kr/data/15108378/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `국토관리`
- Category/provider: `국토관리` / `국가행정기관`
- Provider: `국토교통부`
- UMMAYA primitive candidate: `send/find`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- `붙임1. 요청 파라미터 코드(예비입주자 대기현황)_260331.xlsx`

## Adapter-Relevant Contract

- Swagger title: 국토교통부_마이홈포털 예비입주자 대기현황 조회서비스
- Host: `apis.data.go.kr/1613000/HWSPR03`
- Schemes: `https, http`
### `GET /moveWaitStsList`

- Endpoint: `https://apis.data.go.kr/1613000/HWSPR03/moveWaitStsList`
- Summary: 예비입주자 대기현황 조회
- Description: 광역시도, 시군구, 임대종류, 주택유형을 기준으로 예비입주자 대기현황 정보를 조회하는 서비스
- Produces: `application/json`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `brtcCode` | yes | string | 광역시도 코드 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `signguCode` | no | string | 시군구 코드 |
| `numOfRows` | no | string | 조회될 목록의 페이지당 데이터 개수 (기본값 : 10) |
| `pageNo` | no | string | 조회될 페이지의 번호 (기본값:1) |
| `suplyTy` | no | string | 임대종류 |
| `houseTy` | no | string | 주택유형 |

Representative response fields:
- `header`
- `body`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
