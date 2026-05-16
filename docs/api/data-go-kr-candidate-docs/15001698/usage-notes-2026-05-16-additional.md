# 건강보험심사평가원_병원정보서비스

- Source: <https://www.data.go.kr/data/15001698/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `보건의료`
- Category/provider: `보건의료` / `공공기관`
- Provider: `건강보험심사평가원`
- UMMAYA primitive candidate: `find`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- `OpenAPI활용가이드_건강보험심사평가원(병원정보서비스)_210616.docx`

## Adapter-Relevant Contract

- Swagger title: 건강보험심사평가원_병원정보서비스
- Host: `apis.data.go.kr/B551182/hospInfoServicev2`
- Schemes: `https, http`
### `GET /getHospBasisList`

- Endpoint: `https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList`
- Summary: 병원기본목록
- Description: 의료기관 검색결과 제공 (요양기관명,주소,전화번호,URL)
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `ServiceKey` | yes | string | 서비스키 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |
| `sidoCd` | no | string | 시도코드 |
| `sgguCd` | no | string | 시군구코드 |
| `emdongNm` | no | string | 읍면동명 |
| `yadmNm` | no | string | 병원명(UTF-8 인코딩 필요) |
| `zipCd` | no | string | 분류코드(활용가이드 참조) |
| `clCd` | no | string | 종별코드(활용가이드 참조) |
| `dgsbjtCd` | no | string | 진료과목코드(활용가이드 참조) |
| `xPos` | no | string | x좌표(소수점 15) |
| `yPos` | no | string | y좌표(소수점 15) |
| `radius` | no | string | 단위 : 미터(m) |

Representative response fields:
- `header: 헤더`
- `header.resultMsg: 결과메세지`
- `header.resultCode: 결과코드`
- `body: 바디`
- `body.items: 리스트 항목`
- `body.items.item: 세부항목`
- `body.items.item.detyGdrCnt: 치과일반의 인원수`
- `body.items.item.detyIntnCnt: 치과인턴 인원수`
- `body.items.item.detyResdntCnt: 치과레지던트 인원수`
- `body.items.item.detySdrCnt: 치과전문의 인원수`
- `body.items.item.cmdcResdntCnt: 한방레지던트 인원수`
- `body.items.item.cmdcSdrCnt: 한방전문의 인원수`
- `body.items.item.pnursCnt: 조산사 인원수`
- `body.items.item.XPos: x좌표`
- `body.items.item.YPos: y좌표`
- `body.items.item.distance: 거리`
- `body.items.item.cmdcGdrCnt: 한방일반의 인원수`
- `body.items.item.cmdcIntnCnt: 한방인턴 인원수`
- `body.items.item.mdeptResdntCnt: 의과레지던트 인원수`
- `body.items.item.drTotCnt: 의사총수`
- `body.items.item.mdeptGdrCnt: 의과일반의 인원수`
- `body.items.item.mdeptIntnCnt: 의과인턴 인원수`
- `body.items.item.telno: 전화번호`
- `body.items.item.hospUrl: 홈페이지`
- `body.items.item.estbDd: 개설일자`
- `body.items.item.sgguCdNm: 시군구명`
- `body.items.item.emdongNm: 읍면동명`
- `body.items.item.postNo: 우편번호`
- `body.items.item.addr: 주소`
- `body.items.item.sidoCdNm: 시도명`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
