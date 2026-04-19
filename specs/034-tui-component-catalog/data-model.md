# Data Model: TUI Component Catalog + Brand-System Doctrine

**Feature**: 034-tui-component-catalog
**Phase**: 1 (Design & Contracts)
**Date**: 2026-04-20

> **Nature of this model**: This Epic produces **Markdown documents**, not Pydantic models or database tables. The "entities" below describe the **logical shape** of rows in `docs/tui/component-catalog.md`, sections in `docs/design/brand-system.md`, and entries in `docs/tui/accessibility-gate.md`. The **machine-checkable contract** for these shapes lives in `contracts/` — see `catalog-row-schema.md`, `token-naming-grammar.md`, `brand-system-sections.md`, `accessibility-gate-rows.md`, `grep-gate-rules.md`.

---

## 1 · Entity catalog

### 1.1 `Verdict` (enum)

- **Values**: `PORT` | `REWRITE` | `DISCARD` | `DEFER`
- **Semantics**:
  - `PORT` — lift CC file verbatim; only palette / token rewrite allowed. Logic identical. If CC-specific logic is discovered mid-port, promote to `REWRITE`.
  - `REWRITE` — KOSMOS mission-specific rebuild. Logic changes allowed. MUST have an owning Epic (non-M) or an M-owned follow-up Task when the logical owner is a closed Epic.
  - `DISCARD` — not in KOSMOS tree. MUST cite ADR-006 Part D-1 (intentional exclusion) OR D-3 (KOSMOS-original) OR a specific domain-mismatch rationale.
  - `DEFER` — Phase 3+ or unblocked-by-specific-condition. MUST cite target Epic/Phase and unblock condition.
- **Source FR**: 180 (Key Entities), 002, 004, 005.

### 1.2 `ComponentFamily`

- **Fields**:
  - `family_name: str` — one of 31 top-level subdirectories under `.references/claude-code-sourcemap/restored-src/src/components/` OR one of the semantic-role bins for root-level files (e.g., `root.logo-wordmark`, `root.dialogs`).
  - `cc_path: str` — absolute path under `restored-src/src/components/`.
  - `aggregated: bool` — `true` if this row represents a family-batched aggregation per FR-027 (> 10 REWRITE rows collapsed into one Task); `false` if the family enumerates per-file.
- **Key rule**: a file belongs to its **physical directory** family (FR Edge Cases: ambiguous family membership).
- **Source FR**: 181, 027.

### 1.3 `CCComponent`

- **Fields**:
  - `relative_path: str` — from `restored-src/src/components/` root (e.g., `permissions/PermissionDialog.tsx`).
  - `family_name: str` — FK to `ComponentFamily`.
  - `file_kind: Literal["tsx", "ts"]` — extension.
- **Invariant I1**: every `.tsx`/`.ts` file under `src/components/` at the pinned sourcemap commit MUST appear exactly once in the catalog (FR-001, SC-001).
- **Source FR**: 182.

### 1.4 `OwningEpic`

- **Fields**:
  - `id: str` — one of `{"B", "C", "D", "E", "H", "I", "J", "K", "L", "M"}`.
  - `issue_number: int` — one of `{1297, 1298, 1299, 1300, 1301, 1302, 1303, 1307, 1308, 1309, 1310}` (AGENTS.md confirmed; NB: 1298 is not in the Key Entities closed-set list — see research §2.3 for the closed-Epic edge case).
  - `state: Literal["OPEN", "CLOSED"]` — verified via `gh api graphql`.
  - `closure_delegate: Optional[int]` — if `state == CLOSED`, Task sub-issues for this Epic's REWRITE verdicts are created under Epic M (`closure_delegate = 1310`).
- **Invariant I2**: a REWRITE verdict whose owning Epic is CLOSED triggers `closure_delegate = 1310` per research §R3.
- **Source FR**: 183, 003, 023, 026.

### 1.5 `CatalogRow`

One row in `docs/tui/component-catalog.md`.

