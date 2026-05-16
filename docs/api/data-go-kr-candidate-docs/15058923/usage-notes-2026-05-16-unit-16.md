# Unit 16 Usage Notes

- API: `축산물품질평가원_축산물통합이력정보`
- Candidate ID: `15058923`
- Portal URL: `https://www.data.go.kr/data/15058923/openapi.do`
- Submitted status: approved on `2026-05-16`
- Application reference: `115979896`
- UDDI: `uddi:cb29ffb9-c219-45e3-ac48-a28f87f26ef2_202601281033`
- Expiry: `2028-05-16`

## Endpoint

```text
GET http://data.ekape.or.kr/openapi-data/service/user/animalTrace/traceNoSearch
```

## Query Parameters

| Name | Required | Description |
| --- | --- | --- |
| `traceNo` | yes | Livestock individual, trace, history, or bundle number. Portal sample: `L01709271277007`. |
| `serviceKey` | yes | Public Data Portal API key. The DOCX examples show `ServiceKey`; confirm accepted casing with direct curl before live adapter implementation. |
| `optionNo` | no | Information section selector. `1` individual/raising, `2` birth/reporting, `3` slaughter, `4` packaging, `5` FMD vaccine, `6` disease, `7` brucellosis, `8` bundle basic info, `9` bundle composition. |
| `corpNo` | no | Business registration number of the company that composed the bundle. Portal sample: `1178522046`. |

## Response Fields

| Field | Meaning |
| --- | --- |
| `resultCode` | API result code |
| `resultMsg` | API result message |
| `traceNoType` | Trace-number type, e.g. cattle individual, cattle bundle, pig trace, pig bundle, poultry/duck/egg history |
| `infoType` | Returned information section |
| `birthYmd` | Birth date |
| `farmAddr` | Farm address |
| `farmNo` | Farm number |
| `farmUniqueNo` | Farm unique number |
| `farmerNm` | Farmer or owner name |
| `mngrNm` | Farm manager name |
| `cattleNo` | Cattle individual number |
| `pigNo` | Pig trace number |
| `histNo` | Poultry, duck, or egg history number |
| `lotNo` | Bundle number |
| `lsTypeNm` | Livestock type |
| `sexNm` | Sex |
| `butcheryPlaceNm` | Slaughterhouse name |
| `butcheryPlaceAddr` | Slaughterhouse address |
| `butcheryYmd` | Slaughter date |
| `gradeNm` | Grade |
| `inspectPassYn` | Inspection result |
| `processPlaceNm` | Packaging/processing company name |
| `processPlaceAddr` | Packaging/processing company address |
| `processYmd` | Packaging/processing date |
| `corpNo` | Business registration number |

## Wrapping Logic

For UMMAYA, expose this as a `lookup` adapter with a `verify`-oriented response mode:

- Extract a user-provided livestock trace number or bundle number into `traceNo`.
- Infer `optionNo` from the question when possible: slaughter/grade questions -> `3`, packaging/company questions -> `4`, bundle composition -> `9`, bundle summary -> `8`.
- Include `corpNo` only when the user provides a bundle company business number or when the query explicitly asks for bundle composition requiring that field.
- Return official provenance facts, not a safety guarantee: summarize trace type, farm, slaughterhouse, slaughter date, inspection result, grade, processing company, packaging date, and source endpoint.
- For ambiguous trace numbers, return the raw trace type and evidence fields and ask for a more specific option only when the official response cannot disambiguate.

## Example Query Shapes

```text
GET /openapi-data/service/user/animalTrace/traceNoSearch?serviceKey={DATA_GO_KR_KEY}&traceNo=L01709271277007&optionNo=9&corpNo=1178522046
```

```text
GET /openapi-data/service/user/animalTrace/traceNoSearch?serviceKey={DATA_GO_KR_KEY}&traceNo=170003000058&optionNo=3
```

## Saved Artifacts

- `data-go-kr-detail.html`
- `openapi-schemaorg.json`
- `dcat-metadata-download-error.html` (portal returned a public-data error page instead of RDF)
- `gateway_swagger_guide.pdf`
- `축산물품질평가원_OpenAPI활용가이드_축산물통합이력정보조회_v2.10.docx`
- `official-contract-summary.json`

The data.go.kr detail page contains an empty embedded `swaggerJson`, so no API-specific `swagger.json` was saved for this unit.
