# KOSMOS Scenarios — OPAQUE System Narratives

This directory contains journey narratives for systems that KOSMOS integrates with but **cannot mock** because the protocol, schema, or API is not publicly disclosed. These are distinct from the mockable systems documented under `docs/mock/`.

## Why scenarios exist

The KOSMOS harness distinguishes between two categories of external system:

| Category | Criteria | Location |
|----------|----------|----------|
| **Mock** | Public OpenAPI, public SDK docs, or open reference implementation exists; wire format can be reproduced byte-for-byte (`byte` axis) or shape-for-shape (`shape` axis) | `docs/mock/<system>/README.md` |
| **Scenario** | Protocol, XSD, API schema, or session handshake is withheld from public disclosure; reproduction is not possible without a commercial license or inter-agency agreement | `docs/scenarios/<system>.md` |

An OPAQUE system appearing in `docs/scenarios/` must **never** have a mock adapter under `src/kosmos/tools/mock/`. CI enforces this boundary via `tests/test_no_opaque_mock_adapter.py`.

## Current scenarios

| File | System | Blocking factor |
|------|--------|----------------|
| `gov24_submission.md` | Government 24 (정부24) document submission | Submission API withheld from public disclosure; inter-agency agreement required |
| `kec_xml_signature.md` | KEC (한국전자인증) XML digital signature | XSD + public signing key not disclosed; commercial SDK license required |
| `npki_portal_session.md` | NPKI portal session (공인인증서 포털 세션) | Portal-proprietary session handshake; CA-specific browser plugin protocol |

## How a scenario becomes a mock (FR-025 promotion path)

A scenario can be promoted to a mock when the blocking factor is resolved — typically because:
- The authority publishes a public OpenAPI spec or reference implementation.
- A commercial partner grants KOSMOS access to a sandbox environment with documented wire format.
- A community reverse-engineering effort produces a verified public spec (e.g., a government open-data mandate).

**Promotion process**:

1. Open a GitHub Issue titled `Promote <system> from scenario to mock` with label `mock-promotion`.
2. Attach the evidence that resolves the blocking factor (link to public spec, sandbox access confirmation, etc.).
3. The Lead agent reviews the evidence and assigns a mirror axis (`byte`, `shape`, or `shape+seed`).
4. A new `docs/mock/<system>/README.md` is created following the mock README template.
5. A mock adapter is implemented under `src/kosmos/tools/mock/<system>/`.
6. The scenario file (`docs/scenarios/<system>.md`) is updated with the promotion footer (see template below) but **not deleted** — it serves as a historical record of the OPAQUE boundary.
7. `tests/test_mock_scenario_split.py` is updated to reflect the new mock count and scenario count.

**Promotion footer template** (add to the bottom of the scenario file on promotion):

```
---

*Promoted to mock on <YYYY-MM-DD>, tracked by #<issue>*
```

## Harness discipline

Scenarios define the boundary of KOSMOS's responsibility. Everything inside the `## KOSMOS ↔ real system handoff point` section of each scenario file is what KOSMOS does on its side of the boundary. Everything outside that section is the real system's responsibility.

KOSMOS never guesses, approximates, or reimplements an OPAQUE protocol. If the protocol is not publicly documented, KOSMOS delegates to the real system and records only the structured outcome.
