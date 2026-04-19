# Contract: `docs/tui/accessibility-gate.md` Row Schema

**Feature**: 034-tui-component-catalog
**Phase**: 1 (Design & Contracts)
**Paired with**: `catalog-row-schema.md` — every PORT/REWRITE catalog row has exactly one row here.

---

## 1 · File header

```markdown
# TUI Accessibility Gate

**Epic**: M #1310
**WCAG baseline**: 2.1 AA (subset — see §2)
**KWCAG baseline**: 한국 접근성 지침 2.2 (citizen-facing surfaces only)
**Palette-selection constraint for Epic H #1302**: body text ≥ 4.5:1 contrast, large text / non-text ≥ 3:1 (FR-022)
**IME composition rule**: every component that accepts text input MUST honor `useKoreanIME().isComposing`; see Epic E #1300 contract.
```

## 2 · WCAG 2.1 AA criteria set (FR-019)

The closed set — rows MUST NOT cite criteria outside this set:

| ID | Name | Typical TUI application |
|---|---|---|
| 1.4.3 | Contrast (Minimum) | Every foreground/background pair in the component's rendered output ≥ 4.5:1 (text) or 3:1 (non-text) |
| 2.1.1 | Keyboard | All interactive affordances reachable via keyboard |
| 2.4.7 | Focus Visible | Focus indicator must be visible on terminal (e.g., inverse video or explicit border) |
| 3.3.2 | Labels or Instructions | Input surfaces display a visible label or placeholder instruction |
| 4.1.2 | Name Role Value | Screen-reader-exposed semantic role; deferred to #25 for deep-compliance, but components MUST be annotated with intended role here |

## 3 · Row format

```markdown
| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
```

### 3.1 Column semantics

| Column | Rules |
|---|---|
| `#` | 1-indexed |
| `CC source path` | FK to `CatalogRow.cc_source_path` |
| `Verdict` | `PORT` or `REWRITE` only (DISCARD/DEFER do not appear) |
| `WCAG` | comma-separated subset of `{1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2}`; at minimum `1.4.3` for any visible component |
| `KWCAG notes` | free-text; required for citizen-facing families; `—` otherwise |
| `IME-safe` | `yes` if component accepts text input, `n/a` otherwise |
| `Contrast constraint` | `4.5:1`, `3:1`, or `n/a` |

## 4 · Citizen-facing families (FR-020)

Families whose rows MUST include non-empty `KWCAG notes`:

- `PromptInput`
- `messages`
- `Settings`
- `Onboarding` (root-level family bin `root.onboarding`)
- `HelpV2`
- Any row whose KOSMOS target lives under `tui/src/components/conversation/` or `tui/src/components/input/`
- Any row from subdirectories `Passes`, `permissions`, `Spinner` when surfaced in citizen-visible flows

## 5 · IME-composition flag rule (FR-021)

`IME-safe = yes` MUST be set for every component whose CC source file matches any of:

- contains a `useState<string>` for text input AND renders an Ink `<TextInput>` or `<BaseTextInput>`
- contains an `onSubmit` or `onChange` keyboard handler with a string payload
- lives under `PromptInput/`, `BaseTextInput.tsx`, `CustomSelect/` with search-filter

The row's acceptance checklist (propagated to the generated `TaskSubIssue.acceptance_checklist`) MUST include a line:

```
- [ ] All keyboard handlers gated on `!useKoreanIME().isComposing` before mutating input buffer
```

## 6 · Validation checklist (consumed by `/speckit-analyze`)

| Invariant | Rule | FR |
|---|---|---|
| AG-01 | Every PORT/REWRITE `CatalogRow` has exactly one `AccessibilityGateRow` with matching `CC source path` | FR-018, SC-009 |
| AG-02 | `WCAG` column is non-empty for every row | FR-019 |
| AG-03 | Citizen-facing families (§4) have non-empty `KWCAG notes` | FR-020 |
| AG-04 | `IME-safe = yes` rows have the composition-gate acceptance line in the TaskSubIssue body | FR-021 |
| AG-05 | `Contrast constraint` column values ⊆ `{4.5:1, 3:1, n/a}` | FR-022 |
| AG-06 | Every row's `WCAG` values ⊆ the closed set in §2 | FR-019 |

## 7 · Handoff to Epic H #1302 (FR-022)

The palette-selection constraint is passed to Epic H via the header line:

> **Palette-selection constraint for Epic H #1302**: body text ≥ 4.5:1 contrast, large text / non-text ≥ 3:1.

Epic H's `specify` input MUST acknowledge this line before proposing any concrete color value.
