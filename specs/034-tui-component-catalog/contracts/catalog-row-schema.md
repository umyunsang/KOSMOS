# Contract: `docs/tui/component-catalog.md` Row Schema

**Feature**: 034-tui-component-catalog
**Phase**: 1 (Design & Contracts)
**Consumed by**: `/speckit-tasks`, `/speckit-analyze`, `/speckit-taskstoissues`, `/speckit-implement`, Brand Guardian review, Accessibility Auditor review.

---

## 1 · Catalog file header (mandatory)

The first 20 lines of `docs/tui/component-catalog.md` MUST contain:

```markdown
# TUI Component Catalog — CC → KOSMOS Verdict Matrix

**Epic**: M #1310
**Branch at authoring**: 034-tui-component-catalog
**Commit at authoring**: <KOSMOS repo HEAD at merge>
**CC sourcemap commit (pinned)**: a8a678c
**CC file count at pinned commit**: 389 (`.tsx` + `.ts` under `.references/claude-code-sourcemap/restored-src/src/components/`)
**Top-level subdirectories**: 31
**Recount evidence**: `find .references/claude-code-sourcemap/restored-src/src/components -type f \( -name "*.tsx" -o -name "*.ts" \) | wc -l` on 2026-04-20 at HEAD 34c48f4
**File-count discrepancy note**: Epic body #1310 title claims 286 files; 2026-04-20 recount verified 389. This catalog supersedes the Epic body number.

**Downstream Epic contract**: every subsequent spec input for Epics B #1297, C #1301, D #1299, E #1300, H #1302, I #1303, J #1307, K #1308, L #1309 MUST cite this catalog and `docs/design/brand-system.md` as source-of-truth.
```

## 2 · Row format (per FR-006; PARITY.md-inspired)

```markdown
| # | CC source path | Files | Family | Verdict | Owning Epic | KOSMOS target | Rationale | Evidence | Accessibility gate | Task sub-issue | Feature commit | Merge commit |
|---|---|---:|---|---|---|---|---|---|---|---|---|---|
```

### 2.1 Column semantics

| Column | Required for | Rules |
|---|---|---|
| `#` | all rows | 1-indexed row number |
| `CC source path` | all rows | relative path from `.references/claude-code-sourcemap/restored-src/src/components/`; aggregated rows use the family name with trailing `/*` |
| `Files` | all rows | integer; 1 for per-file rows, N for aggregated rows |
| `Family` | all rows | one of 31 subdirectory names OR `root.<semantic-bin>` for root-level files (e.g., `root.logo-wordmark`, `root.dialogs`, `root.shortcuts`, `root.dev-ui`) |
| `Verdict` | all rows | one of `PORT` \| `REWRITE` \| `DISCARD` \| `DEFER` |
| `Owning Epic` | PORT/REWRITE/DEFER | format `{id} #{issue}` (e.g., `H #1302`); CLOSED Epics annotated `{id} #{issue} (closed)` |
| `KOSMOS target` | PORT/REWRITE only | absolute path under `tui/src/` (creating directories allowed) |
| `Rationale` | DISCARD/DEFER (mandatory); PORT/REWRITE (recommended) | free-text; for DISCARD must start with one of `ADR-006 Part D-1`, `ADR-006 Part D-3`, or `Domain mismatch:`; for DEFER must contain `unblock when` |
| `Evidence` | all rows | citation to file path, spec number, or ADR section |
| `Accessibility gate` | PORT/REWRITE | markdown anchor into `docs/tui/accessibility-gate.md` |
| `Task sub-issue` | REWRITE (filled by `/speckit-taskstoissues`) | `#<number>` or `—` (for M-itself rows whose work lives in this spec) |
| `Feature commit` | post-implementation | short SHA or `—` at Epic M merge |
| `Merge commit` | post-implementation | short SHA or `—` at Epic M merge |

### 2.2 Closed-Epic ownership rule (research §R3)

When `Owning Epic` is `B #1297 (closed)` or `A #1298 (closed)`:

- If the CC component is already fully delivered by the closed Epic's ship: `Verdict = PORT`, `Rationale = "implementation complete; delivered by #<PR>"`, `Task sub-issue = —`.
- If additional TUI-side rewrite is still needed: `Verdict = REWRITE`, `Task sub-issue` is re-parented to Epic M (`parent_epic = M #1310`) per `TaskSubIssue` invariant I2 and I16 in `data-model.md`.

### 2.3 Aggregation rule (FR-027)

A family with > 10 REWRITE rows MAY be collapsed into one aggregated row:

- `CC source path` = `<family>/*`
- `Files` = N (constituent count)
- `Rationale` MUST enumerate the constituent file list with line-items (`- permissions/PermissionDialog.tsx`, …).
- Aggregated rows generate **one** `TaskSubIssue` whose body lists the constituent files.

## 3 · Validation checklist (consumed by `/speckit-analyze`)

1. **SC-001**: sum of `Files` across all rows == 389.
2. **FR-001**: every `.tsx`/`.ts` under `restored-src/src/components/` at commit `a8a678c` appears in exactly one row (per-file OR in an aggregated row's Rationale list).
3. **FR-002**: every row has values in `CC source path`, `Files`, `Family`, `Verdict`, `Evidence`.
4. **FR-003**: `Owning Epic` values ⊆ `{B, C, D, E, H, I, J, K, L, M}` (literal strings match the id prefix).
5. **FR-004** (SC-005): every DISCARD row's `Rationale` starts with `ADR-006 Part D-1`, `ADR-006 Part D-3`, or `Domain mismatch:`.
6. **FR-005** (SC-006): every DEFER row's `Rationale` contains `unblock when`.
7. **FR-006**: table contains all columns from §2.
8. **FR-007**: header declares the 389 vs. 286 discrepancy.
9. **Invariant I6**: every PORT/REWRITE row has non-empty `Accessibility gate` column.

## 4 · Appendix — Downstream Epic spec-input checklist (FR-029)

> Copy-paste into your Epic's `specify` input. Shortened to 5 bullets per SC-010.

```markdown
## References (from Epic M #1310 catalog)

- [ ] I have read `docs/tui/component-catalog.md` and listed every row assigned to my Epic.
- [ ] My spec cites `docs/design/brand-system.md` §1 (brand metaphor) + §2 (token naming doctrine) as source-of-truth.
- [ ] For every PORT/REWRITE row, my spec cites the matching row in `docs/tui/accessibility-gate.md` and inherits its WCAG/KWCAG constraints.
- [ ] For every REWRITE row, my spec proposes a Task that satisfies the `AccessibilityGateRow.acceptance_checklist` derived constraints.
- [ ] My Epic's new tokens conform to `{metaphorRole}{Variant}?` per FR-009 and pass the grep gate at `.github/workflows/brand-guardian.yml`.
```
