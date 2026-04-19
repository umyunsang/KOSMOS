# Implementation Plan: TUI Component Catalog — CC → KOSMOS Verdict Matrix + Brand-System Doctrine

**Branch**: `034-tui-component-catalog` | **Date**: 2026-04-20 | **Spec**: [`specs/034-tui-component-catalog/spec.md`](./spec.md)
**Input**: Feature specification from `/specs/034-tui-component-catalog/spec.md`
**Parent Epic**: #1310 (OPEN, label `epic`) · **Initiative**: #2 (Phase 2 — Multi-Agent Swarm)

## Summary

Epic M produces the **authoritative verdict matrix** for porting Claude Code's 389 `src/components/` files into the KOSMOS TUI, plus the **brand-system doctrine** (metaphor + token naming) that every downstream design-concerned Epic (H / J / K / L / E) must cite as source-of-truth. Deliverables are **four Markdown documents + one tokens-type-surface edit**:

1. `docs/tui/component-catalog.md` — 389 rows across 31+ families, one verdict per file (PORT / REWRITE / DISCARD / DEFER), each with owning-Epic + target-path + evidence.
2. `docs/tui/accessibility-gate.md` — per PORT/REWRITE row, WCAG 2.1 AA subset + KWCAG 2.2 notes + IME flag + contrast constraint.
3. `docs/design/brand-system.md` — 10 sections; §1 (brand metaphor) + §2 (token naming doctrine) authored ≥ 500 words each; §3–§10 placeholder + owner pointer only.
4. `tui/src/theme/tokens.ts` — type surface only; no banned patterns; NO palette value changes (Epic H owns values).
5. Grep CI gate specification at `contracts/grep-gate-rules.md` (impl deferred as a Task under Epic M).

**Technical approach**: pure documentation + small type-surface edit. No Python modules, no TUI components, no dependency changes. Enumeration uses `find` at the pinned CC sourcemap commit `a8a678c`. Phase-0 research.md documents every design decision against `.specify/memory/constitution.md`, `docs/vision.md § Reference materials`, and `docs/adr/ADR-006-cc-migration-vision-update.md`. Phase-1 contracts/ hold the machine-checkable schema rules for each artifact.

## Technical Context

**Language/Version**: N/A for runtime code (documentation-only Epic). `tui/src/theme/tokens.ts` is TypeScript 5.6+ under Bun v1.2.x (existing Spec 287 stack — not extended).
**Primary Dependencies**: None (zero runtime dependency additions; AGENTS.md hard rule satisfied trivially).
**Storage**: N/A — deliverables are Markdown files and a TypeScript type surface. No database, no cache, no filesystem state.
**Testing**: `/speckit-analyze` consumes the `contracts/*.md` invariants (CatalogRow invariants I3–I6, BSS-01..BSS-09, AG-01..AG-06) as lint rules. Grep CI gate has its own test fixtures (contracts/grep-gate-rules.md §5) but its implementation is deferred. No pytest additions.
**Target Platform**: GitHub (Sub-Issues API v2 consumer), local filesystem markdown rendering, future PR-time grep CI gate on GitHub Actions.
**Project Type**: documentation + governance artifact (Spec Kit doc-spec — analogous to Specs 024 and 025 which also shipped primarily as normative docs).
**Performance Goals**: Readability SC-008 — Phase-2 newcomer specs their Epic's Tasks from catalog + ADR-006 + sourcemap alone in < 30 minutes.
**Constraints**:
- Zero source-code file modifications outside `tui/src/theme/tokens.ts` type surface (FR-030, FR-031).
- ≤ 90 Task sub-issues under Epic M excluding `[Deferred]`-prefixed (FR-025, SC-007).
- All owning-Epic values ⊆ `{B, C, D, E, H, I, J, K, L, M}` literal set; closed Epics (B, A) handled per research §R3 (re-parent to M).
- §3–§10 of brand-system.md are scope-violation-protected (FR-014, FR-034).
**Scale/Scope**: 389 catalog rows + up to ~90 generated Task sub-issues + 10 brand-system sections + up to ~275 accessibility-gate rows (only PORT/REWRITE populate; DISCARD/DEFER do not).

## Constitution Check

*GATE: Passed at Phase 0. Re-evaluated at end of Phase 1. See `research.md § 7` for original pass; this section captures the post-Phase-1 re-check.*

