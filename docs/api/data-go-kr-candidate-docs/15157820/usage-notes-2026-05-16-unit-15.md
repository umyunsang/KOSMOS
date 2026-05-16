# Unit 15 Usage Notes

- API: `중소벤처기업부_중소기업 지원사업 공고 조회 서비스`
- Candidate ID: `15157820`
- Portal URL: `https://www.data.go.kr/data/15157820/openapi.do`
- Submitted status: approved on `2026-05-16`
- Application reference: `115979411`
- UDDI: `uddi:9b643802-810b-453c-ad7b-81bbace31ff3_202603261059`
- Expiry: `2028-05-16`

## Endpoint

```text
GET https://apis.data.go.kr/1421000/bizinfo/pblancBsnsService
```

## Query Parameters

| Name | Required | Description |
| --- | --- | --- |
| `serviceKey` | yes | Public Data Portal API key |
| `dataType` | no | Response format |
| `pageNo` | no | Page number |
| `numOfRows` | no | Rows per page |
| `searchLclasId` | no | Support field filter |
| `hashtags` | no | Hashtag filter |
| `pblancId` | no | Notice identifier |
| `registDe` | no | Notice registration date |
| `updtPnttm` | no | Notice update timestamp/date |

## Response Fields

| Field | Meaning |
| --- | --- |
| `pblancNm` | Notice title |
| `pblancUrl` | Business support portal notice URL |
| `pblancId` | Notice ID |
| `jrsdInsttNm` | Jurisdiction agency |
| `excInsttNm` | Executing agency |
| `bsnsSumryCn` | Business support summary |
| `pldirSportRealmLclasCodeNm` | Policy directory support-field large category |
| `creatPnttm` | Created timestamp |
| `reqstBeginEndDe` | Application period |
| `updtPnttm` | Updated timestamp |
| `trgetNm` | Target beneficiaries |
| `inqireCo` | View count |
| `flpthNm` | Attachment path |
| `fileNm` | Attachment file name |
| `printFlpthNm` | Printable body path |
| `printFileNm` | Printable body file name |
| `hashtags` | Hashtags |
| `reqstMthPapersCn` | Application method and documents |
| `refrncNm` | Contact/inquiry information |
| `rceptEngnHmpgUrl` | Application URL |

## Wrapping Logic

For UMMAYA, expose this as a `lookup` adapter that translates citizen queries into filters:

- Business domain or support area -> `searchLclasId` when a known support-field code is available; otherwise use `hashtags` and response-side filtering.
- Hashtag-style queries such as `소상공인`, `창업`, `수출`, `기술개발` -> `hashtags`.
- Specific notice lookup -> `pblancId`.
- Freshness queries -> `registDe` or `updtPnttm`.
- Pagination -> `pageNo`, `numOfRows`.

The adapter should return a concise notice list with title, target, agency, application period, application URL, inquiry contact, and source URL. It should not rewrite official eligibility text as a final determination; use the API fields as cited evidence and mark ambiguous eligibility as requiring agency notice review.

## Example Query Shape

```text
GET /pblancBsnsService?serviceKey={DATA_GO_KR_KEY}&dataType=json&pageNo=1&numOfRows=10&hashtags=소상공인
```

## Saved Artifacts

- `data-go-kr-detail.html`
- `openapi-schemaorg.json`
- `dcat-metadata.rdf.xml`
- `swagger.json`
- `gateway_swagger_guide.pdf`
