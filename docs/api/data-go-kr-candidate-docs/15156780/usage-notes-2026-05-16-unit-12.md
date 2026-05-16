# Usage notes: 인사혁신처_공공취업정보 조회 서비스

## Source files saved

- `data-go-kr-detail.html`: data.go.kr detail page saved from the portal
- `openapi-schemaorg.json`: data.go.kr schema.org metadata
- `dcat-metadata.rdf.xml`: data.go.kr DCAT metadata
- `swagger.json`: Swagger JSON extracted from the saved portal page
- `gateway_swagger_guide.pdf`: data.go.kr gateway Swagger guide

The portal page exposes the API contract through embedded Swagger. The reference-document download link had empty attachment identifiers in the saved HTML, so no separate API-specific attachment could be downloaded.

## Base URL

```text
https://apis.data.go.kr/1760000/PblJobService
http://apis.data.go.kr/1760000/PblJobService
```

The embedded operation metadata also lists the original upstream URL shape:

```text
http://openapi.mpm.go.kr/openapi/service/PblJobService/{operation}
```

For a UMMAYA live adapter, prefer the data.go.kr gateway base URL from Swagger and keep the upstream URL only as source-contract context.

## Operations

### `GET /getList`

Summary: `공공취업정보 목록조회`

Use for broad citizen queries such as agency, public-sector category, keyword, and posting date.

Request parameters:

- `serviceKey` required: data.go.kr API key
- `pageNo` optional: page number, sample/default `1`
- `numOfRows` optional: rows per page, sample/default `10`
- `Pblanc_ty` required: notice type, examples include `e01` public competitive hiring, `e02` career/special hiring, `e03` contract role, `e04` administrative support, `e06` public recruitment
- `Instt_se` required: institution class, examples include all/empty, `g01` national civil service, `g02` local civil service, `g03` public institution, `g04` education office
- `Instt_nm` optional: institution-name search term
- `Begin_de` optional: registration-date start, `yyyy-mm-dd`
- `End_de` optional: registration-date end, `yyyy-mm-dd`
- `Kwrd` optional: keyword search term
- `Sort_order` required: sort order

Important response fields:

- `header.resultCode`, `header.resultMsg`
- `body.totalCount`, `body.numOfRows`, `body.pageNo`
- `body.items.item.idx`: public-job notice identifier
- `body.items.item.title`: notice title
- `body.items.item.insttname`: institution name
- `body.items.item.regdate`, `body.items.item.moddate`, `body.items.item.enddate`
- `body.items.item.type01`, `body.items.item.type02`
- `body.items.item.areacode`
- `body.items.item.readnum`

### `GET /getItem`

Summary: `공공취업정보 상세조회`

Use after `/getList` when the citizen chooses one notice.

Request parameters:

- `serviceKey` required
- `idx` required: public-job notice identifier

Important response fields:

- `idx`, `title`, `type01`, `type02`
- `contents`
- `link01`, `link02`, `link03`

### `GET /getClsfList`

Summary: `채용직급 목록조회`

Request parameters:

- `serviceKey` required
- `pageNo` optional
- `numOfRows` optional
- `Clsf_nm` optional: grade/class search term

Important response fields:

- `code`, `codename`, `codefullname`

### `GET /getItemPosition`

Summary: `채용직급 조회`

Request parameters:

- `serviceKey` required
- `idx` required

Use for enriching a notice with hiring grade/class and headcount information.

### `GET /getItemFile`

Summary: `파일 목록 조회`

Request parameters:

- `serviceKey` required
- `pageNo` optional
- `numOfRows` optional
- `idx` required

Important response fields:

- `filename`, `filepath`, `filesize`
- `parentidx`, `idx`, `sort`

### `GET /getInsttList`

Summary: `채용기관 목록조회`

Request parameters:

- `serviceKey` required
- `pageNo` required
- `numOfRows` required
- `Instt_nm` optional

Use for resolving a citizen's institution name before querying `/getList`.

## UMMAYA adapter behavior

Suggested adapter ID: `mpm_public_job_lookup`.

The adapter should:

1. Resolve agency/institution names with `/getInsttList` when the user gives a fuzzy agency phrase.
2. Query `/getList` with normalized category, keyword, and date filters.
3. Present concise notices with title, institution, registration date, deadline, notice type, and `idx`.
4. Call `/getItem` for the selected notice.
5. Optionally call `/getItemPosition` and `/getItemFile` to return hiring class, headcount, and attachment links.
6. Fail closed when required enum-like parameters cannot be mapped with enough confidence; ask a follow-up instead of guessing a hiring class.

## Example UMMAYA response path

Citizen query: "이번 주 마감하는 공공기관 채용공고 찾아줘."

Adapter flow:

1. Set `Instt_se=g03` for public institutions.
2. Set `End_de` to the current week end and `Sort_order` to latest or deadline-first after contract validation.
3. Call `/getList`.
4. Return top notices with deadline and institution.
5. If the user chooses one notice, call `/getItem`, `/getItemPosition`, and `/getItemFile`.
