# Unit 10 Usage Notes: MFDS Easy Drug Information

Reference bootstrap:
- UMMAYA thesis/docs: `docs/vision.md`, `docs/requirements/ummaya-migration-tree.md`, `docs/api/README.md`.
- CC restored-src files: not edited; this is an intake record for a future `GovAPITool` adapter.
- Adapter/API sources: data.go.kr detail page, Schema.org JSON, DCAT RDF/XML, MFDS DOCX service guide.
- External primary sources: official data.go.kr application and downloaded MFDS service specification.
- Implementation constraints: no live API contract test in CI; use direct `curl` with a real service key only during live validation, with secrets redacted.

## Candidate

- Portal id: `15075057`
- API title: `식품의약품안전처_의약품개요정보(e약은요)`
- Provider: `식품의약품안전처`
- Classification: `보건 - 식품의약안전`
- Service type: REST
- Data format: JSON+XML
- License: `이용허락범위 제한 없음`
- Approval model: development auto-approval; operation review/approval
- Portal URL: `https://www.data.go.kr/data/15075057/openapi.do`
- UMMAYA candidate adapter id: `mfds_easy_drug_info_lookup`
- UMMAYA primitive: `lookup`
- Expected demand: high. Medication efficacy, dosing instructions, warnings, food/drug interaction, side-effect, storage, and pill-image questions are common citizen queries.

## Application Evidence

- Status shown in My Page: `[승인] 식품의약품안전처_의약품개요정보(e약은요)`
- Application date: `2026-05-16`
- Expiry date: `2028-05-16`
- Application reference: `115977335`
- UDDI: `uddi:411d4234-22dd-41ab-a40d-b0866cae3fe2`
- Submitted purpose: UMMAYA R&D citizen medication information lookup adapter using official MFDS eYak data; no diagnosis or resale.

## Endpoint

- Base URL: `http://apis.data.go.kr/1471000/DrbEasyDrugInfoService`
- Operation: `getDrbEasyDrugList`
- Request URL: `http://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList`

## Request Parameters

| Name | Required | Description |
| --- | --- | --- |
| `ServiceKey` | yes | data.go.kr service key. Use URL-encoded key for query string calls. |
| `pageNo` | no | Page number. |
| `numOfRows` | no | Rows per page. |
| `entpName` | no | Company/manufacturer name. |
| `itemName` | no | Drug product name. |
| `itemSeq` | no | Product standard/item sequence code. |
| `efcyQesitm` | no | Efficacy question text filter. |
| `useMethodQesitm` | no | Usage method question text filter. |
| `atpnWarnQesitm` | no | Mandatory pre-use warning question text filter. |
| `atpnQesitm` | no | Precaution question text filter. |
| `intrcQesitm` | no | Drug/food interaction question text filter. |
| `seQesitm` | no | Side effect question text filter. |
| `depositMethodQesitm` | no | Storage method question text filter. |
| `openDe` | no | Open/publication date. |
| `updateDe` | no | Update date. |
| `type` | no | Response format, `xml` or `json`; default is `xml`. |

Specification caveat: the downloaded DOCX sample URL contains `trustEntpName`, while the portal request table lists `entpName`. Prefer the portal table for adapter schema until a direct live `curl` probe proves the accepted alias behavior.

## Response Fields

- Envelope: `resultCode`, `resultMsg`, `numOfRows`, `pageNo`, `totalCount`
- Item fields: `entpName`, `itemName`, `itemSeq`, `efcyQesitm`, `useMethodQesitm`, `atpnWarnQesitm`, `atpnQesitm`, `intrcQesitm`, `seQesitm`, `depositMethodQesitm`, `openDe`, `updateDe`, `itemImage`

## Natural-Language Fit

- Citizen query: "타이레놀 효능, 복용법, 부작용 알려줘."
  - Adapter behavior: call `getDrbEasyDrugList` with `itemName=타이레놀`, `type=json`, then summarize `efcyQesitm`, `useMethodQesitm`, and `seQesitm` with official-source citation.
- Citizen query: "이 약 먹기 전에 피해야 할 음식이나 같이 먹으면 안 되는 약이 있어?"
  - Adapter behavior: search by `itemName` or `itemSeq`, then answer from `atpnWarnQesitm`, `atpnQesitm`, and `intrcQesitm`.
- Citizen query: "약 사진이랑 보관 방법도 확인해줘."
  - Adapter behavior: return `itemImage` and `depositMethodQesitm` when available.

## Wrapping Notes

- Use this as an official medication-information lookup tool, not as diagnosis, treatment recommendation, prescription substitution, or emergency medical triage.
- Fail closed when no exact drug match is found; ask for product name, manufacturer, or item sequence code instead of guessing.
- Keep response language citizen-friendly but preserve official warning wording where it affects safety.
- Redact service keys from all fixtures and logs.

## Saved Artifacts

- `data-go-kr-detail.html`
- `openapi-schemaorg.json`
- `dcat-metadata.rdf.xml`
- `gateway_swagger_guide.pdf`
- `IROS_239_의약품개요정보(e약은요)_서비스_v1.0.docx`
- `IROS_239_의약품개요정보(e약은요)_서비스_v1.0.docx.txt`
- `pre-application-screening-2026-05-16-unit-10.md`
