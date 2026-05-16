# Usage notes: 조달청_종합쇼핑몰 품목정보 서비스

## Source files saved

- `data-go-kr-detail.html`: data.go.kr detail page saved from the portal
- `openapi-schemaorg.json`: data.go.kr schema.org metadata
- `dcat-metadata.rdf.xml`: data.go.kr DCAT metadata
- `swagger.json`: Swagger JSON extracted from the saved portal page
- `gateway_swagger_guide.pdf`: data.go.kr gateway Swagger guide
- `조달청_OpenAPI참고자료_나라장터_종합쇼핑몰품목정보서비스_1.0.docx`: downloaded API reference document
- `조달청_OpenAPI참고자료_나라장터_종합쇼핑몰품목정보서비스_1.0.docx.txt`: extracted DOCX text for local search

## Base URL

The portal's embedded Swagger shows:

```text
https://apis.data.go.kr/1230000/at/ShoppingMallPrdctInfoService
http://apis.data.go.kr/1230000/at/ShoppingMallPrdctInfoService
```

The downloaded DOCX examples use:

```text
http://apis.data.go.kr/1230000/at/ShoppingMallPrdctInfoService05
```

For a UMMAYA live adapter, prefer the data.go.kr portal Swagger gateway base until a direct credentialed curl probe proves whether the `Service05` suffix is required for all operations, specific operation generations, or only legacy examples.

## Operations

### `GET /getShoppingMallPrdctInfoList`

Summary: `종합쇼핑몰 품목 등록 내역 조회`

Use for broad product/catalog questions such as product name, item identifier, supplier, certification, MAS status, and contract period.

Key request parameters:

- `serviceKey` required: data.go.kr API key
- `pageNo` required
- `numOfRows` required
- `inqryDiv` required in the portal contract for many shopping/procurement queries
- `type` optional: response format selector where supported
- `inqryBgnDate`, `inqryEndDate` optional: query date range
- `prdctClsfcNoNm`, `dtilPrdctClsfcNoNm`, `prdctIdntNoNm`, `prdctIdntNo` optional: product-name/classification/identifier filters
- `shopngCntrctNo` optional: shopping contract number
- `exclcProdctYn`, `prodctCertYn`, `masYn`, `regtCncelYn` optional: product status/certification filters

Important response fields:

- `rgstDt`, `shopngCntrctNo`, `shopngCntrctSno`
- `cntrctCorpBizno`, `cntrctCorpNm`, `entrprsDivNm`
- `cntrctMthdNm`, `cntrctPrceAmt`, `cntrctDate`, `cntrctBgnDate`, `cntrctEndDate`
- `prdctClsfcNo`, `prdctClsfcNoNm`, `dtilPrdctClsfcNo`, `dtilPrdctClsfcNoNm`, `prdctIdntNo`
- `prdctSpecNm`, `prdctUnit`, `prdctMakrNm`, `prdctImgUrl`
- `exclncPrcrmntPrdctYn`, `masYn`, `smetprCmptProdctYn`, `prodctCertList`
- `prdctDlvrPlceNm`, `prdctDlvryCndtnNm`, `dlvrTmlmtDaynum`, `prdctSplyRgnNm`

### Contract product endpoints

Operations:

- `GET /getMASCntrctPrdctInfoList`: `다수공급자계약 품목정보`
- `GET /getUcntrctPrdctInfoList`: `일반단가계약 품목정보`
- `GET /getThptyUcntrctPrdctInfoList`: `제3자단가계약 품목정보`

Use when a citizen asks for product information under a specific contract type or when the adapter can infer that the question is about MAS, general unit-price contracts, or third-party unit-price contracts.

Common request parameters:

- `serviceKey` required
- `pageNo`, `numOfRows` required
- `rgstDtBgnDt`, `rgstDtEndDt` optional: registration date range
- `chgDtBgnDt`, `chgDtEndDt` optional: change date range
- `prdctClsfcNoNm`, `prdctIdntNo` optional
- `cntrctCorpNm` optional
- `type` optional where supported

Important response fields:

- supplier/contract fields such as `cntrctCorpNm`, `cntrctDeptNm`, `cntrctDeptTelNo`, `cntrctOfclNm`, `cntrctOfclEmail`
- product fields such as `prdctClsfcNo`, `prdctClsfcNoNm`, `prdctIdntNo`, `prdctSpecNm`, `prdctUnit`, `prdctMakrNm`
- delivery and supply fields such as `splyJrsdctRgnNm`, `splyTmlmtCntnts`, `avrgDlvyTime`
- certification and quality fields such as `qltyRltnCertInfo`, `prefrpurchsObjCertNm`, `dutyPurchsObjCertNm`, `qltyMngmtPrgnCorpYn`
- contract dates such as `cntrctDate`, `cntrctBgnDate`, `cntrctEndDate`

### `GET /getDlvrReqInfoList`

Summary: `종합쇼핑몰 납품요구정보 현황 목록조회`

Use for delivery-request searches by receipt date, delivery-request number, contract number, demand institution, region, supplier, or representative product.

Key request parameters:

