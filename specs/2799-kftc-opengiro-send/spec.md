# Feature Specification: KFTC OpenGiro Send Adapter

**Feature Branch**: `2799-kftc-opengiro-send`  
**Created**: 2026-05-18  
**Status**: Draft  
**Input**: User description: "Wrap the KFTC OpenGiro official billing and payment OpenAPI as a UMMAYA send primitive live adapter. Use the logged-in KFTC developer site evidence, preserve UMMAYA's Claude Code-style tool loop, avoid secret leakage, respect the official Callback URL and API Key workflow, and move through the full Spec Kit pipeline without further review prompts."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Classify OpenGiro as a Send Channel (Priority: P1)

A maintainer can decide, from official KFTC evidence and UMMAYA's primitive model, whether OpenGiro belongs in the live tool system and which citizen-facing action it represents.

**Why this priority**: UMMAYA must not add a financial side-effecting adapter without proving the official channel exists and mapping it to the correct primitive and permission gate.

**Independent Test**: Review the feature evidence and adapter catalog update; confirm that OpenGiro is documented as a `send` channel, that read-only discovery is not used for payment actions, and that the source links point to official KFTC developer pages.

**Acceptance Scenarios**:

1. **Given** the KFTC OpenGiro public OpenAPI pages list bill and payment endpoints, **When** UMMAYA documents the candidate adapter, **Then** it classifies OpenGiro bill creation, bill cancellation, payment URL creation, and payment result inquiry under a financial `send` surface with explicit irreversible-action handling where applicable.
2. **Given** the KFTC developer portal requires service application, Callback URL registration, and API Key registration before testing, **When** the adapter readiness is documented, **Then** the spec marks credentialed live execution as blocked until those official portal steps are complete and evidence is captured without exposing secrets.

---

### User Story 2 - Register a Safe KFTC Credential Path (Priority: P1)

An operator can prepare OpenGiro credentials for UMMAYA without revealing Client Secret values in source, logs, specs, screenshots, or test artifacts.

**Why this priority**: The KFTC portal exposes persistent API credentials and callback configuration; mishandling them would create a long-lived financial API risk.

**Independent Test**: Run credential-path tests and inspect generated artifacts; no Client Secret value appears, Callback URL requirements are documented, and the system fails closed when credentials or callback setup are missing.

**Acceptance Scenarios**:

1. **Given** OpenGiro service is `이용중` but no Callback URL is registered, **When** an operator tries to register the API Key or run a live adapter probe, **Then** UMMAYA reports the missing Callback URL/API Key readiness as a setup blocker instead of attempting a live call.
2. **Given** a Client ID and masked Client Secret are available in the portal, **When** the operator configures UMMAYA, **Then** only environment variables or operator secret storage are used and no secret value is written to repository files or CI logs.
3. **Given** a Callback URL is required by KFTC, **When** UMMAYA documents the setup path, **Then** it names one canonical callback path and states that registering it in the KFTC portal is an operator action tied to the configured deployment environment.

---

### User Story 3 - Invoke OpenGiro Through the Send Envelope (Priority: P2)

A citizen-facing UMMAYA session can request an OpenGiro bill/payment action through the existing `send` primitive and receive a structured receipt without exposing KFTC-specific vocabulary in the primitive envelope.

**Why this priority**: The adapter must preserve UMMAYA's main-verb abstraction; domain-specific fields belong inside the adapter params and receipt, not in the shared primitive contract.

**Independent Test**: Use fixture-backed adapter tests to invoke the OpenGiro send tool with valid and invalid params; confirm that the shared envelope remains `{tool_id, params}` on input and `{transaction_id, status, adapter_receipt}` on output.

**Acceptance Scenarios**:

1. **Given** a valid OpenGiro bill or payment request fixture, **When** the session invokes the OpenGiro tool through `send`, **Then** the response includes a deterministic UMMAYA transaction id, a terminal or pending status, and an adapter receipt containing only sanitized OpenGiro receipt fields.
2. **Given** required OpenGiro params are missing or malformed, **When** the session invokes the adapter, **Then** UMMAYA returns a validation error inside the tool loop and does not contact KFTC.
3. **Given** a live KFTC response indicates rejection, expiry, or upstream error, **When** the adapter handles it, **Then** the response maps to `rejected`, `failed`, or `pending` without unhandled exceptions or retries that could duplicate a financial action.

---

### User Story 4 - Preserve Mock-to-Live Evidence (Priority: P3)

A reviewer can trace every OpenGiro adapter field back to official KFTC documentation or a sanitized live readiness artifact.

**Why this priority**: KFTC document access is partially gated; UMMAYA needs explicit provenance so future maintainers know which evidence is public, which requires portal approval, and which was intentionally deferred.

**Independent Test**: Inspect the feature research, adapter documentation, JSON schema, and fixtures; every endpoint, field group, callback blocker, and permission statement has a source or blocker note.

**Acceptance Scenarios**:

1. **Given** public OpenGiro pages provide endpoint and response examples but gated documents remain inaccessible, **When** research artifacts are reviewed, **Then** public-source evidence and gated-source blockers are separated.
2. **Given** a fixture is used before live KFTC calls are allowed, **When** the adapter documentation is generated, **Then** it marks the fixture as shape-mirrored and records what must be revalidated before enabling live execution.

### Edge Cases

