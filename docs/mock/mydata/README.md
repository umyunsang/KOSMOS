# Mock: mydata

**Mirror axis**: shape
**Source reference**: KFTC 마이데이터 표준 API v2.0 (2024-09-30 기준) — https://www.mydatacenter.or.kr (금융보안원 마이데이터 지원센터)
**License**: Public standard (KFTC / FSS regulatory publication); KOSMOS mock is an independent re-implementation
**Scope**: Reproduces the request/response shape for the KFTC MyData standard API v2.0 (revision date 2024-09-30) used for financial data aggregation, covering the OAuth 2.0 consent flow shape and the account/transaction data retrieval shape; does not reproduce the mTLS handshake or the KFTC inter-operator routing layer.

## What this mock reproduces

- OAuth 2.0 Authorization Code flow endpoints per MyData API v2.0 §4: `/oauth/2.0/authorize`, `/oauth/2.0/token`, `/oauth/2.0/revoke`
- Consent resource: `POST /v2/consents` and `GET /v2/consents/{consentId}` — field names `consentId`, `orgCode`, `accountList`, `validUntil`, `consentStatus`
- Account list endpoint: `GET /v2/accounts` — `bankList[].accountNum`, `accountType`, `prodName`, `isConsent`
- Transaction list endpoint: `GET /v2/bank/accounts/{accountNum}/transactions` — `transList[].transDtime`, `transType`, `transAmt`, `transBal`, `transRemark`
- Error envelope: `{ rsp_code, rsp_msg }` (MyData standard error format)
- Pagination: `next_page` cursor and `is_last` boolean per MyData API §5.3

## What this mock deliberately does NOT reproduce

- Mutual TLS (mTLS) client certificate verification — the mock accepts plain TLS connections; real MyData operators require a KFTC-issued client certificate
- OAuth 2.0 PKCE challenge binding — the mock issues tokens without validating `code_verifier`
- KFTC inter-operator routing (e.g., the ISP's internal transmission layer) — the mock exposes endpoints directly without the routing envelope
- Real financial data — all transaction amounts and balances are synthetic fixtures
- `orgCode` validation against the KFTC operator registry — the mock accepts any non-empty `orgCode`

## Fixture recording approach

Because MyData sandbox access requires KFTC operator certification, fixtures are hand-authored based on the KFTC MyData standard API specification document (v2.0, 2024-09-30). Each fixture file is tagged with `spec_version: "v2.0-20240930"` in `tests/fixtures/mydata/meta.json`.

To update fixtures when a new spec version is published:
1. Download the updated specification PDF from https://www.mydatacenter.or.kr.
2. Review changed endpoint schemas in §4 and §5.
3. Update fixture JSON files and increment `spec_version` in `meta.json`.
4. Open a PR with label `mock-drift`.

## Upstream divergence policy

KFTC publishes numbered revisions of the MyData API standard. The `spec_version` in `tests/fixtures/mydata/meta.json` is the canonical revision marker. KOSMOS CI does not automatically detect standard updates — the engineering team must monitor KFTC release notices at mydatacenter.or.kr. When the spec version changes, treat it as a `mock-drift` event and review all affected endpoint shapes.
