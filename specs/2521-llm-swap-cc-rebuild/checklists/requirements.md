# Specification Quality Checklist: LLM Swap-Surface CC Byte-Copy + Bounded Swap Migration

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-05-01 (revised after user methodology directive)
**Feature**: [spec.md](../spec.md)

## Methodology Compliance (this Epic-specific)

- [x] Methodology section present and aligns with AGENTS.md CORE THESIS ("KOSAX = CC + 2 swaps") and memory `feedback_cc_source_migration_pattern`
- [x] Step A (byte-copy) clearly defined with SHA-256 verification requirement
- [x] Step B (bounded swap) categories enumerated and exhaustive (4 categories: llm-provider / tool-domain / anti-anthropic-1p / identifier-rename)
- [x] Step C (KOSAX-only behavior-mirror) defined for files lacking direct CC source
- [x] Step D (audit reproducibility) defined with executable script

## Content Quality

- [x] Implementation specifics (CC reference paths, SHA-256, line ranges) are intentionally cited because the Epic IS a code-rebuild against a code reference. The "no implementation details" rule applies to product features for non-technical stakeholders; for an audit/rebuild Epic the maintainer audience is the stakeholder.
- [x] Focused on user value (P1 = citizen-visible thinking; P1 = systemic prevention; P2 = reproducibility; P3 = audit closure)
- [x] All mandatory sections completed (User Scenarios, Requirements, Success Criteria, Assumptions, Scope Boundaries)

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous (each FR maps to a SC)
- [x] Success criteria are measurable (SHA match, audit script exit code, test count delta, dependency count delta, file SHA diff)
- [x] All acceptance scenarios are defined per User Story
- [x] Edge cases identified (6 cases covering OAuth carryover, model ID rename, signature_delta byte-copy, KOSAX-only files, byte-copy reintroducing previously-deleted code)
- [x] Scope clearly bounded (Out of Scope + Deferred)
- [x] Dependencies and assumptions identified

## Procedure Mapping (FR-001 table)

- [x] All 4 in-scope files classified into Procedure A or B
- [x] Each Procedure-A file has a CC source path
- [x] Each Procedure-B file has a CC analog path with line range
- [x] Mapping table is in spec body for transparency

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria (FR ↔ SC mapping)
- [x] User scenarios cover primary flows (citizen + maintainer + auditor + cleanup-closer)
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] Methodology is reproducible — replay script (FR-013) demonstrated

## Notes

- **Methodology change** (2026-05-01 user directive): replaced "audit-and-fix" with "byte-copy + bounded swap". Every diff between KOSAX and CC must now justify itself by category; unjustified diffs revert.
- **Step A byte-copy is destructive** for the Procedure-A files: it overwrites the current KOSAX state. Justified state (e.g., the `_ensure_tool_registry` register fix from 2026-05-01) is REINTRODUCED via Step B / Step C swap commits with retroactive labeling. Nothing is silently lost.
- **The 4 cleanup-needed entries within scope** of this Epic resolve through one of two paths: (a) byte-copy reverts to CC and the cleanup is moot, or (b) Step B swap re-applies the deletion with `SWAP/anti-anthropic-1p` justification.
- **`scripts/llm_swap_parity_audit.sh`** (FR-004) is the canonical CI gate for this Epic and successor Epics that touch swap-surface files.
- **Replay script `specs/2521-llm-swap-cc-rebuild/scripts/replay_rebuild.sh`** (FR-013) preserves the rebuild as a reproducible procedure rather than a one-time event that decays.
