# Mock: barocert

**Mirror axis**: shape
**Source reference**: https://developers.barocert.com (PASS 바로서트 개발자 포털)
**License**: Proprietary SDK with public documentation; KOSMOS mock is an independent re-implementation based solely on the publicly documented API shape — not a derivative of the SDK source
**Scope**: Reproduces the request/response shape for the PASS 바로서트 identity verification and electronic signature APIs as documented at developers.barocert.com; does not reproduce the actual OTP/biometric challenge-response protocol executed on the end-user's device.

## What this mock reproduces

- REST endpoint paths and HTTP methods as published in the PASS API docs (e.g., `POST /v1/kastnet/certify`, `POST /v1/kastnet/sign`)
- Request field names and types: `clientCode`, `token`, `receiverNum`, `reqTitle`, `callCenterNum`, `expireIn`, `userAgreementYN`, `subClientCode` per the published SDK reference
- Response field names and types: `receiptID`, `state` (integer enum: 0=pending, 1=success, 2=fail), `signedData`, `ci`
- Error response shape: `{ code: <integer>, message: <string> }` (Barocert standard error envelope)
- Polling flow: `POST /v1/kastnet/certify/status` with `receiptID` returning `state` transitions

## What this mock deliberately does NOT reproduce

- Actual PASS app push notification delivery — the mock immediately returns `state: 1` for happy-path fixtures
- Device biometric verification — out of scope; KOSMOS only consumes the `signedData` result
- `signedData` cryptographic validity — fixture `signedData` values are Base64-encoded placeholders, not real CMS SignedData objects
- Production API key validation (`clientCode` and HMAC signing of requests) — the mock accepts any non-empty `clientCode`

## Fixture recording approach

Because Barocert does not offer a public sandbox, fixtures are hand-authored based on the documented response schemas at developers.barocert.com. Each fixture file under `tests/fixtures/barocert/` is tagged with the documentation version it was modelled from (field `doc_version` in `meta.json`).

When Barocert updates its API documentation:
1. Review the changelog at developers.barocert.com.
2. Update the fixture files to reflect new or changed fields.
3. Increment `doc_version` in `meta.json`.
4. Open a PR with label `mock-drift`.

## Upstream divergence policy

Shape-axis mocks diverge when the upstream SDK documentation adds, removes, or renames fields. KOSMOS CI does not automatically detect this divergence — it relies on the engineering team to monitor the Barocert developer portal changelog. The `doc_version` field in `tests/fixtures/barocert/meta.json` is the canonical reference for the documented version the mock was built against.
