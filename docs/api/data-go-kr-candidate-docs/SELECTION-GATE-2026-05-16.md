# Data.go.kr Candidate Selection Gate

This gate applies before submitting any additional data.go.kr usage application for UMMAYA adapter discovery.

UMMAYA is not a generic public-data crawler. Per `docs/vision.md`, the target is citizen-facing national administrative and public-infrastructure AX: a citizen asks for an outcome, and the harness routes through official channels. A data.go.kr API is eligible only when it can become a useful adapter behind the `find`, `locate`, `send`, or `check` primitive surface documented in `docs/api/README.md`.

## Submit Only If The Candidate Passes

1. Query-to-response reasoning: write at least three concrete Korean citizen natural-language queries, then map each query to the exact API operation, required parameters, response fields, and UMMAYA response. If this table cannot be written convincingly, do not apply.
2. Citizen intent: the queries can be answered without requiring the citizen to know the agency, portal, or dataset name.
3. Infrastructure fit: the provider is a national ministry, local government, public corporation, or regulated public-service infrastructure source.
4. Actionability: the result helps a citizen decide, locate, verify, submit, pay, receive a public-service handoff, or proceed with an official service step.
5. Primitive fit: the API maps cleanly to one of `find`, `locate`, `send`, or `check`; composite flows are allowed only when one primitive remains the primary adapter role.
6. Parameter quality: the endpoint has meaningful filters such as location, date, facility, ID, service type, eligibility category, or status. Pagination-only APIs are accepted only when the official dataset is small and clearly supports a high-value citizen lookup after UMMAYA-side filtering.
7. Frequency or strategic value: expected citizen demand is at least medium, or the API fills an important national-infrastructure gap such as safety, welfare, legal aid, housing, labor, health, education, immigration, identity, payments, utilities, transport, taxes, or civil affairs.
8. Non-duplication: the API is not already covered by an active UMMAYA adapter unless it provides a more authoritative source, better regional coverage, or missing fields for a known citizen scenario.

## Required Pre-Application Reasoning Table

Before clicking the final data.go.kr application button, save a table in the unit notes:

| Citizen query | UMMAYA interpretation | API operation and parameters | Official fields returned | Citizen-facing answer |
|---|---|---|---|---|
| Korean natural-language request | Intent, entity, location, date, and required primitive | Endpoint, method, required params, and any preceding lookup step | Only fields documented by the agency/API | What UMMAYA can honestly answer, plus limits |

This table is the screening proof. High-level statements such as "it is safety-related" or "it has many applications" are insufficient.

## Hard Reject

- Annual statistics, dashboards, media, promotional material, or aggregate-only datasets with no citizen-level actionability.
- APIs whose results cannot answer a citizen query more usefully than a web search.
- Duplicate mirrors of an already cataloged UMMAYA adapter without stronger authority or coverage.
- Opaque channels with no callable shape or no documented request/response contract.
- Personal-data or transaction APIs without an official permission or authentication policy citation.
- Pagination-only APIs unless the post-filtered result is a defensible citizen-facing service lookup.

## Unit Record Requirement

Every accepted unit must save:

- Application status and portal evidence.
- Saved official detail page, Swagger/OpenAPI, and any available reference document.
- Endpoint, method, required parameters, response fields, and result codes.
- Candidate tool ID, primitive mapping, permission-tier hypothesis, and rejection caveats.
- Citizen query examples and rough demand/usage inference.
