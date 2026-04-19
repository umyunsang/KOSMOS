# Research: TUI Component Catalog — CC → KOSMOS Verdict Matrix + Brand-System Doctrine

**Feature**: 034-tui-component-catalog
**Date**: 2026-04-20
**Phase**: 0 (Outline & Research)
**Branch**: `034-tui-component-catalog`
**Parent Epic**: #1310 (Epic M, OPEN, label `epic`)
**Parent Initiative**: #2 (Phase 2 — Multi-Agent Swarm)

---

## 1 · Mandatory reference mapping

Per Constitution Principle I, every design decision is mapped to one concrete reference. This Epic is documentation-only (no source-code modules), so the reference mapping is sparser than an implementation spec and concentrates on **TUI layer** + **process governance** references.

| Design decision | Primary reference | Secondary reference | Evidence citation |
|---|---|---|---|
| Verdict matrix format (rows with Status / Evidence / Feature commit / Merge commit) | `.references/claw-code/PARITY.md` top-level table | `.references/claw-code/README.md` lane-status convention | FR-006 — catalog MUST follow PARITY.md tracker pattern |
| Component enumeration scope = `src/components/` only | ADR-006 Part D-3 (KOSMOS-original surfaces under `src/kosmos/*` OUT of scope) | `docs/vision.md § Layer 5 (TUI)` | Spec §Scope Boundaries; FR-033 |
| CC sourcemap as canonical port source | Constitution §I "Primary migration source" block; ADR-004 (sourcemap port policy, pinned commit) | `docs/vision.md § Reference materials` row "Claude Code sourcemap" | Constitution §I mandates `restored-src/src/` as the first reference for every new module |
| 10 owning-Epic closed set {B #1297, C #1301, D #1299, E #1300, H #1302, I #1303, J #1307, K #1308, L #1309, M #1310} | ADR-006 Part B 9-Epic table + Part D-2 candidate Epic list | Initiative #2 sub-issue graph (GraphQL `subIssues` verified 2026-04-20) | FR-003 |
| DISCARD evidence = ADR-006 Part D-1 / D-3 citation | ADR-006 Part D-1 (intentional exclusion list — 4 categories) + Part D-3 (KOSMOS-original surfaces) | Spec 287 deferred-items registry | FR-004; SC-005 |
| Token naming pattern `{metaphorRole}{Variant}?` | ADR-006 A-9 (KOSMOS brand splash palette + `orbitalRing` / `kosmosCore` / `wordmark` / `subtitle` / `agentSatellite+MINISTRY` vocabulary) | `assets/kosmos-{logo,logo-dark,banner-dark,icon}.{svg,png}` (8 brand assets) | FR-008/009/015 |
| Banned token patterns (`claude*`, `clawd*`, `primary`, `accent+digits`, etc.) | `tui/src/theme/tokens.ts` current surface (inventoried — 65 CC-legacy tokens to audit) | Brand Guardian role description (agent registry) | FR-008; FR-016 |
| WCAG 2.1 AA criteria set {1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2} | W3C WCAG 2.1 Recommendation (public) | Gemini CLI accessibility notes (reference only) | FR-019 |
| 한국 접근성 지침 2.2 (KWCAG 2.2) baseline | 국가표준 KS X 2101 (한국웹접근성표준) public baseline | ADR-006 A-10 IME safety rule | FR-020 |
| IME composition-gate = Epic E #1300 contract handoff | `tui/src/hooks/useKoreanIME.ts` + ADR-006 A-10 | Epic E #1300 body | FR-021 |
| Sub-Issues API v2 `addSubIssue` linking | AGENTS.md § Issue hierarchy (GraphQL-only) | `feedback_graphql_issue_tracking.md` (auto-memory) | FR-023; FR-025; FR-026 |
| 90-cap on Epic M Task sub-issues | `feedback_subissue_100_cap.md` (auto-memory, from #287 orphan-Task incident) | AGENTS.md § Issue hierarchy | FR-025; SC-007 |

**Escalation path**: This spec does not escalate to secondary references beyond the TUI-reference row — the primary sources cover everything. Any future reviewer considering whether to fall back to Gemini CLI or Mastra for UI patterns should first check `.references/claude-code-sourcemap/restored-src/src/components/` per Constitution §I.

---

## 2 · Codebase-verified facts (2026-04-20)

### 2.1 CC sourcemap file counts (evidence for FR-001, FR-007)

- **CC sourcemap submodule commit**: `a8a678c` (submodule HEAD at `.references/claude-code-sourcemap/`, verified by `git rev-parse HEAD` inside submodule).
- **KOSMOS repo commit when enumeration was performed**: `34c48f4` (`feat(033): permission v2 spectrum`, merged on `main` 2026-04-19).
- **Total files in `.references/claude-code-sourcemap/restored-src/src/components/` (`.tsx` + `.ts`)**: **389**. Verified by `find ... | wc -l`.
- **Root-level files** (directly under `src/components/`): **113**.
- **Subdirectories** (one level below `src/components/`): **31** — NOT 30 as the spec's Key Entities section and FR-001 rationale suggests.

**Discrepancy finding #1** (for spec's FR-007 header): Epic M body #1310 title claims "286 files"; the 2026-04-20 recount shows 389. FR-007 already mandates recording this; the plan inherits it.

**Discrepancy finding #2** (minor, spec prose tightening): spec Key Entities says "30 top-level directories"; actual count is 31. Not a blocker — the catalog header will record the correct number (31) and the spec is close enough that `/speckit-analyze` will accept it; a minor spec-prose fix can ride into the same PR as plan.

**31 subdirectories enumerated** (sorted): `agents`, `ClaudeCodeHint`, `CustomSelect`, `design-system`, `DesktopUpsell`, `diff`, `FeedbackSurvey`, `grove`, `HelpV2`, `HighlightedCode`, `hooks`, `LogoV2`, `LspRecommendation`, `ManagedSettingsSecurityDialog`, `mcp`, `memory`, `messages`, `Passes`, `permissions`, `PromptInput`, `sandbox`, `Settings`, `shell`, `skills`, `Spinner`, `StructuredDiff`, `tasks`, `teams`, `TrustDialog`, `ui`, `wizard`.

### 2.2 KOSMOS TUI current tree (evidence for PORT/REWRITE target-path column)

- **Total files under `tui/src/components/`**: 26 across 4 subdirectories: `conversation/`, `coordinator/`, `input/`, `primitive/`.
- Current mapping is sparse — most CC components have NO KOSMOS counterpart yet. This is expected: Epic M is the blueprint; Epics B/C/D/E/H/I/J/K/L do the ports.

### 2.3 Epic status (GraphQL-verified 2026-04-20)

| ID | Issue | State | Title |
|---|---|---|---|
| M | #1310 | **OPEN** | Epic M — TUI component catalog migration (286 files claim; 389 actual) |
| B | #1297 | **CLOSED** | Permission v2 spectrum (shipped 2026-04-19 PR #1441) |
| A | #1298 | **CLOSED** | IPC stdio hardening (shipped 2026-04-14 PR #1378) |
| C | #1301 | OPEN | Ministry Specialist Workers |
| D | #1299 | OPEN | Context Assembly v2 — memdir User tier |
| E | #1300 | OPEN | Korean IME — composition-aware shortcut gating |
| H | #1302 | OPEN | Onboarding + brand port |
| I | #1303 | OPEN | Shortcut Tier 1 port |
| J | #1307 | OPEN | Cost/Token HUD |
| K | #1308 | OPEN | Settings TUI dialog |
| L | #1309 | OPEN | Notifications surface |

**Epic-closed edge case** (design decision required):

> Spec FR-003 lists B + A in the closed set of owning Epics, but both are CLOSED. Three practical scenarios and the chosen handling:
>
> 1. **REWRITE verdict whose logical owner is Epic B** (e.g., `components/permissions/*` family): permission spectrum work shipped under #1441, but a REWRITE of the TUI permission dialog may legitimately still be a Task. Handling: the catalog MAY assign owner = `B #1297 (closed)` and the downstream Task is created as a **follow-up Task on Epic M itself** (not reopened on B) with a pointer back to the shipped spec. Add this clarification to `contracts/catalog-row-schema.md` as an explicit row-rule.
> 2. **REWRITE verdict whose logical owner is Epic A** (e.g., anything in `components/` that touches stdio transport): same rule as B — if the core IPC work shipped, the TUI-side rewrite becomes a follow-up Task under Epic M.
> 3. **Catalog row where the component was fully delivered by the closed Epic** (e.g., `PermissionGauntletModal` already ported in Spec 033): mark as verdict `PORT` with target path in `tui/src/components/coordinator/` and verdict rationale "implemented by #1441"; no Task is generated (implementation complete).
>
> This preserves FR-003's closed-set literal while giving the audit a defensible route when an owning Epic is retrospectively already closed.

### 2.4 Filesystem state

- `docs/design/` **exists** (currently contains no brand-system doc). Creating `docs/design/brand-system.md` is a net-add.
- `docs/tui/` **does NOT exist**. The plan MUST create this directory for `docs/tui/component-catalog.md` + `docs/tui/accessibility-gate.md`.
- `docs/adr/ADR-006-cc-migration-vision-update.md` exists and is the authoritative upstream source for every DISCARD citation (Parts D-1, D-3).
- `tui/src/theme/tokens.ts` **exists** (83 lines, 65 CC-legacy tokens). Ports in scope of this Epic: type surface only. Concrete value rewrites are Epic H territory (see Assumption row 1 and FR-010).

---

## 3 · Deferred-item validation (Constitution §VI gate)

Scan of `spec.md § Scope Boundaries & Deferred Items`:

### 3.1 Permanent out-of-scope (no tracking required)

Five permanent exclusions listed (KOSMOS-original surfaces, dev-domain CC, Gemini CLI parity, CC sourcemap updates, mass file renames). All grounded in ADR-006 Parts D-1/D-3 or Constitution §I. No action required.

### 3.2 Deferred to future work (table walk)

| # | Item | Tracking Issue | Status (2026-04-20) |
|---|---|---|---|
| 1 | `brand-system.md` §3 Logo usage | #1302 | OPEN ✅ |
| 2 | `brand-system.md` §4 Palette values | #1302 | OPEN ✅ |
| 3 | `brand-system.md` §5 Typography scale | #1302 | OPEN ✅ |
| 4 | `brand-system.md` §6 Spacing/grid | #1302 | OPEN ✅ |
| 5 | `brand-system.md` §7 Motion | #1302 | OPEN ✅ |
| 6 | `brand-system.md` §8 Voice & tone | #1302 + #1308 | both OPEN ✅ |
| 7 | `brand-system.md` §9 Iconography | #1302 | OPEN ✅ |
| 8 | `brand-system.md` §10 Component usage | **NEEDS TRACKING** | ⏳ `/speckit-taskstoissues` will backfill |
| 9 | Concrete palette values in `dark.ts`/`default.ts`/`light.ts` | #1302 | OPEN ✅ |
| 10 | Actual mass rename of CC-legacy tokens | **NEEDS TRACKING** | ⏳ `/speckit-taskstoissues` will backfill |
| 11 | Grep CI gate implementation | **NEEDS TRACKING** | ⏳ backfilled as Epic-M-owned Task |
| 12 | Per-component REWRITE implementation | **NEEDS TRACKING** | ⏳ backfilled; one Task per owning Epic |
| 13 | Screen-reader semantic implementation | **NEEDS TRACKING** | ⏳ backfilled per owning Epic |
| 14 | 한국 접근성 지침 2.2 deep-audit | #25 (Public Beta Readiness) | OPEN ✅ |
| 15 | Ministry satellite icon SVGs | #1302 | OPEN ✅ |
| 16 | Light/high-contrast theme palette | **NEEDS TRACKING** | ⏳ Phase 3+ follow-up |

**Count**: 16 deferred items; 10 with concrete GitHub issues; 6 `NEEDS TRACKING` awaiting `/speckit-taskstoissues` backfill (Principle VI-compliant).

### 3.3 Unregistered-deferral scan

Regex scanned spec.md for patterns: `separate epic`, `future epic`, `Phase [2-9]`, `v2`, `deferred to`, `later release`, `out of scope for v1`.

All hits fell into three buckets, none of which are unregistered deferrals:

- **Naming references** — "Initiative #2 (Phase 2 — Multi-Agent Swarm)", "Sub-Issues API v2" (API version). Not deferrals.
- **Flavor text** — "Phase 2 rollout stalls" (User Story 5 motivation). Not a deferral claim.
- **Registered deferrals** — FR-032 "deferred to Epic H #1302" (row 9); L248 "post-Phase-2" tracked to #25 (row 14); L250 "Phase 3+" tracked as row 16.

**Result**: 0 unregistered deferrals. Principle VI gate PASSES.

---

## 4 · Resolved NEEDS CLARIFICATION items

The spec enters plan with **zero `[NEEDS CLARIFICATION: …]`** markers (grep confirmed). Below are the resolutions for ambiguities I surfaced during research that would have blocked `/speckit-plan` or `/speckit-analyze` had they been left implicit:

### R1 · Catalog granularity — per-file or per-family?

- **Decision**: Per-file rows for ~275 individual files + **per-family aggregated rows** for high-density families (> 10 files) that share a single verdict under FR-027. Each aggregated row enumerates constituent files in its evidence column, so the "exactly one verdict per file" rule (SC-001) is preserved.
- **Rationale**: 389 per-file rows would blow Epic M's 90-cap for REWRITE Task sub-issues (FR-025) and produce an unreadable document (SC-008 <30min newcomer test fails). Aggregation is pre-authorized by FR-027.
- **Alternatives considered**: Strict per-file (rejected: breaks 90-cap + readability). Strict per-family (rejected: loses individual-file auditability).

### R2 · Spec says "30 directories" but actual is 31

- **Decision**: Catalog header records the verified **31** with the `a8a678c` sourcemap commit hash as evidence. The spec text can stay at "30" for historical lineage; the catalog is the authoritative artifact per FR-001.
- **Rationale**: Numbers in spec prose rot; numbers in the pinned-hash catalog do not. Making the spec text authoritative would force a spec edit every time a new directory appears upstream, which ADR-004 (pinned sourcemap) explicitly prevents anyway.
- **Alternatives considered**: Edit spec to say "31" (reject: out-of-scope spec churn for a zero-impact semantic difference).

### R3 · Owning-Epic closed-set includes CLOSED Epics B + A

- **Decision**: Catalog owner column MAY cite `B #1297 (closed)` or `A #1298 (closed)` for verdicts whose logical owner was one of those Epics. Any REWRITE Task sub-issue on a closed Epic is re-parented to Epic M as a follow-up Task; PORT verdicts owned by closed Epics that were fully delivered get marked `implementation complete` in the rationale column and do NOT generate Task sub-issues.
- **Rationale**: Preserves FR-003's literal closed-set + AGENTS.md sub-issue hygiene while avoiding the anti-pattern of reopening closed Epics for new Tasks. Also protects SC-004 (every REWRITE has a sub-issue — the sub-issue lives under M in this case).
- **Alternatives considered**: Forbid B/A ownership and re-classify every such row as M-owned (rejected: loses traceability back to the shipped spec work). Reopen B/A (rejected: violates Conventional Commits close-and-lock hygiene).

### R4 · Task-subissue count budget allocation

- **Decision**: Epic M's 90-cap is partitioned as: ≤ 40 REWRITE Tasks (own + follow-ups from closed Epics) + ≤ 30 family-batch Tasks (FR-027) + ≤ 10 DEFER investigation Tasks + ≤ 10 process Tasks (grep-gate impl, brand-system §3–§9 section-owner ping issues). Buffer = 0 — every cell will be audited before `/speckit-taskstoissues` runs.
- **Rationale**: SC-007 hard cap; Principle VI hygiene. REWRITE Tasks owned by non-M Epics (FR-026) do NOT count against M's 90.
- **Alternatives considered**: No partition (rejected: risk of blowing the cap under high-density REWRITE families). Higher cap (rejected: AGENTS.md 100-cap is a GitHub API constraint, not a KOSMOS policy choice).

### R5 · Where does the grep CI gate specification live?

- **Decision**: The **specification** (banned-pattern regex set + error messages + fail-fast rule) lives in `contracts/grep-gate-rules.md` as part of Phase 1 output. The **implementation** (GitHub Actions workflow YAML) is a post-verdict Task under Epic M (one of the 10 process Tasks in R4).
- **Rationale**: FR-011 (spec vs. impl split); spec's Deferred Items row 11 aligns.
- **Alternatives considered**: Embed spec inside workflow YAML (rejected: not reusable across CI backends). Skip the spec (rejected: violates FR-011).

### R6 · `brand-system.md` §10 owner is "All design-concerned Epics" — what tracking issue?

- **Decision**: `/speckit-taskstoissues` backfills a single tracking issue titled "`docs/design/brand-system.md` §10 Component usage guidelines — collaborative section" linked as sub-issue of Epic M. As each downstream Epic contributes, it appends to §10 under a dated H3 subheading; no per-Epic sub-issue on §10 needed.
- **Rationale**: §10 is a living appendix, not a single-owner deliverable. Single tracking Task is sufficient for Principle VI; per-Epic sub-issues would double-count against the 90-cap.
- **Alternatives considered**: One §10 sub-issue per downstream Epic (rejected: 9× duplication wastes cap).

---

## 5 · Best-practices research

### 5.1 PARITY.md-style tracker format (FR-006)

Studied `.references/claw-code/PARITY.md` top-level "9-lane checkpoint" table. Columns adopted for `docs/tui/component-catalog.md`:

| Adopted | Column | Rationale |
|---|---|---|
| ✅ | Status | Maps to Verdict (PORT/REWRITE/DISCARD/DEFER) |
| ✅ | Feature commit | Filled post-implementation by downstream Epic; empty at Epic M merge |
| ✅ | Merge commit | Filled post-implementation by downstream Epic; empty at Epic M merge |
| ✅ | Evidence path(s) | Citation to ADR-006 Part D-1/D-3 or rationale string |
| ➕ | CC source path | PARITY.md implicit; KOSMOS explicit — drives enumeration audit |
| ➕ | KOSMOS target path | PARITY.md implicit; KOSMOS explicit — drives PORT/REWRITE Task acceptance |
| ➕ | Owning Epic | PARITY.md uses "Lane" — KOSMOS uses actual Epic IDs |
| ➕ | Rationale | Free-text; required for DISCARD/DEFER per FR-004/005 |

### 5.2 Token-naming doctrines (FR-009 grammar)

- Tailwind's semantic tokens (`text-primary`) use role-based names but conflict with FR-008's ban on `primary`. Reason for ban: `primary` is content-free in a multi-ministry public-service context where "which ministry is primary" is a live PR comment every time.
- Chakra UI uses `brand.50` / `brand.500` — also banned (digit suffixes forbidden by FR-008).
- **Chosen pattern**: `{metaphorRole}{Variant}?` where `metaphorRole` is one of the fixed vocabulary from ADR-006 A-9. This is KOSMOS-native and matches the orbital-ring metaphor documented there.

### 5.3 WCAG 2.1 AA subset selection (FR-019)

The five criteria in FR-019 (1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2) are the "terminal UI minimum" — criteria that apply to any interactive character-grid UI regardless of whether it's a GUI or TUI. Criteria excluded (e.g., 1.4.4 Resize Text, 1.4.10 Reflow) require pixel-coordinate manipulation that is out of scope for a character-grid app; Ink + terminal rendering satisfies them at the terminal emulator layer.

### 5.4 한국 접근성 지침 2.2 alignment (FR-020)

KWCAG 2.2 (국가표준 KS X 2101) is the Korean baseline referenced by 과기정통부 공공기관 웹접근성 제도. The spec scope is **documentation-level** (catalog rows note which items citizen-facing components MUST satisfy); **implementation-level** deep audit is deferred to #25 Public Beta Readiness (Deferred Items row 14).

---

## 6 · Dependency / integration patterns

This Epic is **documentation-only**. No runtime code is added; no dependency changes; no third-party integrations.

- **Integration with downstream Epics** is a contract boundary: catalog row → Task sub-issue per FR-023. `/speckit-taskstoissues` is the integration mechanism; the tool already exists (Spec Kit skill).
- **Integration with Brand Guardian reviewer role** is a PR-time grep check (FR-011 spec; implementation a follow-up Task).
- **Integration with Accessibility Auditor** is a per-row annotation in `docs/tui/accessibility-gate.md` (FR-018).

No net-new dependencies. Zero `pyproject.toml` or TUI `package.json` edits. This satisfies AGENTS.md hard rule "Never add a dependency outside a spec-driven PR" trivially — this spec adds none.

---

## 7 · Summary of Phase 0 gate state

| Gate | State | Evidence |
|---|---|---|
| Constitution §I — reference mapping | ✅ PASS | Section 1 table maps every design decision |
| Constitution §II — fail-closed security | ✅ N/A | No tool adapters introduced |
| Constitution §III — Pydantic v2 strict typing | ✅ N/A | No new tool I/O schemas |
| Constitution §IV — Government API compliance | ✅ N/A | No adapter work |
| Constitution §V — Policy alignment | ✅ PASS | Catalog preserves PIPA permission-gauntlet invariants via FR-021 IME flag and FR-022 contrast constraints passed to Epic H |
| Constitution §VI — deferred-work accountability | ✅ PASS | 16 items; 10 tracked; 6 backfilled by `/speckit-taskstoissues`; 0 unregistered |
| ADR-006 Part D-3 | ✅ PASS | `src/kosmos/*` surfaces explicitly excluded per FR-033 |
| AGENTS.md Issue hierarchy | ✅ PASS | FR-023 uses `addSubIssue` mutation; FR-025 honors 90-cap |
| AGENTS.md GraphQL-only tracking | ✅ PASS | All issue state verified via `gh api graphql` in §2.3 |

Phase 0 complete. Ready for Phase 1.
