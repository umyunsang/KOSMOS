# 한국예탁결제원_주식정보서비스_GW

- Source: <https://www.data.go.kr/data/15157413/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `재정금융`
- Category/provider: `재정금융` / `공공기관`
- Provider: `한국예탁결제원`
- UMMAYA primitive candidate: `find`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- No downloadable reference document found or the portal exposed only a blank/error download link; saved detail HTML and Swagger instead.

## Adapter-Relevant Contract

- Swagger title: 한국예탁결제원_주식정보서비스_GW
- Host: `apis.data.go.kr/B552481/StockSvc`
- Schemes: `https, http`
### `GET /getKDRSecnInfo`

- Endpoint: `https://apis.data.go.kr/B552481/StockSvc/getKDRSecnInfo`
- Summary: 시장별 KDR 종목 전체 조회
- Description: 한국거래소에 상장된 KDR 종목을 상장시장별로 조회
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `caltotMartTpcd` | yes | string | 시장구분(11: 유가증권시장, 12: 코스닥시장, 13: 코넥스시장) |

Optional params:
- None captured in Swagger parameters. Check `swaggerOprtinVOs` in `data-go-kr-detail.html` before implementation.

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메세지`
- `body: body`
- `body.totalCount: 전체 결과 수`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.kdrIsin: KDR 종목코드(KR표준코드)`
- `body.items.item.korSecnNm: 한글종목명`
- `body.items.item.listDt: 상장일(YYYYMMDD)`
- `body.items.item.ovsListStkmkCd: 해외상장시장(기술문서 참조)`

### `GET /getVctfDivRankInfo`

- Endpoint: `https://apis.data.go.kr/B552481/StockSvc/getVctfDivRankInfo`
- Summary: 유가증권시장 배당순위 조회
- Description: 액면가배당율을 기준으로한 연간 배당금 지급액 TOP3 종목(유가증권 상장 보통주)을 조회
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `schStdYy` | yes | string | 조회기준연도 |

Optional params:
- None captured in Swagger parameters. Check `swaggerOprtinVOs` in `data-go-kr-detail.html` before implementation.

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메시지`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.shotnIsin: 단축코드`
- `body.items.item.exerPrcp: 종목명`
- `body.items.item.persDivamt: 주당배당금`
- `body.items.item.pvalDivrate: 액면가배당율`
- `body.items.item.rank: 순위`
- `body.totalCount: 전체 결과 수`

### `GET /getTotIssuStkQty`

- Endpoint: `https://apis.data.go.kr/B552481/StockSvc/getTotIssuStkQty`
- Summary: 상장시장별 총발행주식수 현황 조회
- Description: 한국거래소 장내시장(유가증권, 코스닥, 코넥스시장)에 발행된 총 발행주식수를 시장별로 조회
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `schStdDt` | yes | string | 조회기준일 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메시지`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.vctfMart: 유가증권시장 총발행주식수`
- `body.items.item.konexMart: 코넥스시장 총발행주식수`
- `body.items.item.kosdaqMart: 코스닥시장 총발행주식수`
- `body.items.item.schStdDt: 조회기준일(YYYYMMDD)`
- `body.pageNo: 페이지 번호`
- `body.numOfRows: 한 페이지 결과 수`
- `body.totalCount: 전체 결과 수`

### `GET /getKDRIssuLmtDetailsN1`

- Endpoint: `https://apis.data.go.kr/B552481/StockSvc/getKDRIssuLmtDetailsN1`
- Summary: KDR 발행한도 내역
- Description: 종목별 KDR 발행한도 조회
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `isin` | yes | string | 종목코드(KR표준코드) |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메시지`
- `body: body`
- `body.totalCount: 전체 결과 수`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.issuLmtDocQty: 한도증서수`
- `body.items.item.korSecnNm: 국문종목명`
- `body.items.item.caltotMartTpcd: 시장구분명([11]유가증권시장 [12]코스닥시장 [13]K-OTC시장 [14]코넥스시장 [50]기타비상장)`
- `body.items.item.kdrIssuRacd: KDR발행사유코드([1]최초공모 [2]유상증자 [3]무상증자 [4]주식배당 [5]추가발행 [6]기타증가 [7]기타감소 [8]구주주발행))`
- `body.items.item.issuLmtRegiDt: 한도적용일(YYYYMMDD)`
- `body.pageNo: 페이지 번호`
- `body.numOfRows: 한 페이지 결과 수`

