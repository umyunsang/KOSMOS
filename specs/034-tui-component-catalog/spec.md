# Feature Specification: TUI Component Catalog — CC → KOSMOS Verdict Matrix + Brand-System Doctrine

**Feature Branch**: `034-tui-component-catalog`
**Created**: 2026-04-20
**Status**: Draft
**Input**: Epic M #1310 — Initiative #2 (Phase 2 — Multi-Agent Swarm), ADR-006 Part D-3. Canonical verdict matrix + token naming contract + brand-system doctrine to gate every subsequent component port under Initiative #2 (Epics B/C/D/E/H/I/J/K/L/M).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Future-Epic Author Reads a Single Verdict (Priority: P1)

A future Epic author (e.g., the team specifying Epic H #1302 Onboarding, Epic K #1308 Settings, or Epic J #1307 Cost HUD) needs to know, for every component family they plan to touch, whether the CC source should be ported as-is (palette swap only), rebuilt for the KOSMOS citizen domain, discarded entirely, or deferred to a later phase. Today this information does not exist in one place — it is scattered across ADR-006 Part D, individual Epic bodies, and implicit codebase conventions. The Epic author currently re-discovers these verdicts by grep + guesswork, and two Epics touching the same family can reach different verdicts.

**Why this priority**: Without a single verdict, Initiative #2 cannot achieve design consistency. Every subsequent Epic spec-cycle restarts the verdict debate. The catalog is a pure prerequisite for 7 other Epics (B/C/D/E/I/J/K/L).

**Independent Test**: A reviewer opens `docs/tui/component-catalog.md`, picks any of the 389 CC component files at random, and finds exactly one verdict (PORT / REWRITE / DISCARD / DEFER), one owning Epic (if REWRITE), and one evidence citation (CC source path, plus ADR-006 Part D-1/D-3 for DISCARD). No file yields zero or multiple verdicts.

**Acceptance Scenarios**:

1. **Given** a reviewer has the committed `docs/tui/component-catalog.md`, **When** they search for any CC component file path, **Then** they find exactly one row with verdict, owning Epic, CC source path, KOSMOS target path (if PORT/REWRITE), and evidence citation.
2. **Given** a future-Epic spec author is writing their own spec input, **When** they consult the catalog for their domain family (e.g., Settings for Epic K), **Then** they can enumerate every PORT/REWRITE/DISCARD verdict within that family without re-reading CC source.
3. **Given** two Epics (e.g., H and K) both touch the Pickers family, **When** reviewers compare their spec inputs, **Then** both cite the same catalog row and reach the same verdict.

---

### User Story 2 — Brand Guardian Enforces Token-Naming Doctrine (Priority: P1)

A Brand Guardian reviewing a downstream PR (e.g., Epic H #1302 proposing `theme/dark.ts` palette values) needs a machine-checkable doctrine to reject ad-hoc token names like `primary`, `accent1`, `mainColor`, or legacy `claudeShimmer` leakage. Today, there is no written contract. Ad-hoc names sneak into PRs because reviewers have no rule to cite.

**Why this priority**: Without a naming contract authored BEFORE downstream Epics start, each Epic invents its own naming. Retrofitting consistent names later is expensive. Epic M is the right place because it is already auditing the whole component tree and knows every token that exists on both sides.

**Independent Test**: Brand Guardian runs a grep on the proposed KOSMOS tree for the banned patterns and finds zero matches in production source. Every token name matches the documented pattern in `docs/design/brand-system.md` §2.

**Acceptance Scenarios**:

1. **Given** the doctrine in `docs/design/brand-system.md` §2 is committed, **When** a downstream PR introduces a token named `primary`, **Then** the grep CI gate rejects the PR with a pointer to §2.
2. **Given** a token name like `orbitalRing`, **When** Brand Guardian audits its semantic fit, **Then** the doctrine provides a mapping (orbital-ring = tool-loop metaphor).
3. **Given** a legacy CC token `claudeShimmer` survives into a PR, **When** the grep gate runs, **Then** the PR fails with a specific error message naming the banned token.

---

### User Story 3 — Cross-Epic Design Consistency via Single Source of Truth (Priority: P1)

Every design-concerned Epic (H / J / K / L / E) makes design decisions: palette values, typography, spacing, motion, voice & tone, iconography, component usage. Without a shared canonical document, each Epic makes these decisions independently and ships mutually inconsistent UI. Today, designers across Epics would re-derive palette or typography from scratch in each spec.

**Why this priority**: A shared brand-system doc turns the multi-Epic rollout from "independent design decisions" into "collaborative extension of a shared contract." This is also the only way Agent Teams (multiple parallel Sonnet teammates) produce a consistent deliverable.

**Independent Test**: A reviewer opens any Epic H/J/K/L/E spec input and finds an explicit "References `docs/design/brand-system.md` as source of truth" statement, AND finds that the Epic's design decisions cite the specific §X section they extend.

**Acceptance Scenarios**:

1. **Given** `docs/design/brand-system.md` with §1 and §2 committed, **When** Epic H #1302 spec input is written, **Then** it references the doc AND declares intent to fill §3–§9.
2. **Given** Epic K spec input, **When** it introduces a theme picker, **Then** it references §4 (Palette values) as authority.
3. **Given** all design-concerned Epics enter Spec Kit cycle, **When** the Kit cross-reference check runs, **Then** 100% of their inputs cite the doc.

---

### User Story 4 — Accessibility Auditor Gates Each Verdict (Priority: P2)

An Accessibility Auditor reviewing any PORT or REWRITE verdict needs to know which accessibility requirements (WCAG 2.1 AA, 한국 접근성 지침 2.2, Hangul composition safety, screen-reader semantics, color contrast) apply to that verdict. Today, accessibility decisions are Epic-specific and inconsistent.

**Why this priority**: Citizen-facing TUI accessibility is a KOSMOS mission commitment (ADR-006 A-10 IME safety rule; vision.md). Without per-verdict accessibility gates in the catalog itself, later Epics will forget to apply them.

**Independent Test**: A reviewer opens `docs/tui/accessibility-gate.md` and, for every PORT/REWRITE verdict in the catalog, finds a matching row with the required WCAG criteria and any Korean-specific gate.

**Acceptance Scenarios**:

1. **Given** the catalog assigns REWRITE to the PromptInput family, **When** the accessibility gate is consulted, **Then** it mandates IME composition-safety (Epic E #1300 contract) + WCAG 2.1 AA keyboard operability.
2. **Given** the catalog assigns PORT to the design-system family, **When** the gate is consulted, **Then** it requires color contrast >= 4.5:1 for body text (enforced during Epic H palette value assignment).
3. **Given** DISCARD verdicts, **When** the gate is consulted, **Then** no accessibility row is required (DISCARD means not in KOSMOS tree).

---

### User Story 5 — Task Sub-Issue Traceability (Priority: P2)

When Epic M completes, every REWRITE verdict must be traceable to a Task sub-issue in the owning Epic. Without this, REWRITE verdicts become orphan work items that no Epic owns, and Phase 2 rollout stalls.

**Why this priority**: Operational hygiene — Initiative #2's Sub-Issues API v2 graph must stay complete. Orphan REWRITEs violate AGENTS.md hierarchy rules.

**Independent Test**: A GraphQL query enumerates all REWRITE rows and verifies each has a corresponding Task sub-issue under its owning Epic (B/C/D/E/H/I/J/K/L/M).

**Acceptance Scenarios**:

1. **Given** the catalog lists a REWRITE for the Settings family owned by Epic K, **When** GraphQL queries Epic K's `subIssues` connection, **Then** a Task sub-issue referencing that REWRITE exists.
2. **Given** Epic M's own Task sub-issues, **When** counted, **Then** total <= 90 (Sub-Issue 100-cap rule).
3. **Given** a DISCARD verdict, **When** audited, **Then** no Task sub-issue is required.

---

### User Story 6 — DISCARD Evidence Integrity (Priority: P3)

Every DISCARD verdict must cite either ADR-006 Part D-1 (intentional exclusion), Part D-3 (KOSMOS-original surface), or a specific domain-mismatch rationale. Unjustified DISCARDs silently lose features; justified DISCARDs provide permanent design-decision traceability.

**Why this priority**: Auditability. Future reviewers must be able to ask "why did we skip X?" and receive a citation, not a guess.

**Independent Test**: Open the catalog, grep DISCARD rows, confirm every row has a non-empty evidence citation field.

**Acceptance Scenarios**:

1. **Given** CC `src/components/AutoUpdater.tsx` is marked DISCARD, **When** evidence is read, **Then** it cites "ADR-006 Part D-1 — CC-specific auto-updater; KOSMOS uses uv/pip."
2. **Given** a component in the Hooks family marked DISCARD, **When** evidence is read, **Then** it cites domain mismatch or ADR-006.
3. **Given** any DISCARD row with empty evidence, **When** validation runs, **Then** the catalog fails validation.

---

### Edge Cases

- **CC source file added between Epic M start and end**: The catalog snapshot pins the `.references/claude-code-sourcemap/` commit hash used for enumeration. New additions after that commit become a separate Task (re-audit) under Epic M or a follow-up Epic.
- **Ambiguous family membership**: A file that could belong to two families (e.g., a Spinner used inside a Permission dialog) is classified under its physical directory location; cross-family references go in the evidence column.
- **Existing KOSMOS file without a CC counterpart**: This is a KOSMOS-original extension (Part D-3 territory). Not in scope for verdict; documented as an explicit "no migration needed" row.
- **Verdict collision between two Epics**: If Epic H and Epic M both claim ownership of a family (e.g., Onboarding), the catalog lists both, with the PRIMARY owner being the Epic whose spec explicitly scopes it.
- **Component depended on by a DISCARD but reused elsewhere**: Mark the re-used component PORT even if its original CC caller is DISCARD.
- **Gemini CLI references a component that CC does NOT have**: Out of scope (Gemini CLI is a triangulation source, not a parity target).
- **Brand Guardian disagrees with a proposed token name**: Escalation is a spec-level comment on Epic M; resolution lands in `docs/design/brand-system.md` §2 as an explicit example.
- **Task sub-issue total approaches 90-cap**: Merge related REWRITEs into combined Tasks when a family has > 10 REWRITEs (batch per-family instead of per-file for high-density families).
- **Accessibility gate contradicts Epic H palette choice**: Epic M's gate wins (contrast >= 4.5:1 is a hard constraint); Epic H must propose palette values that satisfy it.
- **A PORT verdict component contains CC-specific logic (e.g., Claude Code API calls)**: Re-classify as REWRITE — PORT is palette-only swap, no logic changes.

## Requirements *(mandatory)*

### Functional Requirements

#### Verdict Matrix

- **FR-001**: The catalog MUST cover 100% of CC component files at `.references/claude-code-sourcemap/restored-src/src/components/` (enumerated at a pinned commit hash, recorded in the catalog header).
- **FR-002**: Each row MUST contain: CC source path, file count (1 for individual files; N for aggregated family entries where noted), verdict (PORT / REWRITE / DISCARD / DEFER), owning Epic (for PORT/REWRITE/DEFER), KOSMOS target path (for PORT/REWRITE), rationale.
- **FR-003**: Owning Epic values MUST be drawn from the closed set {B #1297, C #1301, D #1299, E #1300, H #1302, I #1303, J #1307, K #1308, L #1309, M #1310}.
- **FR-004**: Each DISCARD row MUST cite ADR-006 Part D-1 (intentional exclusion) OR Part D-3 (KOSMOS-original) OR a specific domain-mismatch rationale.
- **FR-005**: Each DEFER row MUST cite the target phase/Epic and the unblock condition.
- **FR-006**: The catalog MUST follow the `.references/claw-code/PARITY.md` tracker pattern with columns including Status, Feature commit (post-implementation), Merge commit (post-implementation), and Evidence path(s).
- **FR-007**: The catalog MUST record the file count discrepancy between Epic body #1310 (claims 286) and the 2026-04-20 recount (389) in the catalog header, with the recount's commit hash as evidence.

#### Token Naming Contract (Type Surface Only)

- **FR-008**: `tui/src/theme/tokens.ts` type surface MUST NOT contain any identifier matching the banned patterns (claude*, clawd*, anthropic*, primary, secondary, tertiary, accent + digits, mainColor, standalone background/foreground). Contextual use like `orbitalRingBackground` is allowed.
- **FR-009**: All new token names MUST follow the pattern {metaphorRole}{Variant}? where metaphorRole is drawn from {kosmosCore, orbitalRing, wordmark, subtitle, agentSatellite + MINISTRY, ...} and Variant is an optional modifier suffix (Shimmer, Muted, Hover, Active, etc.).
- **FR-010**: This Epic MUST define the token NAME surface only. Concrete color VALUES in `dark.ts`, `default.ts`, `light.ts` are explicitly out of scope (Epic H #1302 owns palette).
- **FR-011**: A grep-based CI gate specification MUST be authored under this Epic to enforce FR-008 at PR time (the gate's implementation may be a post-verdict Task within this Epic).

#### Brand-System Doctrine

- **FR-012**: `docs/design/brand-system.md` MUST be created with 10 top-level headings (§1 Brand metaphor, §2 Token naming doctrine, §3 Logo usage, §4 Palette values, §5 Typography scale, §6 Spacing/grid, §7 Motion, §8 Voice & tone, §9 Iconography, §10 Component usage guidelines).
- **FR-013**: §1 and §2 MUST be fully authored by this Epic.
- **FR-014**: §3–§10 MUST be reserved as placeholder headings with an "Owner: Epic H #1302" (or downstream Epic for §10) pointer and a prohibition on non-owner edits until the owning Epic enters Spec Kit cycle.
- **FR-015**: §1 MUST articulate the KOSMOS (은하계) metaphor — scattered DX infrastructure unified into AX harness — and map visual elements to semantic roles (kosmosCore, orbitalRing, agentSatellite + MINISTRY).
- **FR-016**: §2 MUST enumerate the token naming doctrine (FR-008, FR-009), rejected patterns, and the Brand Guardian review contract.
- **FR-017**: `docs/design/brand-system.md` MUST be referenced as source-of-truth by every subsequent design-concerned Epic (H/J/K/L/E) spec input — this requirement takes effect once their specs enter Spec Kit cycle.

#### Accessibility Gate

- **FR-018**: `docs/tui/accessibility-gate.md` MUST exist and enumerate per-verdict accessibility requirements.
- **FR-019**: Every PORT and REWRITE verdict MUST be annotated with the applicable WCAG 2.1 AA success criteria from the closed set {1.4.3 Contrast, 2.1.1 Keyboard, 2.4.7 Focus Visible, 3.3.2 Labels or Instructions, 4.1.2 Name Role Value}.
- **FR-020**: Citizen-facing components (Onboarding, PromptInput, Messages, Settings, Pickers, Help) MUST be additionally annotated with 한국 접근성 지침 2.2 conformance notes.
- **FR-021**: Every PORT/REWRITE component that accepts text input MUST be flagged for IME composition-gate compliance (Epic E #1300 contract).
- **FR-022**: Color-contrast constraints (>= 4.5:1 body text, >= 3:1 large text / non-text) MUST be documented as a palette-selection constraint passed to Epic H #1302.

#### Task Sub-Issue Generation

- **FR-023**: For each REWRITE verdict, a Task sub-issue MUST be created under the owning Epic via the Sub-Issues API v2 `addSubIssue` mutation.
- **FR-024**: Each Task sub-issue MUST contain: the CC source path, the KOSMOS target path, a pointer back to the catalog row, and an acceptance checklist derived from the accessibility gate.
- **FR-025**: Total Task sub-issues created under Epic M MUST be <= 90 (per Sub-Issue 100-cap rule; [Deferred]-prefixed follow-up items do NOT count against this cap).
- **FR-026**: REWRITE verdicts whose owning Epic is NOT M (e.g., those that land under Epic K's ownership) MUST create Task sub-issues under the OWNING Epic, not Epic M, and those do NOT count against Epic M's 90-cap.
- **FR-027**: High-density families (> 10 REWRITE rows in a single family) MAY be batched into a single "family rewrite" Task to stay under the cap; the Task MUST enumerate the constituent files in its body.

#### Cross-Epic Contract Propagation

- **FR-028**: This Epic's deliverables MUST declare in the catalog header that every subsequent Epic (B/C/D/E/H/I/J/K/L) spec input cites `docs/design/brand-system.md` as source-of-truth.
- **FR-029**: The catalog MUST include a "Downstream Epic spec input checklist" appendix that future Epic authors copy-paste into their own spec inputs to satisfy FR-017.

#### Governance and Exclusions

- **FR-030**: This Epic MUST NOT modify any `tui/src/` source file other than `tui/src/theme/tokens.ts` type surface.
- **FR-031**: This Epic MUST NOT modify any `src/kosmos/` source file.
- **FR-032**: Concrete color values in `dark.ts`, `default.ts`, `light.ts` are explicitly deferred to Epic H #1302.
- **FR-033**: KOSMOS-original surfaces under `src/kosmos/safety/`, `src/kosmos/security/`, `src/kosmos/primitives/`, `src/kosmos/tools/*` are out of scope per ADR-006 Part D-3 — they MUST NOT appear in the verdict matrix.
- **FR-034**: Sections §3–§10 of `docs/design/brand-system.md` MUST NOT be filled by this Epic; attempting to fill them is a scope violation subject to /speckit-analyze rejection.

### Key Entities

- **Verdict**: One of PORT (palette-only swap; preserves logic), REWRITE (KOSMOS mission-specific rebuild; logic changes allowed), DISCARD (excluded from KOSMOS tree; evidence required), DEFER (Phase 3+ with unblock condition).
- **ComponentFamily**: A top-level directory under `.references/claude-code-sourcemap/restored-src/src/components/` (30 directories) OR the root-level files (~111 files) grouped by semantic role (per Epic M body §31 families table).
- **CCComponent**: An individual file (.tsx or .ts) within a ComponentFamily. ~389 total files at the pinned commit hash.
- **OwningEpic**: An element of the closed set {B #1297, C #1301, D #1299, E #1300, H #1302, I #1303, J #1307, K #1308, L #1309, M #1310}. Assigned for every PORT / REWRITE / DEFER verdict.
- **TokenName**: A string identifier in `tui/src/theme/tokens.ts` matching the pattern {metaphorRole}{Variant}?. Each token carries semantic weight tied to the KOSMOS integration metaphor.
- **BrandSystemSection**: One of ten numbered sections in `docs/design/brand-system.md`. §1 and §2 are owned by this Epic (fully authored). §3–§9 are owned by Epic H #1302. §10 is owned by downstream component-level Epics.
- **AccessibilityGate**: A per-verdict set of WCAG 2.1 AA criteria + 한국 접근성 지침 2.2 notes + IME-safety flag + color-contrast constraint, keyed by (CCComponent, Verdict).
- **TaskSubIssue**: A GitHub issue linked as a sub-issue under an OwningEpic via the Sub-Issues API v2 `addSubIssue` mutation. One per REWRITE verdict (or per family batch under FR-027).
- **EvidenceCitation**: A reference to ADR-006 Part D-1, Part D-3, a spec number, or a free-text domain-mismatch rationale. Required for every DISCARD and DEFER row.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of CC component files at the pinned `.references/claude-code-sourcemap/` commit hash have exactly one verdict row in `docs/tui/component-catalog.md` (total = 389 ± the commit-hash snapshot).
- **SC-002**: 0 tokens in `tui/src/theme/tokens.ts` type surface match the banned patterns in FR-008 (verified by grep CI gate).
- **SC-003**: `docs/design/brand-system.md` contains 10 section headings; §1 and §2 each >= 500 words of substantive content; §3–§10 each contain the "Owner: Epic X" pointer and <= 50 words of placeholder.
- **SC-004**: 100% of REWRITE verdicts have a corresponding Task sub-issue under the owning Epic, verified by a GraphQL query comparing catalog REWRITE count to the sum of `subIssues.totalCount` across owning Epics for rows whose title references the catalog.
- **SC-005**: 100% of DISCARD verdicts cite ADR-006 Part D-1, Part D-3, or a non-empty domain-mismatch rationale.
- **SC-006**: 100% of DEFER verdicts cite a target Epic/Phase and an unblock condition.
- **SC-007**: Epic M Task sub-issue count <= 90 (excluding [Deferred]-prefixed follow-ups).
- **SC-008**: A readability audit by a reviewer unfamiliar with CC concludes that the catalog enables a Phase-2 newcomer to spec their Epic's component-level tasks in under 30 minutes using only the catalog + ADR-006 + the referenced CC sourcemap.
- **SC-009**: Every PORT and REWRITE row has an associated accessibility-gate row in `docs/tui/accessibility-gate.md`; 0 orphan verdicts.
- **SC-010**: The downstream Epic spec-input checklist (FR-029) is copy-pasteable and contains <= 5 bullet points.
- **SC-011**: The grep CI gate specification (FR-011) is unambiguous enough that a Sonnet teammate can implement it in a single Task without clarification.
- **SC-012**: Brand Guardian can reject a simulated ad-hoc token proposal (primary, accent1, claudeShimmer) by citing a single §2 subsection.

## Assumptions

- ADR-006 Part B "parallel with H #1302" wording is authoritative over Epic M body "선행: Epic H #1302" — verdict matrix authoring does not depend on H's palette values.
- The 2026-04-20 file-count recount (389 .tsx/.ts files across 30 top-level directories) is accurate as of commit `693d4b6` and is superseded only by a newer pinned commit hash in the catalog header.
- `.references/gemini-cli/` and `.references/claw-code/` remain under `.references/` for the duration of this Epic's execution (not deleted or restructured).
- Brand Guardian is a KOSMOS reviewer role with authority to reject PRs that violate §2 token naming doctrine — implemented via the Agent Teams configuration at `/speckit-implement` time and via the grep CI gate at PR time.
- The Sub-Issues API v2 `addSubIssue` mutation is the canonical linking mechanism per AGENTS.md § Issue hierarchy; `trackedIssues` body-mention fallback is NOT acceptable.
- CC sourcemap at `.references/claude-code-sourcemap/restored-src/` is frozen at an immutable commit (ADR-004 policy) — the pinned hash in the catalog header remains valid indefinitely.
- Agent Teams (Explore, UI Designer, Frontend Developer, Brand Guardian, Accessibility Auditor, Code Reviewer) are available per AGENTS.md and can be spawned at `/speckit-implement` for parallel family audits.
- The 90-cap for Epic M Task sub-issues is sufficient given that DISCARD + DEFER verdicts do NOT generate Tasks and high-density families may be batched per FR-027.
- Downstream Epics that own REWRITE verdicts (B/C/D/E/H/I/J/K/L) will accept Task sub-issues created by Epic M's `/speckit-taskstoissues` run, even though those Tasks are authored outside the receiving Epic's own spec cycle.
- `docs/design/brand-system.md` does NOT require a dedicated ADR — it is a reference document, not an architecture or stack decision under AGENTS.md's "ADR required" clause.
- Korean accessibility standard 한국 접근성 지침 2.2 (KWCAG 2.2) is the applicable compliance baseline for citizen-facing surfaces; WCAG 2.1 AA is the international baseline.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **KOSMOS-original surfaces** under `src/kosmos/safety/`, `src/kosmos/security/`, `src/kosmos/primitives/`, `src/kosmos/tools/*` — no CC analog exists; migration is not applicable per ADR-006 Part D-3.
- **Developer-domain CC surfaces** intentionally excluded from the citizen domain per ADR-006 Part D-1: dev-only slash commands (/commit, /pr_comments, /review, /issue, /install-github-app, /doctor, /heapdump, /vim, /model, /config), Anthropic-platform surfaces (claudeAiLimits, oauth, autoDream, PromptSuggestion, MagicDocs, upstreamproxy, bridge, buddy), migration helpers (src/migrations/), domain-mismatch modules (src/voice/, src/vim/, src/plugins/).
- **Gemini CLI parity** — Gemini CLI is referenced for triangulation only, not as a parity target.
- **CC sourcemap updates** — ADR-004 freezes the sourcemap at an immutable commit; re-audit of new CC releases is a separate future-Epic concern.
- **Mass file renames across KOSMOS tree** — this Epic fixes the NAME CONTRACT only, not the physical rename. Downstream Epics perform renames under their own Tasks.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| `docs/design/brand-system.md` §3 (Logo usage) | Epic H owns logo rendering and usage rules | Epic H #1302 | #1302 |
| `docs/design/brand-system.md` §4 (Palette values) | Concrete color values require Epic H brand port | Epic H #1302 | #1302 |
| `docs/design/brand-system.md` §5 (Typography scale) | Typography tied to Epic H splash + onboarding | Epic H #1302 | #1302 |
| `docs/design/brand-system.md` §6 (Spacing/grid) | Grid rules emerge from Epic H layout decisions | Epic H #1302 | #1302 |
| `docs/design/brand-system.md` §7 (Motion) | Motion library specific to Epic H animations | Epic H #1302 | #1302 |
| `docs/design/brand-system.md` §8 (Voice & tone) | Citizen-facing copy lives in Epic H onboarding + Epic K Settings | Epic H #1302 + Epic K #1308 | #1302, #1308 |
| `docs/design/brand-system.md` §9 (Iconography) | Ministry satellite icon shapes designed alongside Epic H splash | Epic H #1302 | #1302 |
| `docs/design/brand-system.md` §10 (Component usage guidelines) | Per-component usage emerges from downstream Task implementations | All design-concerned Epics (B/C/D/E/H/I/J/K/L) | #1479 |
| Concrete palette values in `dark.ts` / `default.ts` / `light.ts` | Values are Epic H's brand-port deliverable | Epic H #1302 | #1302 |
| Actual mass rename of CC-legacy tokens in KOSMOS tree | Physical rename follows the NAME CONTRACT; implemented per Epic as each touches its files | All design-concerned Epics | #1480 |
| Grep CI gate IMPLEMENTATION (workflow YAML) | Specification (rules, banned patterns, error messages) lives here; implementation is a Task within Epic M | Epic M #1310 (post-verdict Task) | #1481 |
| Per-component REWRITE implementation | Each REWRITE verdict spawns a Task in its owning Epic | B / C / D / E / H / I / J / K / L / M | #1482 |
| Screen-reader semantic implementation | Per-component ARIA/role decisions land in owning-Epic Tasks | All design-concerned Epics | #1483 |
| 한국 접근성 지침 2.2 deep-compliance audit | Baseline is documented here; full audit is post-Phase-2 | Phase 3 Public Beta Readiness (#25) | #25 |
| Ministry satellite icon set (SVG creation beyond existing assets) | New icons beyond `assets/kosmos-*.svg` | Epic H #1302 | #1302 |
| Light/high-contrast theme palette | Phase 1 runs dark theme only per ADR-006 A-9 item 4 | Phase 3+ | #1484 |
