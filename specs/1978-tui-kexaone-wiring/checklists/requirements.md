# Specification Quality Checklist: TUI ↔ K-EXAONE wiring closure

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-04-27
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — verified: spec describes "frame schema", "tool invocation event", "harness boundary" abstractly without naming Python, TS, Pydantic, Bun, or specific JSON Schema constructs in the requirements/criteria sections; technology terms appear only in the Assumptions block where they document upstream environmental contracts
- [x] Focused on user value and business needs — verified: every user story is framed from the citizen's perspective; SC-007 ties directly to KSC 2026 demo, the externally visible business outcome
- [x] Written for non-technical stakeholders — verified: a government program officer reading the User Stories + Success Criteria can understand exactly what the citizen will see and what "done" means without any code knowledge
- [x] All mandatory sections completed — User Scenarios & Testing, Requirements, Success Criteria, Assumptions, Scope Boundaries & Deferred Items all present; Key Entities included since data is involved

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — verified by `grep -c 'NEEDS CLARIFICATION' spec.md` returning 1 occurrence which is the literal "NEEDS TRACKING" placeholder in the deferred-items table (resolved later by `/speckit-taskstoissues` per template instruction); zero `[NEEDS CLARIFICATION:` blocking markers
- [x] Requirements are testable and unambiguous — every FR-NNN names a concrete observable system behaviour with a specific actor and a specific outcome; e.g., FR-009 enumerates the exact three button labels of the consent modal
- [x] Success criteria are measurable — every SC-NNN includes a number (10s, 25s, 1s, 100%, 20 trials, 30-minute session, zero hits, four frame types) or a binary pass/fail demo condition (SC-007 stage rehearsal recording)
- [x] Success criteria are technology-agnostic — verified: SCs describe what the citizen experiences (latency-to-first-chunk, modal appearance, demo-runs-on-stage); no SC mentions Python, Bun, TypeScript, frame names, or class names
- [x] All acceptance scenarios are defined — Given/When/Then format used for every user story (3 stories × 3 scenarios = 9 acceptance paths total)
- [x] Edge cases are identified — 8 distinct edge cases documented covering process-failure, stream-interruption, schema-violation, queueing, empty-input, resume-after-restart, defence-in-depth Anthropic-call regression, and revoked-consent
- [x] Scope is clearly bounded — Scope Boundaries section explicitly lists 5 permanent out-of-scope items and 5 deferred items with their target epics; this is what makes the epic refusable to add ad-hoc work
- [x] Dependencies and assumptions identified — 7 assumptions covering env tokens, host platform, prior onboarding, network reachability, adapter readiness, and reference-source priority hierarchy

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria — every FR is exercised by at least one acceptance scenario or success criterion: FR-001/002 ↔ Story 1 / SC-001 / SC-005; FR-005/006/007/008 ↔ Story 2 / SC-002; FR-009/010/011/012 ↔ Story 3 / SC-003; FR-004 ↔ Story 1 Scenario 3 / SC-004; FR-013/014 ↔ SC-006; FR-015/016 ↔ Edge Cases / SC-005
- [x] User scenarios cover primary flows — Story 1 covers no-tool conversational baseline, Story 2 covers tool-invocation primary flow, Story 3 covers permission-gate primary flow; together these are the three real citizen paths
- [x] Feature meets measurable outcomes defined in Success Criteria — SC-001…SC-007 collectively decide success; each has a verification method (sample of N trials, network log filter, demo rehearsal recording)
- [x] No implementation details leak into specification — verified that no FR mentions `stdio.py`, `frame_schema.py`, `Pydantic`, `Ink`, `Bun.spawn`, or class names; all references go to abstractions ("harness boundary", "frame", "registered tool")

## Notes

- This spec deliberately does not specify *how* the wiring closes. The decision between "extend `UserInputFrame` schema" vs. "introduce a new ChatRequestFrame arm" is implementation detail and belongs in `plan.md` (next step). Citizens do not see the frame name; they see whether their question got answered and whether their consent was honoured.

- The diagnostic findings from 2026-04-27 (the Epic #1978 issue body) are evidence of *why* this spec exists, but the spec itself is forward-looking only. Reviewers wanting the diagnostic detail should read the Epic body or the `feedback_runtime_verification` memory.

- Memory `feedback_check_references_first` mandates that conflicts between the CC 2.1.88 source map, project memory, and `docs/vision.md` resolve in favour of the source map first, memory second, vision third. The Assumptions section names this hierarchy explicitly so downstream Plan and Tasks phases cannot drift back to vision.md as primary reference (which is exactly the failure mode that produced this epic).

- All five Deferred Items have `NEEDS TRACKING` placeholders that will be replaced with concrete sub-issue or successor-Epic numbers during `/speckit-taskstoissues`, satisfying constitution Principle VI without making `/speckit-specify` block on issue-creation IO.

## Validation Result

**Status**: ✅ All checklist items pass on first iteration. No re-runs required.

**Iterations**: 1 / 3 max
