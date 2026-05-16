# 국토교통부_회계감사보고서 정보

- Source: <https://www.data.go.kr/data/15012966/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `국토관리`
- Category/provider: `국토관리` / `국가행정기관`
- Provider: `국토교통부`
- UMMAYA primitive candidate: `check`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- No downloadable reference document found or the portal exposed only a blank/error download link; saved detail HTML and Swagger instead.

## Adapter-Relevant Contract

- Swagger title: 국토교통부_회계감사보고서 정보
- Host: `apis.data.go.kr/1613000/AptAccnutReportService2`
- Schemes: `https, http`
### `GET /getHsmpAccnutReportInfoV5`

- Endpoint: `https://apis.data.go.kr/1613000/AptAccnutReportService2/getHsmpAccnutReportInfoV5`
- Summary: 단지별 회계감사보고서 정보조회
- Description: 단지코드, 회계연도를 이용해 단지코드, 단지명, 회계감사 이행여부, 회계연도, 회계연도 기간 시작일자, 회계연도 기간 종료일자, 회계감사 미실시 동의세대수, 회계감사 대상 세대수(입주한 경우만), 등록일, 결산기준년도, 결산기준월, 회계감사업체명, 계약금액(부가세제외), 회계감사계약체결일, 회계감사 현장감사 착수일, 회계감사 현장감사 종료일, 연간관리수입총액, 연간관리비용지출총액, 기타수입총액, 당기순이익을 조회할 수 있는 회계감사보고서 정보제공 서비스
- Produces: `application/json`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 발급받은 인증키 |
| `kaptCode` | yes | string | 단지코드 |
| `audtYear` | yes | string | 회계연도 |

Optional params:
- None captured in Swagger parameters. Check `swaggerOprtinVOs` in `data-go-kr-detail.html` before implementation.

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메세지`
- `header.resultCode: 00:성공`
- `body: body`
- `body.item: item`
- `body.item.audtContDate: 회계감사체결일`
- `body.item.audtDoEdate: 회계감사 현자감사 종료일`
- `body.item.audtDoSdate: 회계감사 현자감사 시작일`
- `body.item.audtTargetEdate: 회계연도 기간 종료일자`
- `body.item.audtTargetSdate: 회계연도 기간 시작일자`
- `body.item.audtYear: 회계연도(년)`
- `body.item.kaptName: 단지명`
- `body.item.netProfit: 당기순이익(원)`
- `body.item.regDate: 등록일`
- `body.item.byyrIncomeTot: 연간관리수입 총액(원)`
- `body.item.agreeCnt: 회계감사 미실시 동의세대수`
- `body.item.audtCnt: 회계감사 대상 세대수(입주한 경우만)`
- `body.item.audtCompanyName: 회계감사업체명`
- `body.item.audtYn: 회계감사 이행여부`
- `body.item.byyrCostTot: 연간관리비용 지출 총액(원)`
- `body.item.audtSettleMonth: 결산기준월`
- `body.item.audtSettleYear: 결산기준년도`
- `body.item.contAmount: 계약금액(부가세제외)`
- `body.item.etcIncomeTot: 기타수입총액(원)`
- `body.item.kaptCode: 단지코드`
- `body.item.audtOpinion: 감사의견`

### `GET /getAccnutReportList2`

- Endpoint: `https://apis.data.go.kr/1613000/AptAccnutReportService2/getAccnutReportList2`
- Summary: 회계감사보고서 목록조회
- Description: 법정동코드를 이용해 법정동주소, 도로명주소, 단지코드, 단지명, 회계연도를 조회할 수 있는 회계감사보고서 정보제공 서비스
- Produces: `application/json`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 발급받은 인증키 |
| `bjdCode` | yes | string | 행정표준코드관리시스템에서 제공하는 법정동 시군구코드 5자리 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지 번호 |
| `numOfRows` | no | string | 목록 건수 |

Representative response fields:
- `header: header`
- `header.resultCode: 00:정상`
- `header.resultMsg: 결과메세지`
- `body: body`
- `body.items: items`
- `body.items.kaptName: 단지명`
- `body.items.kaptAddr: 법정동주소`
- `body.items.doroJuso: 도로명주소`
- `body.items.kaptCode: 단지코드`
- `body.items.audtYear: 회계연도(년)`
- `body.numOfRows: 한 페이지 결과 수`
- `body.pageNo: 페이지 번호`
- `body.totalCount: 목록 건수`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
