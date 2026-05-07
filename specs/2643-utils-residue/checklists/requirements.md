# Specification Quality Checklist: Epic G — Utils 잔존 정리

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-05-03
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — TypeScript specifics only in functional requirements (necessary for byte-copy fidelity scope), CC reference paths cited as canonical baseline
- [x] Focused on user value and business needs — US1/US2 are headless --print SDK + 시민 한국어 입력 user-facing surfaces
- [x] Written for non-technical stakeholders — Background section ties Epic to KOSAX CORE THESIS in plain language
- [x] All mandatory sections completed (Background, Audit 출처, Pre-execution table, User Scenarios, Requirements, Success Criteria, Assumptions, Scope Boundaries)

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous (FR-001 ~ FR-020 each cite measurable conditions)
- [x] Success criteria are measurable (SC-001 ~ SC-008 all measurable: file existence, LOC counts, diff counts, test pass counts, p95 latency, PNG keyframe counts)
- [x] Success criteria are technology-agnostic where the surface allows; byte-copy fidelity inherently couples to file paths (justified by CORE THESIS)
- [x] All acceptance scenarios are defined (US1: 4 scenarios, US2: 5 scenarios, US3: 5 scenarios, US4: 3 scenarios)
- [x] Edge cases are identified (5 edge cases covering rate-limit, ISO short-circuit, secureStorage absence, Path B callsite, K-EXAONE wrong ISO)
- [x] Scope is clearly bounded (Out of Scope: 4 items, Deferred to Future Work: 5 items, all with tracking)
- [x] Dependencies and assumptions identified (7 assumptions covering queryHaiku stability, FriendliAI tier, cli/print.ts byte-copy state, .env policy, Path B precedent, bun test baseline, pytest baseline)

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (every FR-XXX maps to at least one US scenario or SC)
- [x] User scenarios cover primary flows (4 user stories spanning 4 audit decisions)
- [x] Feature meets measurable outcomes defined in Success Criteria (SC-001 ~ SC-008 each tied to FR group)
- [x] No implementation details leak into specification beyond byte-copy/swap-1 file paths (these are mandatory for the Epic's byte-identical fidelity contract)

## Notes

- Epic G is intentionally "audit jail-break" scoped: every requirement traces back to `specs/cc-migration-audit/scope-S9-utils.md` row + `decisions.md § S9 Utils` row.
- Path B precedent (Spec 2295 PR #2364 commit c6747dd) is cited to remove ambiguity about US3 module-split pattern.
- ADR-009 file path is forward-declared (FR-017) — the next available ADR slot per `docs/adr/` listing (existing range ADR-001 ~ ADR-008).
- CORE THESIS hard rule "byte-identical default" forces the spec to allow swap-1 deviation (queryHaiku target = K-EXAONE) explicitly via FR-002 / FR-007 / FR-016.
