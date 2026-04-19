# Quickstart: Using the TUI Component Catalog + Brand System

**Feature**: 034-tui-component-catalog
**Target audience**: Future-Epic authors (B/C/D/E/H/I/J/K/L/M), Brand Guardian reviewers, Accessibility Auditors.
**Time to first answer**: < 30 minutes (SC-008 readability target).

---

## 1 · I'm a future-Epic author. How do I use this?

### 1.1 Before you run `/speckit-specify`

1. Open `docs/tui/component-catalog.md`.
2. Search for your Epic's owning-Epic ID (e.g., `H #1302`).
3. Read every row assigned to your Epic — these are the components you will PORT or REWRITE.
4. Also read every DISCARD row in families your Epic touches (e.g., H's Onboarding family has DISCARD rows for developer-domain onboarding steps) — understanding *why* those are excluded prevents accidentally porting them.

### 1.2 Copy-paste checklist into your Epic's specify input

Per FR-029, copy this block verbatim into your `/speckit-specify` input and check each item:

```markdown
## References (from Epic M #1310 catalog)

- [ ] I have read `docs/tui/component-catalog.md` and listed every row assigned to my Epic.
- [ ] My spec cites `docs/design/brand-system.md` §1 (brand metaphor) + §2 (token naming doctrine) as source-of-truth.
- [ ] For every PORT/REWRITE row, my spec cites the matching row in `docs/tui/accessibility-gate.md` and inherits its WCAG/KWCAG constraints.
- [ ] For every REWRITE row, my spec proposes a Task that satisfies the row's `AccessibilityGateRow.acceptance_checklist` constraints.
- [ ] My Epic's new tokens conform to `{metaphorRole}{Variant}?` per FR-009 and pass the grep gate.
```

### 1.3 When you add a new token

1. Open `docs/design/brand-system.md` §1 — confirm the semantic role (and ministry code, if satellite) is in the vocabulary.
2. If the semantic role is new: propose a §1 ministry-roster addition in your Epic's PR, cite this quickstart.
3. Use the grammar from §2: `{metaphorRole}{Variant}?`. Examples:
   - ✅ `orbitalRingBackground`
   - ✅ `agentSatelliteKoroad`
   - ✅ `kosmosCoreShimmer`
   - ❌ `primary` — banned (BAN-04)
   - ❌ `accent1` — banned (BAN-05)
   - ❌ `mainColor` — banned (BAN-06)
4. When the grep gate ships (Deferred row 11), it will validate at PR time. Until then, Brand Guardian reviews the diff manually using §2 as reference.

---

## 2 · I'm a Brand Guardian. How do I reject a bad token?

### 2.1 Single-citation rejection workflow

1. Read the proposed token name.
2. Open `docs/design/brand-system.md` §2 → find the matching BAN-XX subsection.
3. Post a PR review comment with:
   > "Token `{name}` violates §2 rule BAN-XX: `{error_message}`. Propose an alternative using the grammar from §2 (`{metaphorRole}{Variant}?`)."

### 2.2 Worked examples

| Proposed | Violates | Suggested alternative |
|---|---|---|
| `primary` | BAN-04 | `kosmosCore` (if core-color role) or a ministry satellite |
| `accent1` | BAN-05 | Name the role explicitly (e.g., `autoAccept`, `planMode`) |
| `claudeShimmer` (new) | BAN-01 | `orbitalRingShimmer` if tool-loop visual; `kosmosCoreShimmer` if headline emphasis |
| `mainColor` | BAN-06 | Decompose into context (`promptBorder`, `subtitle`, etc.) |
| `background` | BAN-07 | `orbitalRingBackground` or another qualified form |

### 2.3 Escalation

If a token legitimately doesn't fit the grammar (rare; expected for wholly new UI paradigms), request an ADR under `docs/adr/` amending §2. Do not approve the PR pending ADR.

---

## 3 · I'm an Accessibility Auditor. How do I use the gate?

### 3.1 Per-PR flow

1. For each file changed under `tui/src/components/`, look up its `CC source path` in `docs/tui/accessibility-gate.md`.
2. Check that the PR's new code satisfies every WCAG criterion listed for that row.
3. For citizen-facing families, check `KWCAG notes` column for Korean-specific requirements.
4. For rows with `IME-safe = yes`, verify the PR's keyboard handlers gate on `!useKoreanIME().isComposing`.
5. For rows with `Contrast constraint = 4.5:1`, verify the palette value chosen by Epic H satisfies the constraint.

### 3.2 When the gate row is missing

If a PR touches a component whose catalog verdict is PORT/REWRITE but no gate row exists → fail the PR with a pointer to this quickstart §3.1.

---

## 4 · I'm a reviewer of Epic M itself (`/speckit-analyze` or PR review)

### 4.1 What `/speckit-analyze` verifies

- Constitution §I reference mapping (research.md §1).
- Deferred-items table consistency (research.md §3).
- `docs/tui/component-catalog.md` row coverage (contracts/catalog-row-schema.md §3).
- `docs/design/brand-system.md` section-level invariants BSS-01..BSS-09 (contracts/brand-system-sections.md §5).
- `docs/tui/accessibility-gate.md` row invariants AG-01..AG-06 (contracts/accessibility-gate-rows.md §6).
- §3–§10 scope-violation trap (contracts/brand-system-sections.md §6).

### 4.2 What a human reviewer verifies

- SC-008: pick a random Phase-2 newcomer persona, can they spec their Epic's Tasks from the catalog + ADR-006 + sourcemap alone in < 30 minutes?
- SC-012: simulate an ad-hoc token proposal (`primary`). Can Brand Guardian reject it citing a single §2 subsection?
- Spot-check 5 random DISCARD rows for evidence-citation quality.
- Spot-check 5 random REWRITE rows for Task sub-issue linkage (after `/speckit-taskstoissues` runs).

---

## 5 · Quick reference — file layout

```
specs/034-tui-component-catalog/
├── spec.md                     # WHAT and WHY
├── plan.md                     # HOW (this planning output)
├── research.md                 # Phase 0 — references + deferred validation
├── data-model.md               # Phase 1 — logical entity shapes
├── contracts/
│   ├── catalog-row-schema.md           # docs/tui/component-catalog.md row format
│   ├── token-naming-grammar.md         # MetaphorRole grammar + BAN rules
│   ├── brand-system-sections.md        # docs/design/brand-system.md layout
│   ├── accessibility-gate-rows.md      # docs/tui/accessibility-gate.md row format
│   └── grep-gate-rules.md              # Brand Guardian CI gate spec (impl deferred)
├── quickstart.md               # (this file)
└── checklists/                 # pre-existing checklists from `/speckit-checklist`

Deliverables of this Epic's PR:
├── docs/tui/component-catalog.md      # NEW — 389 rows across 31+ families
├── docs/tui/accessibility-gate.md     # NEW — per-PORT/REWRITE row
├── docs/design/brand-system.md        # NEW — §1, §2 authored; §3-§10 placeholders
└── tui/src/theme/tokens.ts            # MODIFIED — type surface only (if any new tokens are needed for catalog examples; otherwise untouched)
```

## 6 · Who owns what — at-a-glance

| Artifact | Owner | Status at Epic M merge |
|---|---|---|
| `docs/tui/component-catalog.md` | Epic M #1310 | authored (389 rows) |
| `docs/tui/accessibility-gate.md` | Epic M #1310 | authored (per PORT/REWRITE) |
| `docs/design/brand-system.md` §1, §2 | Epic M #1310 | authored (≥ 500 words each) |
| `docs/design/brand-system.md` §3–§9 | Epic H #1302 | placeholder (≤ 50 words, owner pointer) |
| `docs/design/brand-system.md` §10 | all design-concerned Epics | placeholder + append-log convention |
| Grep CI gate workflow | Epic M (post-verdict Task) | deferred; tracked |
| Per-component REWRITE impl | B/C/D/E/H/I/J/K/L/M | deferred to owning Epic |
| Concrete palette values | Epic H #1302 | deferred; catalog provides contrast constraint |
| KWCAG deep-compliance audit | #25 Public Beta Readiness | deferred to Phase 3+ |
