# Usage notes: 한국예탁결제원_금융용어조회서비스_GW

## Source files saved

- `data-go-kr-detail.html`: data.go.kr detail page saved from the portal
- `openapi-schemaorg.json`: data.go.kr schema.org metadata
- `dcat-metadata.rdf.xml`: data.go.kr DCAT metadata
- `swagger.json`: Swagger JSON extracted from the saved portal page
- `gateway_swagger_guide.pdf`: data.go.kr gateway Swagger guide

No API-specific reference document was available from the portal page. The `참고문서 다운로드` link rendered with an empty file identifier in the saved detail HTML.

## Base URL

The portal's embedded Swagger shows:

```text
https://apis.data.go.kr/B552481/FnTermSvc
http://apis.data.go.kr/B552481/FnTermSvc
```

## Operation

### `GET /getFinancialTermMeaning`

Summary: `금융용어사전 조회`

Use for citizen questions asking the official meaning of a securities, bond, disclosure, settlement, or financial-market term.

Request parameters:

- `serviceKey` required: data.go.kr API key
- `term` required: financial term name
- `pageNo` optional: page number
- `numOfRows` optional: number of rows per page

Important response fields:

- `header.resultCode`: result code
- `header.resultMsg`: result message
- `body.totalCount`: total number of matched terms
- `body.pageNo`: page number
- `body.numOfRows`: page size
- `body.items.item.fnceDictNm`: financial term name
- `body.items.item.ksdFnceDictDescContent`: term description, may include HTML tags

Documented error codes:

- `3`: `NODATA_ERROR(데이터 없음)`
- `10`: `INVALID_REQUEST_PARAMETER_ERROR(잘못된 요청 파라메터)`
- `11`: `NO_MANDATORY_REQUEST_PARAMETER_ERROR(필수요청 파라메터가 없음)`

## UMMAYA adapter behavior

Suggested adapter ID: `ksd_financial_term_lookup`.

The adapter should:

1. Extract one primary finance term from the user's question.
2. Ask a clarification only when multiple unrelated terms are present and the query cannot be answered cleanly in one call.
3. Call `/getFinancialTermMeaning` with the normalized `term`.
4. Preserve the official Korean term and definition, but sanitize HTML in `ksdFnceDictDescContent`.
5. Return a short plain-language explanation plus the official definition.
6. Use `resultCode`, `resultMsg`, and `totalCount` to distinguish no-result, malformed-query, and successful responses.
7. Fail closed for requests to trade, invest, open accounts, change holdings, file disclosures, or submit financial records; this API supports lookup only.

## Example UMMAYA response path

Citizen query: "대량주식 보유상황 공시제도라는 말이 무슨 뜻이야?"

Adapter flow:

1. Extract `대량주식 보유상황 공시제도` as `term`.
2. Call:

```text
GET https://apis.data.go.kr/B552481/FnTermSvc/getFinancialTermMeaning?serviceKey={serviceKey}&term=대량주식%20보유상황%20공시제도&pageNo=1&numOfRows=10
```

3. Parse `body.items.item.fnceDictNm` and `ksdFnceDictDescContent`.
4. Strip HTML tags from the official description.
5. Answer with the official definition, a short citizen-friendly paraphrase, and the data.go.kr source citation.

## Implementation notes

- Data format is XML only in the portal metadata, despite `consumes` containing `application/json` in Swagger.
- The license is non-commercial, so UMMAYA documentation and adapter metadata should carry the non-commercial constraint explicitly.
- Development traffic is 100 calls per day. Tests must use recorded fixtures and must not call the live endpoint from CI.
- The service is useful as a helper for other financial adapters because it can resolve official meanings before or after a transaction-specific lookup.