- **Fields**:
  - `cc_source_path: str` — FK to `CCComponent.relative_path` OR `ComponentFamily.family_name` for aggregated rows.
  - `file_count: int` — 1 for per-file rows; N for aggregated rows.
  - `verdict: Verdict`
  - `owning_epic: Optional[OwningEpic]` — required for PORT/REWRITE/DEFER; forbidden for DISCARD.
  - `kosmos_target_path: Optional[str]` — absolute under `tui/src/`; required for PORT/REWRITE; forbidden for DISCARD/DEFER.
  - `rationale: str` — free-text; required for DISCARD/DEFER (cites ADR-006 Part D-1/D-3 or unblock condition).
  - `evidence: str` — citation column per FR-006 (ADR-006 Part D reference, spec number, etc.).
  - `feature_commit: Optional[str]` — filled post-implementation by downstream Epic; empty at Epic M merge.
  - `merge_commit: Optional[str]` — filled post-implementation; empty at Epic M merge.
  - `task_sub_issue: Optional[int]` — GitHub issue number of the Task sub-issue generated per FR-023; filled by `/speckit-taskstoissues`.
  - `accessibility_gate_ref: Optional[str]` — anchor into `docs/tui/accessibility-gate.md`; required for PORT/REWRITE.
- **Invariant I3** (SC-001): `len({row.cc_source_path for row in catalog if not row.aggregated}) + sum(row.file_count for row in catalog if row.aggregated) == 389`.
- **Invariant I4** (FR-004): every DISCARD row has non-empty `rationale` AND `rationale` starts with one of `{"ADR-006 Part D-1", "ADR-006 Part D-3", "Domain mismatch:"}`.
- **Invariant I5** (FR-005): every DEFER row has non-empty `rationale` AND `rationale` includes target Epic/Phase AND includes unblock condition (string match on "unblock when").
- **Invariant I6** (FR-019): every PORT/REWRITE row has `accessibility_gate_ref != None`.
- **Source FR**: 002, 003, 004, 005, 006.

### 1.6 `TokenName`

- **Fields**:
  - `name: str` — identifier in `tui/src/theme/tokens.ts` type surface.
  - `metaphor_role: MetaphorRole` — the semantic prefix (see §1.7).
  - `variant: Optional[str]` — modifier suffix (Shimmer, Muted, Hover, Active, Background).
- **Invariant I7** (FR-008): `name` MUST NOT match any banned pattern:
  - regex `^claude.*`, `^clawd.*`, `^anthropic.*`
  - regex `^primary$|^secondary$|^tertiary$`
  - regex `^accent[0-9]+$`
  - regex `^mainColor$`
  - regex `^background$|^foreground$` (standalone — contextual suffix like `orbitalRingBackground` is allowed)
- **Invariant I8** (FR-009): `name == f"{metaphor_role.value}{variant or ''}"` with variant title-cased.
- **Source FR**: 184, 008, 009.

### 1.7 `MetaphorRole` (enum)

- **Values** (closed set; extensions require an ADR):
  - `kosmosCore`
  - `orbitalRing`
  - `wordmark`
  - `subtitle`
  - `agentSatellite{MINISTRY}` where `{MINISTRY}` is one of `{Koroad, Kma, Hira, Nmc, Nfa119, Geocoding, ...}` (open-ended ministry set).
  - `permissionGauntlet`
  - `planMode`
  - `autoAccept`
  - `success` / `error` / `warning` / `info` — retained from CC semantic base (NOT banned; these are WCAG-aligned semantic slots, not visual roles).
- **Source**: ADR-006 A-9 brand splash vocabulary.

### 1.8 `BrandSystemSection`

One section in `docs/design/brand-system.md`.

- **Fields**:
  - `number: int` — 1..10.
  - `heading: str` — canonical heading text.
  - `owner_epic: OwningEpic`
  - `status: Literal["authored", "placeholder"]`
  - `word_count: int`
- **Invariant I9** (FR-012, SC-003):
  - section `1` and `2` → `status == "authored"` AND `word_count >= 500`
  - section `3..10` → `status == "placeholder"` AND `word_count <= 50` AND body MUST contain the literal string `Owner: Epic {owner_epic.id} #{owner_epic.issue_number}`
- **Invariant I10** (FR-014): sections 3..10 MUST NOT be edited by this Epic's PR; `/speckit-analyze` asserts no content lines beyond the owner pointer.
- **Source FR**: 185, 012, 013, 014, 015, 016, 017, 034.

### 1.9 `AccessibilityGateRow`

One row in `docs/tui/accessibility-gate.md`.

