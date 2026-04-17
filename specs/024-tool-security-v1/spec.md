# Feature Specification: Tool Template Security Spec v1 — Ministry-PR-ready hardening

**Feature Branch**: `024-tool-security-v1`
**Created**: 2026-04-17
**Status**: Draft
**Input**: Epic #612 — synthesize 6 security research lanes (Epic #605) into a single normative spec for the KOSMOS Tool Template, hardened to a level that a Korean ministry reviewer can accept for a PR/trial partnership.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ministry auditor validates KOSMOS tool-call behavior (Priority: P1)

A government security reviewer (e.g., 부처 정보보호 담당관 or KISA 평가위원) receives KOSMOS as a candidate system for a public-service pilot. The reviewer must be able to answer, from documentation alone, three questions: (1) what minimum authentication strength is required for each of the 8 canonical tools, (2) what immutable evidence is produced per tool call, and (3) how personal information handling responsibilities are split between the citizen, KOSMOS, and the ministry. The reviewer completes this assessment without reading source code and without requiring Q&A with the KOSMOS team.

**Why this priority**: This is the binding outcome of the epic. If a ministry reviewer cannot self-serve answers to these three questions, the spec has failed its purpose regardless of how well the underlying controls are designed.

**Independent Test**: An independent reviewer (not involved in authoring the spec) reads only the published normative document plus the three referenced artifacts (PR checklist, pydantic model, OpenAPI skeleton) and produces a structured gap assessment. The test passes if the reviewer can list, unaided, the min-AAL for all 8 tools, the audit record schema fields, and the PIPA role interpretation for both pre-synthesis and synthesis stages.

**Acceptance Scenarios**:

1. **Given** a reviewer reads the normative spec end-to-end, **When** they list the minimum authentication level for each of the 8 canonical tools, **Then** their list matches the single `TOOL_MIN_AAL` table in the spec with zero ambiguity for any tool including `check_eligibility` and its `public_path` fallback.
2. **Given** a reviewer is shown a sample tool-call audit record, **When** they verify it against the spec's JSON Schema, **Then** every required field is present, each is traceable to either a Korean legal basis or an international standard citation, and no [NEEDS CLARIFICATION] or placeholder text remains.
3. **Given** a reviewer asks "who is the 개인정보처리자 in a typical tool call," **When** they consult the spec's PIPA role section, **Then** they find an unambiguous answer with the pre-synthesis `수탁자` default and the LLM-synthesis controller-level carve-out explicitly demarcated.

---

### User Story 2 - Citizen delegates authority to KOSMOS to call a ministry API (Priority: P1)

A citizen interacts with KOSMOS to accomplish a government-service task that requires an authenticated call to a ministry API (e.g., 긴급복지 신청 자격 확인, 주민등록등본 발급 의뢰). The citizen's delegation must be expressible, time-bounded, scope-limited, and revocable without bypassing PASS/공동인증서's TEE-bound authentication constraints. The delegation protocol must be grounded in OAuth 2.1 practices and W3C Verifiable Credentials such that a future ministry MCP/API endpoint can adopt the same protocol without KOSMOS-specific coupling.

**Why this priority**: Every non-trivial public-service tool call requires delegated authority. Without a documented protocol, the spec reduces to a catalog of controls rather than a usable platform contract. This is the second core asset for ministry PR positioning per Lane 4.

**Independent Test**: A standards-literate reviewer reads the OpenAPI 3.0 skeleton plus the spec's delegation section and confirms it can be implemented by a ministry that adopts OAuth 2.1 + mTLS without depending on any KOSMOS proprietary artifact. The test passes if the skeleton validates under an OpenAPI 3.0 linter and references only IETF RFCs, W3C recommendations, or Korean statutory artifacts.

**Acceptance Scenarios**:

1. **Given** a tool call requires AAL2 delegated authority, **When** the spec is consulted for the auth flow, **Then** the exact flow (device grant / token exchange / consent record fields) is documented with RFC identifiers including RFC 8628, RFC 8693, and RFC 9068.
2. **Given** a citizen revokes delegation mid-session, **When** the spec is consulted for the revocation semantics, **Then** the token lifetime, revocation endpoint, and downstream cache invalidation are specified per RFC 7009 with explicit maximum propagation window.
3. **Given** a PII-bound scope (e.g., `issue_certificate:resident_registration`), **When** the consent record is emitted, **Then** the `dpa_reference` field is non-null and points to a DPA template identifier, closing the PIPA §26 위탁 documentation gap.