- Callback URL is absent, malformed, or registered for a different deployment environment.
- OpenGiro API Key registration remains blocked after service application.
- KFTC document pages remain access-denied even after OpenGiro is marked `이용중`.
- Payment URL responses expire before the citizen completes the external payment step.
- The upstream response is successful at the KFTC gateway but rejected by the biller or payment institution.
- The same citizen request is retried after a timeout and could duplicate a financial action.
- Live credentials are present locally but the session lacks the required citizen permission gate.
- Tests run in CI without live KFTC credentials and must not contact KFTC.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST document KFTC OpenGiro as an official financial side-effecting channel mapped to UMMAYA's `send` primitive.
- **FR-002**: System MUST separate public KFTC OpenAPI evidence from portal-gated documents and record the exact blocker state observed in the developer portal.
- **FR-003**: System MUST define one canonical OpenGiro adapter family covering bill creation, bill cancellation, payment URL creation, and payment/result inquiry, while keeping the shared `send` envelope domain-neutral.
- **FR-004**: System MUST require a cited KFTC policy/source URL and citizen-facing `send` gate for any OpenGiro adapter registration.
- **FR-005**: System MUST fail closed when Callback URL registration, API Key registration, Client ID, Client Secret, or access token readiness is incomplete.
- **FR-006**: System MUST prevent KFTC Client Secret values, access tokens, authorization codes, and raw financial identifiers from being committed, logged, included in test artifacts, or printed in final reports.
- **FR-007**: System MUST provide fixture-backed tests for successful, validation-failed, upstream-rejected, expired-payment-url, and missing-credential paths without contacting live KFTC services in CI.
- **FR-008**: System MUST map upstream OpenGiro outcomes into the existing `send` result statuses without introducing a new primitive or domain-specific top-level envelope fields.
- **FR-009**: System MUST define operator setup instructions for KFTC service application, Callback URL registration, API Key registration, and safe secret provisioning.
- **FR-010**: System MUST treat actual financial settlement or external payment confirmation as citizen/operator-mediated unless official KFTC docs prove a fully API-callable settlement flow for the registered application.
- **FR-011**: System MUST expose bilingual Korean/English search hints sufficient for tool discovery of OpenGiro bill/payment requests.
- **FR-012**: System MUST update the adapter catalog and schema exports so maintainers can verify the OpenGiro surface from documentation alone.
- **FR-013**: System MUST ensure live execution is opt-in and excluded from default tests and CI.
- **FR-014**: System MUST include a sanitized direct-curl evidence checklist for any future live probe before live mode is considered complete.

### Key Entities *(include if feature involves data)*

- **OpenGiro Service Readiness**: The portal-level state for service application, Callback URL registration, API Key registration, and document/tool access.
- **OpenGiro Credential Set**: Operator-held Client ID, Client Secret, access token material, and callback configuration required to call KFTC services.
- **OpenGiro Send Request**: Adapter-specific request payload for bill creation, bill cancellation, payment URL creation, payment result inquiry, or payment-status inquiry.
- **OpenGiro Receipt**: Sanitized adapter result containing transaction status, upstream response code/message, optional payment URL metadata, and non-secret correlation identifiers.
- **Evidence Artifact**: Official source link, portal blocker note, sanitized response header/body sample, or fixture provenance record used to justify adapter behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of OpenGiro endpoints included in this feature have an official KFTC source URL or a documented gated-source blocker.
- **SC-002**: 0 committed files, logs, test snapshots, or final reports contain KFTC Client Secret, access token, authorization code, or raw personal financial identifiers.
- **SC-003**: Default test runs complete without making live KFTC network calls.
- **SC-004**: Fixture-backed tests cover at least five paths: success, validation failure, missing credential/setup, upstream rejection, and expired payment URL.
- **SC-005**: The adapter catalog lists the OpenGiro surface under `send` with Korean and English search hints and a policy citation.
- **SC-006**: An operator can follow the documented setup path and determine, in under 10 minutes, whether the KFTC portal is ready for live probing or still blocked by Callback URL/API Key/document access.

## Assumptions

- The feature uses the KFTC developer portal account already logged in by the user for readiness inspection, but does not reveal or store Client Secret values.
- OpenGiro service application has been switched to `이용중`, while API Key registration is blocked until a Callback URL is registered.
- KFTC public OpenAPI pages are sufficient for fixture shape and adapter documentation, but gated documents are not treated as available until portal access is granted.
- The first implementation keeps live KFTC calls disabled by default and uses fixtures for CI and local non-live verification.
- The canonical Callback URL belongs to the operator's deployed UMMAYA gateway environment; registering an arbitrary localhost URL in the KFTC portal is not assumed safe for production.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- Secret retrieval from the browser UI by the agent — persistent KFTC secrets must be handled by the operator and never read into the conversation.
- CI execution against live KFTC, government, identity, payment, certificate, utility, or citizen-infrastructure endpoints — default verification uses fixtures only.
- UMMAYA-issued financial authorization policy — permission classification must cite KFTC or the relevant agency; UMMAYA does not invent policy.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Production financial settlement confirmation beyond documented OpenGiro redirect/result APIs | Requires approved KFTC documents, registered Callback URL, API Key, and sanitized live probe evidence | Follow-up live validation after this adapter epic | #2979 |
| General live `send` gateway support for all financial adapters | Existing gateway only permits live `find` and `locate`; broader send-gateway semantics need separate architecture review | Tool system live-gateway expansion | #2980 |
| Additional KFTC services beyond OpenGiro, such as OpenBanking transfer or Financial Certificate verification | Different scopes, credentials, assurance levels, and documents | Separate KFTC service adapter epics | #2981 |