### `GET /getSecSetlCostStatN1`

- Endpoint: `https://apis.data.go.kr/B552481/StockSvc/getSecSetlCostStatN1`
- Summary: 월별 주식결제대금현황
- Description: 월별 주식결제대금현황
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `schBeginDt` | yes | string | 조회시작일자 |
| `schExpryDt` | yes | string | 조회종료일자 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메시지`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.kotcSetlCost: K-OTC시장 결제대금`
- `body.items.item.stdYymm: 기준년월(조회시작일자~조회종료일자 내 월별로 데이터로 제공)`
- `body.items.item.martsetlTrCost: 주식시장결제 거래대금`
- `body.items.item.martsetlSetlCost: 주식시장결제 결제대금`
- `body.items.item.stkisetlTrCost: 주식기관결제 거래대금`
- `body.items.item.stkisetlSetlCost: 주식기관결제 결제대금`
- `body.items.item.kotcTrCost: K-OTC시장 거래대금`
- `body.totalCount: 전체 결과 수`
- `body.pageNo: 페이지 번호`
- `body.numOfRows: 한 페이지 결과 수`

### `GET /getStkIsinByNmN1`

- Endpoint: `https://apis.data.go.kr/B552481/StockSvc/getStkIsinByNmN1`
- Summary: 종목명칭으로 주식종목코드 및 기본정보 조회
- Description: 주식 종목명칭을 기준으로 종목번호와 단축코드, 주식종류 등 주식의 기본정보 조회
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `secnNm` | yes | string | 발행회사명 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메시지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.numOfRows: 한 페이지 결과 수`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.shotnIsin: 단축코드(6자리)`
- `body.items.item.engSecnNm: 영문 종목명`
- `body.items.item.isin: 종목번호(KR표준코드)`
- `body.items.item.issuDt: 발행일(YYYYMMDD)`
- `body.items.item.issucoCustno: 발행회사번호(기업정보서비스 참조)`
- `body.items.item.korSecnNm: 한글 종목명`
- `body.items.item.secnKacdNm: 주식종류(보통주/우선주)`
- `body.items.item.eltscYn: 전자증권 여부(Y/N)`
- `body.totalCount: 전체 결과 수`
- `body.pageNo: 페이지 번호`

### `GET /getStkIsinByShortIsinN1`

- Endpoint: `https://apis.data.go.kr/B552481/StockSvc/getStkIsinByShortIsinN1`
- Summary: 단축번호로 주식종목코드(풀코드) 조회
- Description: 단축번호를 기준으로 주식종목코드(풀코드) 및 종목명, 발행일 등 주식 기본정보 조회
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `pageNo` | yes | string | 페이지번호 |
| `numOfRows` | yes | string | 한 페이지 결과 수 |
| `shortIsin` | yes | string | 단축코드(6자리) |

Optional params:
- None captured in Swagger parameters. Check `swaggerOprtinVOs` in `data-go-kr-detail.html` before implementation.

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메시지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.numOfRows: 한 페이지 결과 수`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.secnKacdNm: 주식종류`
- `body.items.item.engSecnNm: 영문 종목명`
- `body.items.item.isin: 종목코드(KR표준코드)`
- `body.items.item.issuDt: 발행일(YYYYMMDD)`
- `body.items.item.issucoCustno: 발행회사번호(기업정보서비스 참조)`
- `body.items.item.korSecnNm: 국문종목명`
- `body.items.item.eltscYn: 전자증권 여부(Y/N)`
- `body.items.item.shotnIsin: 단축코드(6자리)`
- `body.totalCount: 전체 결과 수`
- `body.pageNo: 페이지 번호`

### `GET /getDividendRankN1`