---

### User Story 3 - Tool-adapter developer ships a new KOSMOS tool through PR review (Priority: P2)

A KOSMOS contributor (human or agent) adds or modifies a tool adapter. Before opening the PR, they consult the unified tool-adapters PR checklist and can self-verify compliance against all six security domains (Korean legal, international standards, LLM/tool threats, identity/delegation, public-sector precedent, supply-chain/audit) through a single checklist pass. A reviewer can complete the checklist-mediated review in under 30 minutes for a standard adapter.

**Why this priority**: The checklist is the operational instrument that prevents drift between the normative spec and shipped code over time. Without it, the spec decays into aspirational prose. Lower priority than P1 stories because it is enabling infrastructure rather than a direct ministry-facing deliverable, but still P2 because without it the epic's controls are unenforceable.

**Independent Test**: A contributor unfamiliar with the security research lanes opens the PR checklist, applies it to a representative adapter (e.g., an existing NMC or KOROAD adapter), and produces a compliance report. The test passes if they identify the same items a senior reviewer would identify, with at most one false-negative, within 30 minutes.

**Acceptance Scenarios**:

1. **Given** a new tool adapter PR, **When** the unified checklist is applied, **Then** all six research-lane domains are covered by a minimum of five unified checklist items without requiring lane-specific prior knowledge.
2. **Given** an adapter violates the fail-closed invariant (e.g., missing `auth_level` annotation on a PII-bound tool), **When** the contributor runs the repository's invariant tests locally, **Then** the failure is surfaced with a diagnostic pointing to the specific spec section and the `GovAPITool` field that was violated.

---

### Edge Cases

- **Output sanitization vs audit integrity**: The spec must disambiguate which output is hashed for tamper-evidence. Raw output contains PII that cannot be exported to auditors; sanitized output has been through LLM-adjacent filtering that itself could fail. The resolution is the `sanitized_output_hash` field plus an explicit Merkle chain coverage declaration stating which hash the tamper-evident chain binds.
- **Delegation revocation race**: A citizen revokes delegation while an in-flight tool call is mid-execution. The spec must declare whether the call completes, is aborted, or is completed-then-voided, and how the audit record reflects the citizen's revocation intent.
- **AAL downgrade attempts**: A tool-call request arrives with a credential bound to a lower AAL than the tool's `TOOL_MIN_AAL`. The fail-closed invariant applies, but the spec must also state that the audit record for the rejected call is retained at the same evidentiary level as successful calls.
- **`check_eligibility` public_path**: For pure rules-only eligibility checks over public inputs, the spec permits an AAL1 `public_path`. The spec must state the exact conditions under which this fallback is allowed and require an explicit marker in the audit record so the path cannot be confused post-hoc with an authenticated call.
- **LLM synthesis carve-out**: When KOSMOS's synthesis stage combines citizen PII with ministry API response text, the processor/controller boundary shifts mid-session. The spec must declare the carve-out explicitly and require the consent record to separate "forward raw response" consent from "synthesize response" consent.
- **SBOM divergence**: A dependency bump in `uv.lock` diverges from the last-signed SBOM. The spec must state the build-gate behavior (fail fast) and the review path (force-regenerate with a signed note, not silent override).
- **Stale token reuse**: A delegation token expires or is revoked but remains cached in a long-running KOSMOS session. The spec must require token introspection per RFC 7662 at a minimum cadence and on every irreversible-action tool call regardless of cache state.

## Requirements *(mandatory)*

### Functional Requirements

**Tool registry and classification**