- `serviceKey` required
- `pageNo`, `numOfRows` required
- `inqryDiv`, `inqryBgnDate`, `inqryEndDate` commonly required for date-window queries
- `dlvrReqNo`, `cntrctNo` optional
- `dminsttCd`, `dminsttNm`, `dminsttRgnNm` optional
- `corpNm` optional

Important response fields:

- `dlvrReqNo`, `dlvrReqNm`, `dlvrReqRcptDate`, `dlvrReqQty`, `dlvrReqAmt`, `dlvrReqIncdecQty`
- `dminsttCd`, `dminsttNm`, `dmndInsttDivNm`, `dminsttRgnNm`
- `corpNm`, `cntrctNo`, `cntrctCnclsStleNm`
- `rprsntPrdctClsfcNo`, `rprsntPrdctClsfcNoNm`
- `maxDlvrTmlmtDate`, `fnlDlvrReqYn`, `masYn`, `exclcProdctYn`

### `GET /getDlvrReqDtlInfoList`

Summary: `종합쇼핑몰 납품요구상세 현황 목록조회`

Use after `/getDlvrReqInfoList` when the citizen wants item-level detail for a delivery request.

Key request parameters:

- `serviceKey` required
- `pageNo`, `numOfRows` required
- `inqryDiv`, `inqryBgnDate`, `inqryEndDate` commonly required
- `dlvrReqNo`, `cntrctNo` optional
- product-name/classification filters optional depending on the query

Important response fields:

- delivery-request identifiers and dates
- item classification, detailed product name, item identifier, quantity, unit price, amount
- demand institution and supplier fields

### `GET /getSpcifyPrdlstPrcureInfoList`

Summary: `특정품목조달내역 목록 조회`

Use for procurement-history questions such as "which agencies bought this item?" or "show procurement records for this product class."

Key request parameters:

- `serviceKey` required
- `pageNo`, `numOfRows` required
- `inqryDiv`, `inqryBgnDate`, `inqryEndDate` required for the main search window
- `inqryPrdctDiv`, `prdctClsfcNo`, `dtilPrdctClsfcNo`, `prdctIdntNo` optional
- `prdctClsfcNoNm`, `dtilPrdctClsfcNoNm`, `prdctIdntNoNm` optional
- `dminsttCd`, `dminsttNm`, `dminsttRgnNm` optional
- `bizno`, `corpNm` optional
- `exclcProdctYn`, `cnstwkMtrlDrctPurchsObjYn`, `prcrmntDiv` optional

Important response fields:

- `prdctClsfcNo`, `dtilPrdctClsfcNoNm`, `prdctIdntNoNm`
- `prcrmntDivNm`, `cntrctDivNm`, `cntrctDlvrDivNm`, `cntrctMthdNm`
- `cntrctDlvrReqDate`, `cntrctDlvrReqNo`, `cntrctDlvrReqNm`
- `dminsttCd`, `dminsttNm`, `dmndInsttDivNm`, `dminsttRgnNm`
- `bizno`, `corpNm`
- `prdctUprc`, `prdctQty`, `prdctUnit`, `prdctAmt`
- `exclcProdctYn`, `cnstwkMtrlDrctPurchsObjYn`, `masYn`, `masCntrct2StepYn`

### `GET /getSpcifyPrdlstPrcureTotList`

Summary: `특정품목조달집계 목록 조회`

Use for aggregate questions over a product or product class, such as "how much was bought in this period?" or "summarize procurement volume by institution/region."

Key request parameters follow `/getSpcifyPrdlstPrcureInfoList`, with focus on date window and product/demand-institution filters.

### `GET /getVntrPrdctOrderDealDtlsInfoList`

Summary: `벤처나라 물품 주문거래 내역 조회`

Use for queries about Venture Nara product order/deal details, especially startup/venture-company public procurement activity.

## UMMAYA adapter behavior

Suggested adapter ID: `pps_shopping_mall_product_lookup`.

The adapter should:

1. Classify the user's procurement question into catalog, delivery-request, item-detail, procurement-history, aggregate-history, or Venture Nara lookup.
2. Normalize product and institution terms into the relevant classification/name/id fields.
3. Prefer product identifier fields when the user gives an official code; otherwise use product-name/classification search.
4. Return concise product cards with supplier, contract price, contract period, certification flags, delivery deadline, and product identifier.
5. Use `/getDlvrReqInfoList` then `/getDlvrReqDtlInfoList` for institution spending and delivery-request questions.
6. Use procurement-history endpoints for public-transparency summaries, including agency, region, quantity, unit price, and amount.
7. Fail closed when the user asks to purchase, bid, submit, or modify procurement records; this API supports lookup only.

## Example UMMAYA response path

Citizen query: "최근 1년 동안 부산 지역 공공기관이 구매한 사무용 의자 조달 내역을 요약해줘."

Adapter flow:

1. Map "사무용 의자" to `prdctClsfcNoNm` or `prdctIdntNoNm`.
2. Set `dminsttRgnNm` to Busan if accepted by the upstream field format.
3. Set `inqryBgnDate` and `inqryEndDate` to the last-year range.
4. Call `/getSpcifyPrdlstPrcureInfoList` for detailed records.
5. If the user asks for totals, call `/getSpcifyPrdlstPrcureTotList`.
6. Summarize agencies, suppliers, quantities, unit prices, and total amounts with source-record identifiers.