- Endpoint: `https://apis.data.go.kr/B552481/StockSvc/getDividendRankN1`
- Summary: 배당순위조회
- Description: 순위구분, 조회기준연도, 상장구분, 주식종류를 기준으로 배당순위, 결산월일 등 배당관련 정보를 조회
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `rankTpcd` | yes | string | 순위구분(1.시가배당율, 2.액면가배당율) |
| `year` | yes | string | 기준년도(YYYY) |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |
| `stkTpcd` | no | string | 주식종류(1. 보통주 2.우선주) |
| `listTpcd` | no | string | 상장구분(11. 유가증권시장 12.코스닥시장 13.K-OTC시장 14.코넥스시장 50.기타비상장) |

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메시지`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.shotnIsin: 단축코드(6자리)`
- `body.items.item.caltotMartTpcd: 시장구분명`
- `body.items.item.divAmtPerStk: 주당배당금`
- `body.items.item.divRateCpri: 시가배당율(%)`
- `body.items.item.divRatePval: 액면가배당율(%)`
- `body.items.item.issucoCustno: 발행회사번호(기업정보서비스 참조)`
- `body.items.item.korSecnNm: 국문 종목명`
- `body.items.item.num: 배당 순위`
- `body.items.item.pval: 액면가`
- `body.items.item.secnKacd: 주식종류(보통주/우선주)`
- `body.items.item.setaccMm: 결산월(예:12)`
- `body.items.item.setaccMmdd: 결산월일(예:1231)`
- `body.totalCount: 전체 결과 수`
- `body.pageNo: 페이지 번호`
- `body.numOfRows: 한 페이지 결과 수`

### `GET /getSafeDpDutyDepoStatusN1`

- Endpoint: `https://apis.data.go.kr/B552481/StockSvc/getSafeDpDutyDepoStatusN1`
- Summary: 의무보호예수전체현황 전체현황표 조회
- Description: 조회기준일과 상장구분을 기준으로 의무보호예수주식주, 보호예수비율 등 의무보호예수 전체현황 조회
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `stdDt` | yes | string | 기준일(YYYYMMDD) |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |
| `listTpcd` | no | string | 상장구분(11. 유가증권시장 12.코스닥시장 13.K-OTC시장 14.코넥스시장 50.기타비상장) |

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메시지`
- `body: body`
- `body.numOfRows: 한 페이지 결과 수`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.stkDepoQty: 의무보유예탁 주식수`
- `body.items.item.cocnt: 의무보호예수 기업수`
- `body.items.item.issuStkKindTpcd: 주식종류코드(주식종류명 참조)`
- `body.items.item.issuStkKindTpnm: 주식종류명(예:보통주/우선주)`
- `body.items.item.issuStkqty: 총발행주식수`
- `body.items.item.safedpRatioValue: 보호예수비율(%)`
- `body.items.item.secncnt: 종목수`
- `body.items.item.stdDt: 기준일(YYYYMMDD)`
- `body.totalCount: 전체 결과 수`
- `body.pageNo: 페이지 번호`

### `GET /getSafeDpDutyDepoRgtStatusN1`

- Endpoint: `https://apis.data.go.kr/B552481/StockSvc/getSafeDpDutyDepoRgtStatusN1`
- Summary: 의무보호예수전체현황 사유별 조회
- Description: 상장구분과 기준일을 이용하여 의무보호예수 사유, 기업수, 종목수 등 의무보호예수 정보 조회
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `pageNo` | yes | string | 페이지번호 |
| `numOfRows` | yes | string | 한 페이지 결과 수 |
| `listTpcd` | yes | string | 상장구분(11.유가증권시장 12.코스닥시장 13.K-OTC시장 14.코넥스시장 50.기타비상장) |
| `stdDt` | yes | string | 기준일(YYYYMMDD) |

Optional params:
- None captured in Swagger parameters. Check `swaggerOprtinVOs` in `data-go-kr-detail.html` before implementation.

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메시지`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.safedpStkDepoQty: 의무보유예탁주식수`
- `body.items.item.codevalueNm: 사유명(예: 최대주주(상장))`
- `body.items.item.dutyDepoCocnt: 의무보호예수기업수`
- `body.items.item.dutyDepoSecncnt: 의무보호예수종목수`
- `body.items.item.dutyDepoStkDepoQty: 의무보호예수주식수`
- `body.items.item.safedpCocnt: 의무보유예탁기업수`
- `body.items.item.safedpRacd: 사유코드`
- `body.items.item.safedpSecncnt: 의무보유예탁종목수`
- `body.totalCount: 전체 결과 수`
- `body.pageNo: 페이지 번호`
- `body.numOfRows: 한 페이지 결과 수`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