- **FR-001**: The spec MUST define a single `TOOL_MIN_AAL` table listing all 8 canonical tools (`lookup`, `pay`, `issue_certificate`, `submit_application`, `reserve_slot`, `subscribe_alert`, `resolve_location`, `check_eligibility`) with exactly one minimum authentication level per tool, sourced from NIST SP 800-63-4 (never SP 800-63-3).
- **FR-002**: The `check_eligibility` entry in the `TOOL_MIN_AAL` table MUST be AAL2 with an explicit `public_path` marker that permits AAL1 only for rules-only evaluation over public inputs with no PII in either request or response.
- **FR-003**: The `GovAPITool` schema MUST expose four new fields that are mandatory for every registered tool: `auth_level` (enum: public | AAL1 | AAL2 | AAL3), `pipa_class` (enum: non_personal | personal | sensitive | identifier), `is_irreversible` (boolean), and `dpa_reference` (nullable string identifier pointing to a DPA template when the scope is PII-bound, non-null whenever `pipa_class` is anything other than `non_personal`).
- **FR-004**: The spec MUST preserve and reference the FR-038 fail-closed invariant "any tool whose input or output includes personal data MUST require authentication" and extend it so that any tool with `pipa_class != non_personal` MUST have `auth_level != public`.
- **FR-005**: Every tool registration MUST be rejected at load time if any of the four new `GovAPITool` fields is missing, ambiguous, or inconsistent with the `TOOL_MIN_AAL` table.

**Permission pipeline**

- **FR-006**: The permission pipeline MUST reject any tool call whose presented credential AAL is below the tool's `TOOL_MIN_AAL`, and MUST emit an audit record of the rejection at the same evidentiary level as a successful call.
- **FR-007**: For any tool where `is_irreversible = true`, the permission pipeline MUST perform a live token introspection per RFC 7662 before execution, regardless of local cache state, and MUST reject the call if the token is not currently active.
- **FR-008**: The spec MUST require the permission pipeline to be deny-by-default: in the absence of a matching positive authorization, the call is rejected. This invariant MUST be expressed in a testable form that maps to OWASP ASVS V4.1.5.

**Audit trail**

- **FR-009**: The `ToolCallAuditRecord` pydantic model and its JSON Schema (Draft 2020-12) MUST include at minimum the following fields: `tool_id`, `session_id`, `caller_identity`, `permission_decision`, `input_hash`, `output_hash`, `sanitized_output_hash` (nullable, string), `timestamp` (RFC 3339 with timezone), `cost_tokens`, `rate_limit_bucket`, `auth_level_presented`, `pipa_class`, `dpa_reference`, and `merkle_leaf_id`.
- **FR-010**: The spec MUST explicitly declare which hash the Merkle chain covers. The declaration MUST state that the Merkle leaf binds `sanitized_output_hash` when present and `output_hash` otherwise, with the chosen variant recorded in a dedicated `merkle_covered_hash` field so downstream verifiers do not need to re-examine the record's content to know which hash is authoritative.
- **FR-011**: Audit retention MUST be reconciled between PIPA 안전조치 고시 §8 (2 years) and 전자정부법 §33 (5 years) by binding to the longer period (5 years) as the default, with a citation explaining that KOSMOS chooses the binding maximum to satisfy both statutes simultaneously.
- **FR-012**: Mock and live adapters MUST produce audit records against the identical schema. The spec MUST forbid transport-layer divergence in the record shape; only the `adapter_mode` field may differ to distinguish mock from live.

**Identity, consent, and delegation**

- **FR-013**: The spec MUST include an OpenAPI 3.0 skeleton for an `/agent-delegation` endpoint family covering consent creation, token issuance, token refresh, token introspection, and revocation, grounded in RFC 8628, RFC 8693, RFC 9068, RFC 7636, RFC 7662, and RFC 7009.
- **FR-014**: Every consent record issued through `/agent-delegation` MUST carry a `dpa_reference` field; the field MUST be non-null whenever the requested scope touches a PII-bound tool, closing the PIPA §26 위탁 documentation gap.
- **FR-015**: Every consent record MUST also carry a `synthesis_consent: bool` field that is separate from the processing consent, reflecting the PIPA role carve-out whereby "forwarding a ministry response" and "synthesizing a response using LLM-combined PII" are distinct processing purposes.
- **FR-016**: The spec MUST document that PASS and 공동인증서 are TEE-bound and cannot be programmatically exported to KOSMOS, and MUST explain that the delegation protocol intentionally does not attempt to bypass this constraint but instead builds on OAuth 2.1 + Verifiable Credentials to achieve equivalent assurance for agent-mediated actions.

**Supply chain and provenance**

