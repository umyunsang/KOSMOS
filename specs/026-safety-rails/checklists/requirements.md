# Specification Quality Checklist — Epic #466 Safety Rails

**Feature**: `specs/026-safety-rails/spec.md`
**Checklist version**: 1.0
**Last validation**: 2026-04-17

This checklist validates `spec.md` against Spec Kit quality gates before plan/tasks/analyze stages proceed.

---

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
  - **Note**: Presidio / OpenAI Moderation / LiteLLM are named as dependency constraints under the Dependency License Posture subsection and Cross-Epic Contracts table — they are license and ownership facts, not implementation prescriptions. Functional requirements stay technology-agnostic where possible.
- [x] Focused on user value and business needs
  - P1 (PII redaction) protects citizens; P2 (injection defense) protects platform integrity; P3 (moderation) protects vulnerable users. Each priority leads with citizen-facing value, not engineering convenience.
- [x] Written for non-technical stakeholders
  - Legal citations (PIPA §26, 주민등록법 시행령 제2조 별표 1, ISO/IEC 7812, AI Action Plan 원칙8/9) ground the work in published reference material a policy reviewer can verify.
- [x] All mandatory sections completed
  - User Scenarios (P1/P2/P3 + Edge Cases), Requirements (FR-001 through FR-024), Key Entities (5), Success Criteria (SC-001 through SC-007), Assumptions (6), Scope Boundaries (5 permanent + 6 deferred) — all present.

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
  - Validation: `grep -n "NEEDS CLARIFICATION" spec.md` returns zero matches. All ambiguities resolved at spec-write time using KOSMOS norms (Apache-2.0 purity, fail-closed defaults, Pydantic v2 strict, NFR-003 cache stability).
- [x] Requirements are testable and unambiguous
  - Every FR names a concrete enforcement point (module path, function name, or decision outcome). Test fixtures in Validation Scenarios provide deterministic inputs for each FR cluster.
- [x] Success criteria are measurable
  - SC-001..SC-007 each name a numeric threshold (100% detection on 10 fixtures, zero false positives on 5 guardrail-pass queries, <100ms p95 redaction latency, zero PII in spans under the `gen_ai.safety.event` key) rather than qualitative language.
- [x] Success criteria are technology-agnostic (no implementation details)
  - SC phrasing: "detects X across N fixtures", "blocks X categories", "emits Y attribute" — outcomes, not mechanisms. Where a mechanism is unavoidable (OpenAI Moderation categories), the SC scopes to the category taxonomy rather than the vendor API.
- [x] All acceptance scenarios are defined
  - P1 has 3 Given/When/Then rows (tool-return redaction, step-3 preserved deny, re-registration idempotence). P2 has 3 rows (role-assumption, system-prompt-override, encoded payload). P3 has 2 rows (hate-speech block, 자살 예방 pass).
- [x] Edge cases are identified
  - 6 edge cases named: moderation outage (fail-open vs fail-closed), redaction of legitimate Korean names that resemble passport patterns, tool output larger than 1 MB, Presidio load failure, recursive nested JSON in tool output, Korean crisis hotline refusal message.
- [x] Scope is clearly bounded
  - Scope Boundaries section enumerates 5 permanent out-of-scope items and 6 deferred items. Each deferred row has a Target Epic and an explicit tracking marker (either Epic number or NEEDS TRACKING for the post-MVP Llama Guard ADR).
- [x] Dependencies and assumptions identified
  - Assumptions section lists Presidio pattern-only mode viability, `openai` SDK already present (FR-018 requires plan-phase verification), LiteLLM callback slot availability per #465, OTLP attribute acceptance per #501 policy, PIPA §26(4) carve-out interpretation stable.

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
  - FRs are clustered by layer (A/B/C/D + Observability + Configuration + Enum). Each cluster has a matching Validation Scenario fixture group (10 PII / 10 injection / 5 block / 5 pass) and a Success Criterion.
- [x] User stories cover primary flows
  - P1 covers the LLM02 Sensitive Information Disclosure path end-to-end (tool-return → redactor → LLM context). P2 covers the LLM01 Prompt Injection path (tool-return → detector → refusal envelope). P3 covers the moderation pre/post-call path (LiteLLM callback → OpenAI Moderation).
- [x] Feature meets measurable outcomes defined in Success Criteria
  - Each SC is reproducible from the Validation Scenarios fixtures. A plan-phase task can wire the fixtures into pytest and assert the SC thresholds directly.
- [x] No implementation leakage in requirements
  - Requirements name effects and boundaries (enum extension, span attribute, env key family) rather than class structure or algorithm details. Key Entities provide schema shape for downstream plan work without fixing method signatures.

## Cross-Epic Contract Compliance

- [x] Enum ownership clearly attributed
  - LookupErrorReason extension is code-owned (historical #507 cited via Refs, not Closes). PR-A scope is enum-only.
- [x] Span boundary respected
  - `gen_ai.safety.event` is the only new attribute key proposed to #501. Spec explicitly forbids raw PII or raw tool-output bytes in span attributes.
- [x] Env key ownership respected
  - 4 `KOSMOS_SAFETY_*` keys proposed as a follow-up note to #468; spec forbids hand-editing `docs/configuration.md` in this epic.
- [x] LiteLLM config ownership respected
  - Hook registration is code-only; spec forbids modifying `infra/litellm/config.yaml` in this epic.
- [x] Permission layer boundary respected
  - Step 3 PII logic is strengthened (via single-source-of-truth refactor) but authz flow is unchanged. #16 and #20 remain the permission-gauntlet owners.

## License Posture

- [x] Apache-2.0 purity preserved in MVP path
  - Primary guardrail is OpenAI Moderation (Apache-2.0 compatible via `openai` SDK).
- [x] Llama Guard 3 deferral documented
  - Dependency License Posture subsection names Option A (accepted) vs. Option B (deferred) with explicit Llama 3.2 Community License blockers (§5(c) indemnification + "Built with Llama" attribution).
- [x] Post-MVP ADR requirements enumerated
  - If Option B is later adopted, the spec lists: feature flag off by default, separate NOTICE_LLAMA.md, README license statement revision.

## No-Hardcoding Compliance (3x rule)

- [x] No static keyword blocklist proposed
  - Moderation is delegated to OpenAI Moderation API; no in-repo keyword list.
- [x] No static salvage regex proposed
  - PII detection delegated to Presidio `PatternRecognizer` fed by `_patterns.py` (the canonical regex registry, not a salvage layer).
- [x] No hand-rolled PII tokenizer proposed
  - Presidio handles tokenization boundaries; spec forbids tokenizer reimplementation.

## Single Source of Truth

- [x] `_PII_PATTERNS` canonical location defined
  - `src/kosmos/safety/_patterns.py` is the single source. `step3_params.py` imports from it.
- [x] Duplicate-elimination verification planned
  - FR-002 requires `grep -rn "_PII_PATTERNS" src/` to return matches only in `_patterns.py` and import sites post-implementation.

---

## Validation Result

**Status**: PASS (first iteration)

All quality gates satisfied. Zero `[NEEDS CLARIFICATION]` markers. Cross-Epic contracts explicit. License posture grounded in Llama 3.2 Community License text. No-hardcoding rule honored via Presidio delegation. Single source of truth for PII patterns defined.

**Ready for**: `/speckit-plan`.
