# Data.go.kr Candidate Unit 01 - MOJ Village Lawyer Regional Status

## Reference Bootstrap

- UMMAYA thesis/docs: `docs/vision.md` frames UMMAYA as a citizen-facing national administrative and public-infrastructure execution surface, not a generic public-data collector. `docs/api/README.md` defines the active public-service primitive surface as `find`, `locate`, `send`, and `check`.
- Adapter/API sources: data.go.kr detail page saved as `data-go-kr-detail.html`; inline Swagger saved as `data-go-kr-inline-swagger.json`; general data.go.kr Swagger guide saved as `gateway_swagger_guide.pdf`.
- External primary source: `https://www.data.go.kr/data/15121954/openapi.do`.
- Implementation constraints: data.go.kr usage application was submitted through the portal UI and approved for development use on 2026-05-16. The endpoint exposes only pagination parameters, so a UMMAYA adapter must combine a `locate`/address-normalization step with client-side filtering over paged records.
- Unknowns or blocked evidence: the data.go.kr page's API-specific reference-document download handler is blank (`fn_fileDownload('', '')`), so no API-specific attachment was available from the page. Live contract probing requires `UMMAYA_DATA_GO_KR_API_KEY` and must be performed with direct `curl` before implementation.

## Candidate Summary

- Public data ID: `15121954`
- Title: `법무부_마을변호사 지역별 현황`
- Provider: Ministry of Justice (`법무부`)
- Category: `법률`
- Classification: `공공질서및안전 - 법무및검찰`
- Application status: submitted and approved for development use through data.go.kr on 2026-05-16; expiry shown as 2028-05-16 in the portal usage-application list.
- Candidate tool ID: `moj_village_lawyer_lookup`
- Primary primitive: `find`
- Supporting primitive: `locate` when the citizen provides a free-form address instead of province/city/village fields.
- Permission tier candidate: Tier 1 public data. The endpoint returns public program assignment records, not citizen-specific records. The adapter should still display the agency source and avoid implying legal advice.

## Why This Fits UMMAYA

This is not a general statistics dataset. It maps a citizen's place of residence to an official legal-aid access channel under the Ministry of Justice village-lawyer program. It supports UMMAYA's "citizen asks for an outcome, not a portal" thesis for legal-help discovery.

Representative citizen queries:

- `우리 동네 마을변호사 찾아줘.`
- `OO군 OO면에서 무료 법률상담 받을 수 있는 담당 변호사 알려줘.`
- `전세 문제 상담할 수 있는 지역 법률지원 창구를 찾아줘.`
- `주소 기준으로 담당 마을변호사와 읍면동 담당 공무원 정보를 정리해줘.`

Expected usage/frequency inference:

- Frequency: medium-low compared with weather, emergency, hospital, welfare, tax, utility, or transport adapters.
- Strategic value: medium. Legal help is a citizen-facing national service, especially for rural, island, small-city, and legal-service underserved areas.
- Adapter quality caveat: medium. The endpoint lacks location filter parameters and exposes only `serviceKey`, `pageNo`, and `numOfRows`; UMMAYA must normalize location and filter response records itself. This makes it acceptable as a coverage adapter, but it should not displace higher-frequency national-infrastructure APIs in the next 30-unit collection.

Screening result: pass with caveat. Keep as a secondary legal-access adapter candidate, not a top-priority high-frequency infrastructure adapter.

## Endpoint

- Gateway endpoint: `https://apis.data.go.kr/1270000/mojmabyun/mabyun`
- Provider/origin endpoint from Swagger metadata: `https://www.moj.go.kr/lawyerdataApi/mojmabyun`
- Method: `GET`
- Format: XML response
- Swagger operation ID: `mabyun`
- Operation description: `마을변호사 및 마을담당공무원의 지역별 배정현황의 상세사항을 조회`

Required query parameters:

| Name | Required | Type | Notes |
|---|---:|---|---|
| `serviceKey` | yes | string | data.go.kr service key |
| `pageNo` | yes | string | page number; default value in metadata is `1` |
| `numOfRows` | yes | string | rows per page; default value in metadata is `20` |

Response shape:

| Field | Meaning |
|---|---|
| `header.resultCode` | result code |
| `header.resultMsg` | result message |
| `body.items.item.State` | province/city |
| `body.items.item.City` | city/county/district |
| `body.items.item.Village` | eup/myeon/dong |
| `body.items.item.AreaNote` | area note |
| `body.items.item.CityPublicServan` | city/county/district public official; field name is misspelled in the official spec |
| `body.items.item.CityServDuty` | city/county/district public official duty |
| `body.items.item.VillagePublicServant` | eup/myeon/dong public official |
| `body.items.item.VillageServDuty` | eup/myeon/dong public official duty |
| `body.items.item.Attorney` | village lawyer |
| `body.items.item.AttorneyNote` | village lawyer note |
| `body.pageNo` | response page number |
| `body.numOfRows` | response rows per page |
| `body.totalCount` | total count |

Result codes documented in the inline Swagger:

| Code | Meaning |
|---|---|
| `0` | normal |
| `5` | no data |
| `200` | success |

## Proposed Adapter Behavior

Input model:

- `address`: optional citizen-provided free-form address.
- `state`: optional province/city value.
- `city`: optional city/county/district value.
- `village`: optional eup/myeon/dong value.
- `page_limit`: conservative internal page cap for fail-closed behavior.

Execution:

1. If `address` is present, call an existing `locate` adapter to derive province/city/village terms.
2. Call `GET /mabyun` with the data.go.kr key and paginated parameters.
3. Filter records by the normalized administrative fields.
4. Return matching attorney, local official, and area notes with source URL and timestamp.
5. If no record matches, return a structured zero-result response and cite the official program scope caveat from the page description.

Non-goals:

- Do not present the response as legal advice.
- Do not submit a counseling request; this API is lookup-only.
- Do not infer eligibility or appointment availability beyond what the official response contains.

## Future Selection Gate

Before submitting future data.go.kr usage applications, the candidate must pass this gate:

1. Citizen intent: at least three natural citizen queries can be answered by the API without requiring the citizen to know the agency or portal.
2. Infrastructure fit: the provider is a national, local-government, public corporation, or regulated public-service infrastructure source.
3. Actionability: the result helps the citizen decide, locate, verify, submit, pay, or proceed with an official service step.
4. Primitive fit: the API maps cleanly to one of `find`, `locate`, `send`, or `check`.
5. Parameter quality: the endpoint has meaningful filters, or the dataset is small and official enough that UMMAYA-side filtering is still defensible.
6. Frequency or strategic value: expected citizen usage is at least medium, or the API fills an important national-infrastructure gap such as safety, welfare, legal aid, housing, labor, health, education, immigration, identity, payments, or utilities.
7. Non-duplication: it is not already covered by an active UMMAYA adapter unless it provides a better official source or missing region/domain coverage.

Hard reject examples: annual statistics, PR/media content, dashboards without citizen actionability, datasets with only pagination and no practical filtering unless they support a clear public-service lookup, duplicate agency mirrors, and opaque channels with no callable shape.