| Principle | Gate | State | Evidence |
|---|---|---|---|
| I. Reference-Driven Development | Every design decision mapped to a concrete reference | ✅ PASS | `research.md § 1` table (13 decisions → 13 references). Primary migration source = CC sourcemap (Constitution §I); secondary = Gemini CLI & claw-code PARITY.md. ADR-006 Part D is cited for every DISCARD verdict shape. |
| II. Fail-Closed Security (NON-NEGOTIABLE) | Adapter defaults, permission bypass-immune | ✅ N/A | No tool adapters introduced; no permission checks added. Catalog rows that flag citizen-facing text input propagate the IME + permission constraints to the owning Epic, not to this PR. |
| III. Pydantic v2 Strict Typing (NON-NEGOTIABLE) | No `Any`, schemas required | ✅ N/A | No new tool I/O schemas introduced. `data-model.md` documents logical entity shapes consumed by `/speckit-analyze` as lint rules; not Python classes. |
| IV. Government API Compliance | No live API in CI, quota tracking, fail-closed defaults | ✅ N/A | No API touched. |
| V. Policy Alignment | PIPA, 공공AX Principles 5/8/9, permission gauntlet | ✅ PASS | §1 of brand-system.md explicitly grounds the KOSMOS metaphor in Principle 8 (single conversational window). FR-021 + FR-022 propagate PIPA-adjacent safety constraints (IME composition, contrast) to downstream Epics. |
| VI. Deferred Work Accountability | Every deferral tracked, 0 unregistered | ✅ PASS | `research.md § 3` — 16 deferred items; 10 tracked to existing issues; 6 `NEEDS TRACKING` to be backfilled by `/speckit-taskstoissues`. 0 unregistered deferral patterns (regex scan in §3.3). |
| ADR-006 Part D-3 | KOSMOS-original surfaces out of scope | ✅ PASS | FR-033 codifies the exclusion; catalog enumeration is limited to `.references/claude-code-sourcemap/restored-src/src/components/`. |
| AGENTS.md Issue hierarchy | Initiative → Epic → Task; Sub-Issues API v2 `subIssues`/`parent` | ✅ PASS | FR-023 uses `addSubIssue` mutation; FR-025 honors 90-cap (auto-memory lesson from #287 orphan-Task incident). Closed-Epic handling (research §R3) re-parents to M to avoid reopen. |
| AGENTS.md GraphQL-only tracking | No REST/CLI list fallback for state claims | ✅ PASS | All Epic state facts verified via `gh api graphql` in `research.md § 2.3`. |
| AGENTS.md zero-dep rule | No new deps outside spec-driven PR | ✅ PASS | Zero additions. |
| AGENTS.md English-only source text | Korean allowed only in domain data | ✅ PASS | All source text English. Korean strings appear only inside §1 brand-metaphor prose (`은하계`), KWCAG standard name (`한국 접근성 지침 2.2`), and ministry names where domain-correct (e.g., `출산 보조금`). |

**No violations to justify** — Complexity Tracking section is intentionally empty.

## Project Structure

### Documentation (this feature)

```text
specs/034-tui-component-catalog/
├── plan.md                 # This file (/speckit-plan output)
├── spec.md                 # Input (authored pre-plan)
├── research.md             # Phase 0 — references, deferred validation, codebase facts, NEEDS CLARIFICATION resolutions
├── data-model.md           # Phase 1 — logical entity shapes (CatalogRow, TokenName, BrandSystemSection, AccessibilityGateRow, TaskSubIssue, EvidenceCitation)
├── quickstart.md           # Phase 1 — future-Epic author / Brand Guardian / Accessibility Auditor quickstarts
├── contracts/
│   ├── catalog-row-schema.md        # docs/tui/component-catalog.md row format + validation (I3–I6)
│   ├── token-naming-grammar.md      # MetaphorRole BNF + BAN-01..BAN-07 regex rules
│   ├── brand-system-sections.md     # docs/design/brand-system.md layout + BSS-01..BSS-09 invariants
│   ├── accessibility-gate-rows.md   # docs/tui/accessibility-gate.md row format + AG-01..AG-06
│   └── grep-gate-rules.md           # Brand Guardian CI gate spec (impl deferred to post-verdict Task)
└── checklists/             # pre-existing (from /speckit-checklist)

(After `/speckit-tasks` runs:)
└── tasks.md                # Phase 2 output — NOT created by /speckit-plan
```

### Source Code (repository root)

This Epic modifies the KOSMOS tree minimally. Structure decision: **documentation-only Epic with a narrow type-surface edit**.

```text
# NEW files — created by this Epic's PR
docs/
├── tui/
│   ├── component-catalog.md          # 389 rows; see contracts/catalog-row-schema.md
│   └── accessibility-gate.md         # per PORT/REWRITE; see contracts/accessibility-gate-rows.md
└── design/
    └── brand-system.md               # 10 sections; see contracts/brand-system-sections.md

# MODIFIED file — type surface only (if needed for catalog examples; otherwise untouched)
tui/src/theme/
└── tokens.ts                         # add NEW token names matching MetaphorRole grammar;
                                      # leave existing CC-legacy tokens untouched (allow-listed)

# DEFERRED files — NOT created by this Epic (tracked as Deferred Items)
# .github/workflows/brand-guardian.yml  → Deferred row 11, post-verdict Task under Epic M
# tui/src/theme/.brand-guardian-allowlist.txt  → regenerated at workflow-impl time

# UNCHANGED directories (governed out by FR-030, FR-031, FR-033)
src/kosmos/**                         # untouched — KOSMOS-original per ADR-006 Part D-3
tui/src/components/**                 # untouched — per-component ports are owning-Epic Tasks
tui/src/theme/dark.ts, default.ts, light.ts  # untouched — palette values are Epic H #1302 territory
```

**Structure Decision**: Single-project Markdown deliverables under existing `docs/` tree (creating `docs/tui/` new directory). The one source-code edit is scoped to `tui/src/theme/tokens.ts` **type surface only** — same file already exists (Spec 287 legacy), and modifications stay within the TypeScript `type ThemeToken = { … }` block per FR-030. No Python files, no new `src/kosmos/` additions. No `pyproject.toml` or `package.json` edits.

## Phase 0: Outline & Research — summary

Executed. Output: `research.md`. Key findings:

- **Reference mapping** ✅: 13 design decisions → 13 concrete reference citations (CC sourcemap + ADR-006 + claw-code PARITY.md + Constitution §I).
- **Codebase facts verified** ✅: 389 files; 31 subdirectories (minor spec prose says 30 — acceptable); CC sourcemap pinned at `a8a678c`; KOSMOS HEAD at `34c48f4`; `docs/tui/` does NOT exist yet (plan creates it).
- **Epic state verified via GraphQL** ✅: B #1297 CLOSED, A #1298 CLOSED; all others OPEN. Closed-Epic edge case handled (research §R3 — re-parent REWRITE Tasks to Epic M).
- **Deferred-item validation** ✅: 16 items; 10 tracked; 6 `NEEDS TRACKING` awaiting `/speckit-taskstoissues`. 0 unregistered deferrals.
- **6 NEEDS CLARIFICATION items resolved** (R1–R6): catalog granularity, 30-vs-31 discrepancy, closed-Epic owning, sub-issue budget allocation, grep gate location, §10 owner tracking.

## Phase 1: Design & Contracts — summary

Executed. Outputs:

- `data-model.md` — 11 entities with 17 invariants (I1–I17), relationships, state transitions.
- `contracts/catalog-row-schema.md` — header format + row columns + closed-Epic rule + aggregation rule + downstream Epic checklist appendix (FR-029).
- `contracts/token-naming-grammar.md` — BNF grammar + BAN-01..BAN-07 regex + CC-legacy allow-list convention + Brand Guardian rejection playbook.
- `contracts/brand-system-sections.md` — 10-section layout + BSS-01..BSS-09 invariants + §3–§10 exact placeholder text + scope-violation trap for `/speckit-analyze`.
- `contracts/accessibility-gate-rows.md` — WCAG closed set + row format + citizen-facing family list + IME-flag rule + AG-01..AG-06 invariants + Epic H handoff line.
- `contracts/grep-gate-rules.md` — Brand Guardian CI gate spec + legacy allow-list bootstrap + pseudocode + fixture plan + handoff to the deferred impl Task.
- `quickstart.md` — future-Epic author, Brand Guardian, Accessibility Auditor, and reviewer quickstarts.

Agent context update (`update-agent-context.sh claude`) will be re-run after this plan.md is written so the "Active Technologies" block in `CLAUDE.md` picks up "N/A — documentation-only Epic".

## Phase 2: Ready for `/speckit-tasks`

`tasks.md` will be generated by `/speckit-tasks` (NOT by this command). Expected task structure:

- Authoring Tasks for the 4 Markdown deliverables (one per doc).
- Enumeration Task for the 389-row catalog (family-by-family pass over 31 subdirectories + root-bin pass for 113 files).
- Brand-system §1, §2 authoring Tasks (each ≥ 500 words).
- Type-surface edit Task on `tui/src/theme/tokens.ts` (minimal, additive only).
- Post-verdict Task for grep CI gate implementation (Deferred row 11 backfill).
- `/speckit-analyze` invariant-check validations folded into the individual authoring Tasks' acceptance criteria.

Expected Task sub-issue count at `/speckit-taskstoissues` time: ~15–25 for Epic M itself + N for non-M REWRITE verdicts whose owning Epics absorb them (NOT counted against M's 90-cap per FR-026).

## Complexity Tracking

> Fill only if Constitution Check has violations to justify.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

No violations.