- **FR-017**: The repository MUST include a scaffolded GitHub Actions workflow that generates an SBOM in both SPDX 2.3 and CycloneDX 1.6 formats from `pyproject.toml` and `uv.lock` on every push to `main` and every tagged release.
- **FR-018**: The spec MUST document the SLSA Level 3 gap analysis (current state → target state) and MUST list the specific provenance artifacts the project commits to producing as the minimum viable supply-chain posture for a ministry pilot.
- **FR-019**: The spec MUST state the build-gate policy for SBOM divergence: a build whose generated SBOM diverges from the last-signed SBOM MUST fail, and the recovery path MUST require a signed regeneration with an explicit reviewer-authored note, not a silent override.

**Documentation and PR gating**

- **FR-020**: `docs/tool-adapters.md` MUST be extended with at minimum 5 new PR checklist items covering the six research-lane domains, unified so that a contributor applying the checklist touches every domain without needing to know the lane boundaries.
- **FR-021**: The normative spec MUST cite Korean statutory artifacts (PIPA, 전자정부법, 전자서명법, K-ISMS-P), international standards (NIST SP 800-63-4, OWASP ASVS 4.0, OWASP Top 10 for LLM, ISO 27001, NIST Zero Trust SP 800-207), and at least three public-sector precedents (eGovFramework, Singapore IMDA MGF, EU AI Act Annex III) with resolvable identifiers or section references for every control it proposes.

### Key Entities *(include if feature involves data)*

- **`GovAPITool`**: Registry entry describing a KOSMOS tool adapter. Extended in this spec with `auth_level`, `pipa_class`, `is_irreversible`, and `dpa_reference`. All fields MUST be populated at registration time; fail-closed loading rejects incomplete entries.
- **`ToolCallAuditRecord`**: Immutable per-call evidence artifact. Contains input/output hashing, sanitized-output hashing, permission decision, caller identity, and Merkle-chain binding metadata. Mock and live adapters produce identical record shape.
- **`DelegationToken`**: Time-bounded, scope-limited token representing citizen authority delegated to KOSMOS. Carries `aal_asserted`, `scope`, `expires_at`, and `introspection_endpoint`. Revocation semantics defined per RFC 7009.
- **`ConsentRecord`**: Citizen-signed artifact linking a delegation event to one or more tool scopes. Carries `dpa_reference` (non-null for PII-bound scopes) and `synthesis_consent` (separate boolean for the LLM-synthesis carve-out).
- **`SBOMArtifact`**: Build-time-generated bill of materials in both SPDX 2.3 and CycloneDX 1.6 formats. Signed per SLSA v1.0 provenance expectations.
- **`TOOL_MIN_AAL`**: Static lookup table mapping each of the 8 canonical tools to its minimum AAL, with an explicit `public_path` exception for `check_eligibility` rules-only evaluation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All four hard contradictions identified in the cross-lane consistency review (AAL drift for `check_eligibility`, NIST SP 800-63-3 → 63-4 migration, audit retention period, `output_hash` tamper-evidence ambiguity) are explicitly resolved in the spec with citations. Verification: a reviewer reading only the spec can state each resolution and its legal or standards basis without consulting the original research lanes.
- **SC-002**: An adapter PR reviewer can complete the unified checklist-mediated security review of a standard adapter in under 30 minutes without cross-lane domain expertise. Verification: measured on three representative adapters by a reviewer unfamiliar with the six research lanes.
- **SC-003**: 100% of the 8 canonical tools have all four new `GovAPITool` fields populated at registration time. Verification: the registry's load-time invariant test fails on any missing field, and CI runs this test on every push.
- **SC-004**: The `ToolCallAuditRecord` JSON Schema validates at least three worked example records (one successful authenticated call, one rejected-for-insufficient-AAL call, one `check_eligibility` `public_path` call) included in the spec. Verification: schema validation passes on all three examples in a reproducible CI step.
- **SC-005**: SBOM generation is fully automated from `uv.lock` + `pyproject.toml` with zero manual steps, and the workflow produces both SPDX 2.3 and CycloneDX 1.6 artifacts. Verification: a fresh clone can reproduce both artifact formats by running only the scaffolded GitHub Actions workflow.
- **SC-006**: An independent reviewer (not involved in spec authoring) produces a gap assessment from documentation alone that correctly identifies the min-AAL for every tool, the audit record required fields, and the PIPA role interpretation for both pre-synthesis and synthesis stages. Verification: a blind review exercise at spec acceptance.
- **SC-007**: The `/agent-delegation` OpenAPI 3.0 skeleton validates against the OpenAPI 3.0 specification under a standard linter with zero errors and cites only IETF RFCs, W3C recommendations, or Korean statutory artifacts for every normative reference. Verification: automated OpenAPI linting plus citation audit.
- **SC-008**: The spec uses consistent PIPA role language throughout — every occurrence of the 처리자/수탁자 distinction traces to the single pre-decided interpretation (§26 수탁자 default + LLM-synthesis controller-level carve-out). Verification: a textual audit finds zero contradictory role statements.