- **Fields**:
  - `cc_component: str` — FK to `CatalogRow.cc_source_path`.
  - `verdict: Literal["PORT", "REWRITE"]` — DISCARD/DEFER rows do NOT appear here.
  - `wcag_criteria: set[str]` — subset of `{"1.4.3", "2.1.1", "2.4.7", "3.3.2", "4.1.2"}`.
  - `kwcag_notes: Optional[str]` — 한국 접근성 지침 2.2 notes; required for citizen-facing families.
  - `ime_composition_safe: bool` — true if component accepts text input (FR-021).
  - `contrast_constraint: Literal["4.5:1", "3:1", "n/a"]`
- **Invariant I11** (FR-019): `wcag_criteria != set()` for every row.
- **Invariant I12** (FR-020): rows whose `cc_component` family is in `{Onboarding, PromptInput, messages, Settings, PickerLike, HelpV2}` MUST have `kwcag_notes != None`.
- **Invariant I13** (FR-021): rows whose CC component accepts text input MUST have `ime_composition_safe == True`.
- **Source FR**: 186, 018, 019, 020, 021, 022.

### 1.10 `TaskSubIssue`

- **Fields**:
  - `issue_number: int`
  - `parent_epic: OwningEpic`
  - `cc_source_path: str` — FK to CatalogRow
  - `kosmos_target_path: str`
  - `catalog_row_anchor: str` — markdown anchor like `#permissions-permissiondialog-tsx`
  - `acceptance_checklist: list[str]` — derived from `AccessibilityGateRow` for the same `cc_source_path`
- **Invariant I14** (FR-023, SC-004): every REWRITE row has exactly one `TaskSubIssue` linked via `addSubIssue` mutation.
- **Invariant I15** (FR-025, SC-007): `len([t for t in all_tasks if t.parent_epic.id == "M" and not t.title.startswith("[Deferred]")]) <= 90`.
- **Invariant I16** (FR-026): for each non-M REWRITE, `TaskSubIssue.parent_epic == CatalogRow.owning_epic` (re-parents to Epic M only when owning Epic is CLOSED per research §R3).
- **Source FR**: 187, 023, 024, 025, 026, 027.

### 1.11 `EvidenceCitation`

- **Fields**:
  - `kind: Literal["ADR_D1", "ADR_D3", "SPEC", "DOMAIN_MISMATCH"]`
  - `reference: str` — spec number (`"spec 031"`) or ADR section (`"ADR-006 Part D-1 § 'Dev-only slash commands'"`) or free-text.
- **Invariant I17** (FR-004, SC-005): every DISCARD row's evidence MUST resolve to an `EvidenceCitation` with valid `kind`.
- **Source FR**: 188, 004.

---

## 2 · Relationships

```
Initiative #2
  └─ Epic M #1310
        ├─ produces docs/tui/component-catalog.md  (N × CatalogRow)
        │   ├─ each CatalogRow ↔ 0..1 TaskSubIssue   (REWRITE only; FR-023)
        │   └─ each CatalogRow ↔ 0..1 AccessibilityGateRow (PORT/REWRITE only; FR-018)
        │
        ├─ produces docs/tui/accessibility-gate.md  (N × AccessibilityGateRow)
        │
        ├─ produces docs/design/brand-system.md     (10 × BrandSystemSection)
        │   ├─ §1, §2 authored ≥ 500 words each    (FR-013)
        │   └─ §3..§10 placeholder ≤ 50 words      (FR-014)
        │
        └─ modifies tui/src/theme/tokens.ts type surface
              └─ each TokenName conforms to MetaphorRole grammar (FR-009)
```

## 3 · State transitions

**`CatalogRow.verdict`** is effectively immutable once Epic M merges. Mid-port re-classification (PORT → REWRITE because CC-specific logic found) triggers a NEW Task sub-issue under the owning Epic, not a rewrite of the merged catalog row; the row's `rationale` may be updated via PR with a dated H3 note, but `verdict` itself is append-only history in git.

**`TaskSubIssue.state`** follows standard GitHub issue lifecycle: open → closed on merge of the owning-Epic PR that implements the REWRITE.

**`BrandSystemSection.status`** transitions `placeholder → authored` only when the owning Epic (H, K, or 10-collaborators) enters its Spec Kit cycle; transition is forbidden within this Epic's PR.
