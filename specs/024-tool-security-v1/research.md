# Research: Tool Template Security Spec v1

**Feature**: 024-tool-security-v1
**Date**: 2026-04-17
**Phase**: 0 (Outline & Research)

## 0. Purpose

Resolve all `NEEDS CLARIFICATION` slots in the Technical Context, validate the Deferred Items table per Constitution Principle VI, and record the authoritative design-decision rationale with concrete reference pointers for every non-trivial control in the spec.

The six research lanes (Epic #605, under `.eval-artifacts/security-design-research/`) are treated as **frozen primary inputs**. This `research.md` does not re-open lane-level questions; it synthesizes them and binds each spec requirement to a reference source per Constitution Principle I.

## 1. Technical Context — unknowns resolution

**Status**: Zero `NEEDS CLARIFICATION` markers remain in `plan.md § Technical Context`. All slots are resolved below.

| Context slot | Resolution | Basis |
|---|---|---|
| Language/Version | Python 3.12+ (project baseline, no bump) | Existing `pyproject.toml`; KOSMOS constitution § Development Standards |
| Primary Dependencies | Pydantic v2, httpx >=0.27, pytest, pytest-asyncio — all existing. No new runtime deps. | This spec is a contract + model seed; the full pipeline lives in later epics |
| Storage | N/A — schema contract only | `ToolCallAuditRecord` is a shape, not a backing store. Append-only storage is explicitly deferred. |
| Testing | pytest unit tests for registration invariants + audit-record round-trip. JSON Schema validates 3 worked examples in CI. | FR-005, FR-009, SC-003, SC-004 |
| Target Platform | Linux CI (SBOM workflow), macOS/Linux dev (Python changes) | `.github/workflows/ci.yml` baseline |
| Project Type | Single project | No new deployable surface |
| Performance Goals | `ToolCallAuditRecord.model_validate` < 5 ms per record | Per-call audit overhead must be negligible when the enforcement pipeline lands |
| Constraints | Fail-closed registration; no silent defaults on new fields | Constitution II; FR-004, FR-005 |
| Scale/Scope | 8 canonical tools; 2,500-3,500 line normative spec | Spec user story US1 acceptance criteria |

## 2. Deferred Items validation (Constitution Principle VI gate)

Read from `spec.md § Scope Boundaries & Deferred Items`.

**Out of Scope (Permanent) — 3 items**: PIPC 유권해석 질의서 drafting, real DPA legal text, public Rekor-like transparency log for citizen sessions. Each has an on-spec justification. No tracking required.

**Deferred to Future Work — 7 items**:

| # | Item | Tracking Issue | Resolution |
|---|---|---|---|
| D1 | Full 8-tool mock implementation with live-fixture continuity | `NEEDS TRACKING` | Resolve via `/speckit-taskstoissues` |
| D2 | Full `/agent-delegation` endpoint implementation | `NEEDS TRACKING` | Resolve via `/speckit-taskstoissues` |
| D3 | Full Merkle audit chain implementation | `NEEDS TRACKING` | Resolve via `/speckit-taskstoissues` |
| D4 | PIPC 유권해석 질의서 draft | `NEEDS TRACKING` | Parallel legal-process track |
| D5 | Singapore IMDA MGF alignment deep dive | `NEEDS TRACKING` | Resolve via `/speckit-taskstoissues` |
| D6 | EU AI Act Annex III full obligation mapping | `NEEDS TRACKING` | Resolve via `/speckit-taskstoissues` |
| D7 | eGovFramework code-level pattern adoption | `NEEDS TRACKING` | Resolve via `/speckit-taskstoissues` |

**Unregistered-deferral scan**: Grep of `spec.md` for `separate epic|future epic|Phase [2-9]|v2|deferred to|later release|out of scope for v1` returned zero matches outside the Deferred Items table. Constitution VI gate = PASS.

## 3. Design-decision log (reference-mapped per Constitution Principle I)

Every decision below binds to a source in `docs/vision.md § Reference materials` or to a statutory / standards artifact cited verbatim in the spec.

### 3.1 Permission pipeline topology — Layer 3

- **Decision**: Permission pipeline remains deny-by-default with short-circuit auth-gate ahead of any adapter `handle()` body, mirroring `docs/tool-adapters.md § Layer 3 auth-gate contract`.
- **Primary reference**: OpenAI Agents SDK guardrail pipeline (`docs/vision.md § Reference materials`, Permission Pipeline row).
- **Secondary reference**: Claude Code reconstructed permission model (same row).
- **Rationale**: Guardrail-style composition lets KOSMOS wrap statutory checks (PIPA §17, §28-2) and standards checks (OWASP ASVS V4.1.5 fail-secure, NIST SP 800-207 Zero Trust policy decision point) as discrete steps without rewriting the pipeline. Preserves Constitution II.
- **Alternatives considered**: Inline per-adapter checks (rejected — violates DRY and Constitution II by letting each adapter author redefine "secure enough"), middleware-only (rejected — does not surface per-step decisions to the audit record the way a discrete-step pipeline does).
- **Spec binding**: FR-006, FR-007, FR-008.

### 3.2 Minimum-AAL table single source of truth

- **Decision**: One canonical `TOOL_MIN_AAL` table, published in the normative spec and replicated verbatim in registry code comments. `check_eligibility` = AAL2; `public_path` marker permits AAL1 only for rules-only evaluation over public inputs with zero PII either direction.
- **Primary reference**: NIST SP 800-63-4 (IAL/AAL/FAL framework). The withdrawn SP 800-63-3 is removed from every citation site per the consistency review.
- **Cross-binding**: Lanes 3 and 4 both depended on an AAL table; the consistency review pre-decided the `check_eligibility` = AAL2 + `public_path` resolution. This spec freezes that resolution.
- **Rationale**: A single table prevents drift. `public_path` preserves the public-goods use case (citizen asks "am I eligible?" with no PII) without weakening the default posture.
- **Alternatives considered**: Per-tool AAL with no shared table (rejected — drift risk), uniform AAL2 for all tools (rejected — overshoots `lookup`/`resolve_location` and harms usability for non-PII flows).
- **Spec binding**: FR-001, FR-002.

### 3.3 Audit retention — binding maximum

- **Decision**: 5 years, selected as the binding maximum of PIPA 안전조치 고시 §8 (2-year floor for access-log retention) and 전자정부법 §33 (5-year floor for electronic government records).
- **Rationale**: Both statutes mandate floors, not ceilings. Binding to the maximum simultaneously satisfies both without requiring per-tool retention branching. Audit integrity is unaffected by over-retention.
- **Alternatives considered**: 2-year PIPA-only retention (rejected — 전자정부법 non-compliance for any tool call that produces an electronic record of government service), per-tool retention matrix (rejected — operational complexity without benefit).
- **Spec binding**: FR-011.
- **Citations**: `01-korean-legal-baseline.md` § PIPA 안전조치 고시 §8; `05-public-sector-precedents.md` § 전자정부법 §33.

### 3.4 `sanitized_output_hash` + Merkle coverage declaration

- **Decision**: `ToolCallAuditRecord` carries both `output_hash` (always present) and `sanitized_output_hash` (nullable). A dedicated `merkle_covered_hash` enum field declares which hash the Merkle leaf covers — `sanitized_output_hash` when present, `output_hash` otherwise. Downstream verifiers do not need to re-examine the record body to know which variant is authoritative.
- **Primary reference**: RFC 9162 (Sunlight Merkle certificate transparency) for append-only log semantics; Google Trillian for implementation shape.
- **Rationale**: Raw output may contain PII that cannot be exported to auditors. Sanitized output has passed LLM-adjacent filtering. Binding the Merkle leaf to the sanitized form when available keeps the chain publicly verifiable; binding to raw otherwise keeps tamper-evidence for non-PII tools. The coverage declaration closes the consistency review's `output_hash` ambiguity.
- **Spec binding**: FR-009, FR-010; Edge Case "Output sanitization vs audit integrity".

### 3.5 PIPA role — `§26 수탁자` default + LLM-synthesis carve-out

- **Decision**: KOSMOS acts as 수탁자 (processor) by default for pre-synthesis tool-call processing. The LLM synthesis stage (combining citizen PII with ministry response text) is carved out as controller-level processing. Consent records carry both `dpa_reference` (for the §26 processor chain) and `synthesis_consent: bool` (for the carve-out).
- **Rationale**: Most tool-call processing has no independent purpose decision by KOSMOS — it is a pipe with evidentiary obligations, which matches §26(4) 수탁자 duties. Synthesis independently re-purposes PII to produce a bespoke artifact, which matches 처리자 (controller) duties. Separating the two consents aligns user expectations with legal posture and provides a clean DPA negotiation surface.
- **Parallel track**: PIPC 유권해석 질의서 (D4) not required for v1 spec acceptance but recommended before any production launch.
- **Spec binding**: FR-014, FR-015; Edge Case "LLM synthesis carve-out".
- **Citations**: auto-memory `project_pipa_role.md`; `01-korean-legal-baseline.md` § PIPA §26; `00-consistency-review.md` § PIPA role.

### 3.6 Delegation protocol — IETF/W3C only

- **Decision**: `/agent-delegation` endpoint family published as OpenAPI 3.0 skeleton citing only IETF RFCs (8628 device grant, 8693 token exchange, 9068 JWT profile, 7636 PKCE, 7662 introspection, 7009 revocation) and W3C recommendations (VC Data Model v2.0, DID Core). PASS / 공동인증서 TEE-binding is acknowledged and not bypassed; the protocol builds equivalent assurance from OAuth 2.1 + Verifiable Credentials.
- **Rationale**: Ministry partners must be able to adopt the protocol without KOSMOS-proprietary coupling. Citing only open standards avoids lock-in and maximizes adoptability.
- **Alternatives considered**: KOSMOS-specific token shape (rejected — coupling risk), SAML (rejected — mobile-first agent context favors OAuth 2.1), bespoke VC profile (rejected — unnecessary invention over W3C VC Data Model v2.0).
- **Spec binding**: FR-013, FR-014, FR-015, FR-016; SC-007.
- **Citations**: `04-identity-delegation.md` § OAuth 2.1 + VC; lane 4 OpenAPI draft.

### 3.7 Supply-chain posture — SLSA L3 gap + dual-format SBOM

- **Decision**: Scaffold `.github/workflows/sbom.yml` to emit both SPDX 2.3 and CycloneDX 1.6 from `pyproject.toml` + `uv.lock` on every push to `main` and every tag. Spec documents SLSA v1.0 L3 gap (current → target) and lists provenance artifacts KOSMOS commits to producing for a ministry pilot. Build-gate policy: SBOM divergence fails the build; recovery requires a signed regeneration with a reviewer-authored note.
- **Primary reference**: SLSA v1.0 (Levels 1-3), sigstore/cosign, Rekor transparency log, NIST SP 800-218 SSDF.
- **Rationale**: Dual-format SBOM maximizes ministry-reviewer tooling compatibility (some Korean public-sector scanners consume SPDX only, others CycloneDX only). Build-gate-on-divergence prevents silent supply-chain mutation; the signed-regeneration recovery path preserves audit integrity when dependencies legitimately change.
- **Spec binding**: FR-017, FR-018, FR-019; SC-005; Edge Case "SBOM divergence".
- **Citations**: `06-supply-chain-audit.md` § SLSA L3 gap, § SBOM dual-format.

### 3.8 Fail-closed registration invariant

- **Decision**: `ToolRegistry.register()` rejects any `GovAPITool` whose four new fields (`auth_level`, `pipa_class`, `is_irreversible`, `dpa_reference`) are missing, ambiguous, or inconsistent with `TOOL_MIN_AAL`. Cross-invariant: `pipa_class != non_personal → auth_level != public`. `pipa_class != non_personal → dpa_reference is not None`.
- **Primary reference**: OWASP ASVS 4.0 V4.1.5 (fail-secure); KOSMOS Constitution II.
- **Rationale**: Load-time failure prevents an under-documented adapter from ever reaching the permission pipeline. Cross-invariant binds statutory classification to auth strength and DPA documentation — eliminates the "PII tool with no DPA reference" class of bug.
- **Spec binding**: FR-003, FR-004, FR-005; SC-003.

### 3.9 Unified PR checklist extension

- **Decision**: Extend `docs/tool-adapters.md` with a minimum of 5 new unified PR checklist items spanning the six research-lane domains (Korean legal, international standards, LLM/tool threats, identity/delegation, public-sector precedent, supply-chain/audit). Contributors do not need lane-boundary prior knowledge to apply the checklist.
- **Rationale**: Without the checklist, the spec decays into aspirational prose. Unified framing ensures every adapter PR exercises every domain at least once, per US3 Acceptance Scenario 1.
- **Spec binding**: FR-020; US3.
- **Citations**: all six research lanes' PR-impact sections.

## 4. Constitution re-check after research

Re-evaluating all six principles against the decisions above.

- **I. Reference-Driven**: Every decision in §3 names a primary reference plus, where applicable, a statutory or standards artifact. PASS.
- **II. Fail-Closed**: §3.8 tightens registration; §3.1 preserves pipeline deny-by-default; §3.4 keeps tamper-evidence even for rejected calls. PASS.
- **III. Pydantic v2**: `ToolCallAuditRecord` uses pydantic v2 exclusively; GovAPITool extension stays in the existing v2 model. No `Any`. PASS.
- **IV. Government API Compliance**: No live calls introduced; existing quota/error-path rules untouched. PASS.
- **V. Policy Alignment**: §3.6 materially advances Principle 9 (OpenMCP/Open API); §3.5 advances Principle 5 (consent-based access); §3.2 and §3.8 advance Principle 8 (single-window trust model). PASS.
- **VI. Deferred Work Accountability**: §2 validates all 7 deferred items + 3 permanent OOS entries. Zero unregistered deferrals. PASS.

**Gate result**: all 6 principles remain PASS post-research. Proceed to Phase 1.