## Assumptions

- The six research-lane deliverables under `.eval-artifacts/security-design-research/` are frozen inputs for this spec; no new primary research is conducted during `/speckit-plan` or later phases.
- The cross-lane consistency review at `00-consistency-review.md` is the authoritative reconciliation; where it conflicts with any individual lane, it wins.
- The PIPA role interpretation (§26 수탁자 default + LLM-synthesis controller-level carve-out) is a pre-decided product judgment, recorded in auto-memory, and not re-litigated in this epic.
- The four hard-contradiction resolutions listed in the epic brief are pre-decided inputs: `check_eligibility` = AAL2 with `public_path` marker, NIST 63-4 (not 63-3), retention = 5 years (binding maximum of PIPA §8 and 전자정부법 §33), `sanitized_output_hash` added to the audit record with explicit Merkle coverage declaration.
- The full 8-tool mock implementation, the full Merkle chain implementation, the full `/agent-delegation` endpoint implementation, and the PIPC 유권해석 질의서 are separate efforts tracked in the deferred items table below.
- The spec is written in English per KOSMOS hard rules; Korean legal citations retain their original Korean text where precision requires it.
- Reviewers of the spec are assumed to have working familiarity with either Korean public-sector compliance or international AppSec / identity standards, but not necessarily both; the spec must bridge the two audiences.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- PIPC (개인정보보호위원회) 유권해석 질의서 drafting and submission — this is a legal-process artifact, not a platform engineering output; KOSMOS's platform spec can stand independently of the 유권해석 outcome.
- Real DPA (Data Processing Agreement) legal text — DPA template references in the spec are identifiers; the binding legal text is authored by counsel during ministry partnership negotiations, not in a KOSMOS spec.
- Public Rekor-like transparency log for citizen sessions — transparency logs are appropriate for build provenance (handled here) but inappropriate for per-citizen tool-call records whose privacy posture requires the opposite of public append-only disclosure.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Full 8-tool mock implementation with live-fixture continuity | Requires adapter-by-adapter work beyond a single spec epic | Phase 2 — Multi-Agent Swarm | #643 |
| Full `/agent-delegation` endpoint implementation | Spec lands OpenAPI 3.0 skeleton only; server-side implementation is a distinct engineering effort | Phase 2 — Multi-Agent Swarm | #644 |
| Full Merkle audit chain implementation | Spec lands schema and Merkle-coverage declaration; chain construction, verifier, and append-only storage are separate | Phase 2 — Multi-Agent Swarm | #645 |
| Full permission pipeline wiring (policy engine + introspection hook + deny-path emitter) | Spec lands the model contract only; pipeline integration (deny-by-default enforcement, FR-007 introspection invocation, rejection-path audit emission) is a distinct engineering effort | Phase 2 — Multi-Agent Swarm | #646 |
| Full SBOM signing (sigstore/cosign end-to-end) | Scaffolded workflow in this spec includes SBOM generation + diff gate; production signing requires a key-management posture not in scope here | Phase 2 — Supply chain | #647 |
| PIPC 유권해석 질의서 draft | Parallel legal-process track; not a blocker for v1 spec acceptance | Parallel legal track | #648 |
| Singapore IMDA MGF alignment deep dive beyond precedent citation | Precedent-citation depth is sufficient for this spec; MGF-specific compliance mapping is a separate positioning artifact | Phase 2 — Positioning & PR | #649 |
| EU AI Act Annex III full obligation mapping | Spec cites the subset relevant to Tool Template controls; full mapping is a distinct compliance artifact | Phase 2 — Compliance | #650 |
| eGovFramework code-level pattern adoption | Lane 5 cites eGovFramework patterns; concrete code reuse is an implementation epic | Phase 2 — Multi-Agent Swarm | #651 |
