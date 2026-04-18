# Mock: omnione

**Mirror axis**: byte
**Source reference**: W3C DID Core 1.0 (https://www.w3.org/TR/did-core/) + OmniOne OpenDID reference implementation (https://github.com/OmniOneID) — Apache-2.0
**License**: Apache-2.0
**Scope**: Reproduces the DID Document resolution and Verifiable Presentation exchange wire format defined by the OmniOne OpenDID SDK, covering the subset used by KOSMOS for citizen identity attestation; does not reproduce OmniOne's proprietary trust registry or blockchain anchor calls.

## What this mock reproduces

- DID Document structure: `id`, `verificationMethod[]`, `authentication[]`, `assertionMethod[]` fields per W3C DID Core §5
- Verifiable Credential (VC) envelope: `@context`, `type`, `issuer`, `issuanceDate`, `credentialSubject` per W3C VC Data Model 1.1
- Verifiable Presentation (VP) request/response exchange: `challenge` nonce, `proof` (Ed25519Signature2020), holder binding
- HTTP endpoints as defined in the OmniOne OpenDID Server SDK (`/api/v1/did/resolve/{did}`, `/api/v1/vp/verify`)
- Error responses: `{ code, message }` envelope with OmniOne-specific error codes (e.g., `DID_NOT_FOUND`, `PROOF_INVALID`)

## What this mock deliberately does NOT reproduce

- OmniOne's proprietary blockchain ledger write path (DID registration / revocation anchor)
- The OmniOne trust registry — mock issues VCs from a hard-coded test issuer DID
- OmniOne's internal HSM key storage — the mock uses software Ed25519 keys from the `cryptography` stdlib
- Government-issued VC content (e.g., resident registration number) — fixture uses synthetic citizen stubs

## Fixture recording approach

Because the OmniOne reference server (https://github.com/OmniOneID/did-doc-architecture) can be run locally via Docker Compose, fixtures are recorded against the local reference stack rather than a live production endpoint. Steps:

1. Clone the OmniOneID/did-doc-architecture repo and run `docker compose up`.
2. Run `uv run python tests/fixtures/record_omnione.py` with `KOSMOS_OMNIONE_BASE_URL=http://localhost:8080`.
3. Commit the updated fixture JSON files under `tests/fixtures/omnione/`.

## Upstream divergence policy

The OmniOne OpenDID SDK is tagged with semantic versions on GitHub. Pin the version used for fixture recording in `tests/fixtures/omnione/meta.json` as `sdk_version`. When a new minor version is released, re-record fixtures and open a PR with label `mock-drift`. Breaking changes in the VP exchange protocol require a new mock version directory (e.g., `docs/mock/omnione_v2/`) and a deprecation note in this file.
