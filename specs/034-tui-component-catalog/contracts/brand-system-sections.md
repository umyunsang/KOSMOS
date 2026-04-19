# Contract: `docs/design/brand-system.md` Section Layout

**Feature**: 034-tui-component-catalog
**Phase**: 1 (Design & Contracts)
**Owning Epic of §1, §2 (authoritative sections)**: M #1310.
**Owning Epics of §3–§10 (placeholders)**: H #1302 (§3–§9), all design-concerned Epics + M (§10).

---

## 1 · File structure (FR-012, FR-013, FR-014)

```markdown
# KOSMOS Brand System

## §1 Brand metaphor
<authored by Epic M #1310; ≥ 500 words>

## §2 Token naming doctrine
<authored by Epic M #1310; ≥ 500 words; embeds/references contracts/token-naming-grammar.md>

## §3 Logo usage
**Owner: Epic H #1302**
<≤ 50-word placeholder>

## §4 Palette values
**Owner: Epic H #1302**
<≤ 50-word placeholder>

## §5 Typography scale
**Owner: Epic H #1302**
<≤ 50-word placeholder>

## §6 Spacing / grid
**Owner: Epic H #1302**
<≤ 50-word placeholder>

## §7 Motion
**Owner: Epic H #1302**
<≤ 50-word placeholder>

## §8 Voice & tone
**Owner: Epic H #1302 + Epic K #1308**
<≤ 50-word placeholder>

## §9 Iconography
**Owner: Epic H #1302**
<≤ 50-word placeholder>

## §10 Component usage guidelines
**Owners: all design-concerned Epics (B/C/D/E/H/I/J/K/L/M)**
<≤ 50-word placeholder + note: "Each downstream Epic appends a dated H3 subheading as its components ship.">
```

## 2 · §1 Brand metaphor — required content outline (FR-015)

Authored in this Epic. MUST cover (non-exhaustive — word count target ≥ 500):

1. **The KOSMOS (은하계) integration metaphor** — why fragmented ministry interfaces (DX infrastructure) resolve into a single citizen conversation (AX harness). Ties to `docs/vision.md § What is original to KOSMOS` and Korea AI Action Plan Principle 8 (single conversational window).
2. **Visual element vocabulary** — ring + core + satellites + wordmark + subtitle, mapped to ADR-006 A-9 onboarding splash. Each visual has a semantic role the TUI renders.
3. **Ministry satellite roster** — current ministries (KOROAD, KMA, HIRA, NMC, 119, Geocoding). Extensions require appending to this roster before a new `agentSatellite{MINISTRY}` token can ship (FR-009 cross-reference).
4. **Why metaphor matters for a text UI** — text-grid rendering does not show the ring or satellites literally, but color tokens carry the metaphor into every visible element. A reader of `orbitalRingShimmer` inherits the orchestration story even without a literal ring on screen.
5. **Permanent cross-references**: ADR-006 A-9, `assets/kosmos-{logo,banner-dark}.svg`, Korea AI Action Plan 공공AX Principle 8/9.

## 3 · §2 Token naming doctrine — required content outline (FR-016)

Authored in this Epic. MUST cover (target ≥ 500 words):

1. **Grammar** — inline the `{metaphorRole}{Variant}?` BNF from `contracts/token-naming-grammar.md` (or reference by stable link).
2. **Banned patterns** — reproduce the BAN-01..BAN-07 table with error messages.
3. **Exceptions** — semantic-safety keywords; CC-legacy allow-list convention.
4. **Ministry roster pointer** — §1's roster is the source of truth for `agentSatellite{MINISTRY}` extensions; §2 only restates the lookup.
5. **Brand Guardian review contract** — each PR touching `tui/src/theme/**` gets a Check Run from the grep gate (Deferred row 11); Brand Guardian may manually override an exception on a case-by-case basis but MUST leave a PR comment citing the §2 exception category.
6. **Rejection precedent** — three worked examples of simulated ad-hoc proposals (`primary`, `accent1`, `claudeShimmer`) and the exact §2 subsection that rejects each (SC-012 test).
7. **Future-proofing** — when a new metaphor role becomes necessary (e.g., a `plugin` or `skill` visual emerges), process for extending §2 via an ADR vs. an in-place §2 edit.

## 4 · §3–§10 placeholders — exact text template (FR-014)

Every §3–§9 placeholder body MUST be ≤ 50 words AND contain:

```markdown
**Owner: Epic H #1302**

This section is intentionally a placeholder until Epic H #1302 enters its Spec Kit cycle. Do not edit
under Epic M — edits land as part of Epic H's PR. See Epic M #1310 FR-014 for the scope rule.
```

Variations:

- §8 (voice & tone): `**Owners: Epic H #1302 + Epic K #1308**` — one or the other (or both, collaborative) fills it.
- §10 (component usage): `**Owners: all design-concerned Epics (B/C/D/E/H/I/J/K/L/M)**` and append the note about dated H3 subheadings.

## 5 · Authoring-time invariants (consumed by `/speckit-analyze`)

| Invariant | Rule | FR |
|---|---|---|
| BSS-01 | Exactly 10 `^## §` H2 headings; numbers 1..10 in order | FR-012 |
| BSS-02 | §1 body word count ≥ 500 | FR-013, SC-003 |
| BSS-03 | §2 body word count ≥ 500 | FR-013, SC-003 |
| BSS-04 | §3–§9 body word count ≤ 50 each | FR-014, SC-003 |
| BSS-05 | §10 body word count ≤ 50 | FR-014, SC-003 |
| BSS-06 | §3–§10 body each contains literal `Owner:` line | FR-014 |
| BSS-07 | §1 contains the literal strings `KOSMOS`, `은하계`, and a ministry roster header | FR-015 |
| BSS-08 | §2 contains the literal strings `BAN-01`..`BAN-07` | FR-016 |
| BSS-09 | No text between `# KOSMOS Brand System` and `## §1` (no untracked preamble) | FR-012 cleanliness |

## 6 · Scope-violation trap

Any line edit in §3–§10 beyond the owner pointer + 50-word placeholder, within a PR on branch `034-tui-component-catalog`, is a scope violation subject to `/speckit-analyze` rejection per FR-034. `/speckit-analyze` MUST run BSS-04, BSS-05, BSS-06 checks.
