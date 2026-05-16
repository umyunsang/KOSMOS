# Unit 13 pre-application screening: data.go.kr API 15129471

## Candidate

- Portal ID: `15129471`
- API name: `조달청_종합쇼핑몰 품목정보 서비스`
- Portal URL: `https://www.data.go.kr/data/15129471/openapi.do`
- Provider: `조달청`
- Classification: `일반공공행정 - 정부조달`
- Category seen: `공공행정`
- Format: `JSON+XML`
- Type: `REST`
- Update cadence: real time
- License: no usage restriction

## UMMAYA fit decision

Decision: apply and keep as a UMMAYA `lookup` adapter candidate.

Rationale: this is a national public-procurement catalog and delivery-request channel. It is less everyday-citizen-facing than emergency, welfare, or health data, but it is a strong UMMAYA fit for public transparency and business/civic queries because citizens, SMEs, and public officials can ask about government-shopping catalog products, suppliers, contract price, product identifiers, certification status, delivery requests, and procurement history without navigating 나라장터 screens manually.

## Citizen natural-language coverage

- "나라장터 종합쇼핑몰에서 공공기관이 살 수 있는 전광판 품목 찾아줘."
- "이 물품식별번호의 계약가격, 공급업체, 납품기한, 인증정보 알려줘."
- "최근 특정 기관이 어떤 사무용품을 납품요구했는지 조회해줘."
- "우수조달물품 또는 중소기업자간경쟁제품 여부를 확인해줘."
- "특정 품목의 조달 내역과 기관별 구매실적을 요약해줘."

## Primitive mapping

- Primary primitive: `lookup`
- Secondary primitive: none for the initial adapter. The API exposes procurement/catalog lookup and delivery-request history, not bid submission or purchase execution.

## Wrapping sketch

The adapter should map a citizen's procurement question to one of three lookup paths:

1. Catalog/product lookup with `/getShoppingMallPrdctInfoList` or contract-specific product endpoints.
2. Delivery-request lookup with `/getDlvrReqInfoList` and `/getDlvrReqDtlInfoList`.
3. Procurement-history lookup with `/getSpcifyPrdlstPrcureInfoList` and `/getSpcifyPrdlstPrcureTotList`.

Natural-language query to API mapping:

- product name or classification -> `prdctClsfcNoNm`, `dtilPrdctClsfcNoNm`, `prdctIdntNoNm`
- product identifier -> `prdctIdntNo`
- supplier/company -> `cntrctCorpNm`, `corpNm`, `bizno`
- certification/special status -> `prodctCertYn`, `exclcProdctYn`, `smetprCmptProdctYn`
- agency or demand institution -> `dminsttNm`, `dminsttCd`, `dminsttRgnNm`
- contract or delivery-request number -> `shopngCntrctNo`, `cntrctNo`, `dlvrReqNo`
- date window -> `inqryBgnDate`, `inqryEndDate`, `rgstDtBgnDt`, `rgstDtEndDt`, `chgDtBgnDt`, `chgDtEndDt`

## Expected usage

Expected usage is medium for UMMAYA. Most citizens will use it less often than jobs, welfare, health, or safety APIs, but procurement transparency and SME/vendor discovery can generate high-value multi-call sessions. One conversation may need a product-list call, a contract-specific detail call, and a procurement-history call. The development traffic of 1,000 calls per day per operation is enough for prototype wrapping and fixture capture.

## Application result

- Submitted through Computer Use on data.go.kr.
- My Page status after submission: `[승인] 조달청_종합쇼핑몰 품목정보 서비스`
- Application date: `2026-05-16`
- Expiry date: `2028-05-16`
- Application reference: `115978644`
- UDDI: `uddi:9c34f80a-feec-4485-8a25-dc8f751686b6_202410241405`
- Submitted purpose: `UMMAYA lookup adapter: procurement catalog and delivery lookup by product name, item ID, supplier, certification, agency, and date.`
