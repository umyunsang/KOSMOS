# Contract: Token Naming Grammar for `tui/src/theme/tokens.ts`

**Feature**: 034-tui-component-catalog
**Phase**: 1 (Design & Contracts)
**Authoritative sections in `docs/design/brand-system.md`**: §1 (Brand metaphor), §2 (Token naming doctrine).

---

## 1 · Grammar (BNF)

```
TokenName       ::= MetaphorRole Variant?
MetaphorRole    ::= "kosmosCore"
                  | "orbitalRing"
                  | "wordmark"
                  | "subtitle"
                  | "agentSatellite" MinistryCode
                  | "permissionGauntlet"
                  | "planMode"
                  | "autoAccept"
                  | SemanticRole
MinistryCode    ::= "Koroad" | "Kma" | "Hira" | "Nmc" | "Nfa119" | "Geocoding" | …
                    (open-ended; each new ministry MUST be added to §1 of brand-system.md before use)
SemanticRole    ::= "success" | "error" | "warning" | "info" | "text" | "inverseText"
                  | "inactive" | "subtle" | "suggestion" | "remember"
Variant         ::= <TitleCased> (one of: "Shimmer" | "Muted" | "Hover" | "Active"
                                  | "Background" | "Border" | "Dimmed" | "Selected"
                                  | …  open-ended with owner-Epic approval)
```

- `MetaphorRole` is **camelCase starting lowercase**.
- `Variant` is **TitleCased** (initial capital) — e.g., `orbitalRingShimmer`, not `orbitalring_shimmer`.
- Concatenation is direct, no separator: `{role}{Variant}`.

### 1.1 · Canonical regex (BNF-derived, for `lint-tokens.mjs` Deferred row 11)

The single canonical regex below is derived 1:1 from the BNF above. Any token identifier added to `tui/src/theme/tokens.ts` type surface MUST match this regex AND not match any BAN-01..BAN-07 rule in §2. When the BNF changes (e.g., new `MinistryCode` or new `Variant`), this regex MUST be updated in the same PR.

```regex
^(kosmosCore|orbitalRing|wordmark|subtitle|agentSatellite(Koroad|Kma|Hira|Nmc|Nfa119|Geocoding)|permissionGauntlet|planMode|autoAccept|success|error|warning|info|text|inverseText|inactive|subtle|suggestion|remember)(Shimmer|Muted|Hover|Active|Background|Border|Dimmed|Selected)?$
```

**Caveats**:
- `MinistryCode` alternation is closed to the six ministries listed in `docs/design/brand-system.md §1 ministry roster` at the time of this PR. Adding a new ministry requires a one-line PR against that roster plus a regex update here.
- `Variant` alternation reflects the eight variants listed in the BNF. New variants require owner-Epic approval (see BNF note) plus a regex update.
- The regex does NOT encode BAN-01..BAN-07 exclusions — the lint script runs both checks: (i) name matches this regex; (ii) name does not match any BAN regex from §2.

## 2 · Banned patterns (enforced by grep gate)

Regex applied to every identifier added in a PR touching `tui/src/theme/tokens.ts` type surface (not imports):

| ID | Regex | Error message |
|---|---|---|
| BAN-01 | `^claude[A-Za-z0-9_]*$` | `Banned token: CC-legacy '{name}'. See brand-system.md §2 — use an 'orbitalRing*' or ministry-specific name instead.` |
| BAN-02 | `^clawd[A-Za-z0-9_]*$` | `Banned token: leaked-source prefix '{name}'. Remove; rename under KOSMOS metaphor vocabulary.` |
| BAN-03 | `^anthropic[A-Za-z0-9_]*$` | `Banned token: vendor-specific '{name}'. KOSMOS is not an Anthropic product.` |
| BAN-04 | `^(primary\|secondary\|tertiary)$` | `Banned token: content-free '{name}'. Use a semantic role from brand-system.md §1 (e.g., 'kosmosCore', 'orbitalRing', or a ministry satellite).` |
| BAN-05 | `^accent[0-9]+$` | `Banned token: numeric-suffix '{name}'. Tokens must describe semantic role, not ordinal.` |
| BAN-06 | `^mainColor$` | `Banned token: '{name}' conveys no semantic intent.` |
| BAN-07 | `^(background\|foreground)$` | `Banned token: standalone '{name}'. Qualify with a role (e.g., 'orbitalRingBackground', 'kosmosCoreForeground').` |

## 3 · Exceptions

- **Semantic-safety keywords** (`success`, `error`, `warning`, `info`) are WCAG-aligned semantic slots. They pass BAN-04 despite being "content-free" at first glance — their meaning is accessibility-driven, not brand-driven.
- **CC-legacy tokens under deprecation** (e.g., `claudeShimmer`, `claudeBlue_FOR_SYSTEM_SPINNER`): these already exist in `tui/src/theme/tokens.ts`. This Epic's FR-008 contract is the NAME SURFACE GATE for **new** additions and **renames**. Mass rename of legacy tokens is **Deferred Items row 10** (NEEDS TRACKING → backfilled by `/speckit-taskstoissues`). The grep gate MUST be configured with an **allow-list** of existing CC-legacy names at the commit where the gate ships, so the gate fails only on NEW violations, not existing ones.
- **Ministry satellite identifier extensions**: new `MinistryCode` values (e.g., a future `agentSatelliteMolit`) require a single-line PR against `docs/design/brand-system.md` §1 ministry roster. The grep gate refers to the §1 roster as its source of truth.

## 4 · Test fixtures (for Sonnet teammate implementing the grep gate under Deferred Items row 11)

**PASS fixtures** (grep gate returns 0):

```typescript
// tokens.ts type surface additions that pass
export type ThemeToken = {
  orbitalRingBackground: string
  kosmosCoreShimmer: string
  agentSatelliteKoroad: string
  agentSatelliteHiraMuted: string
  wordmarkActive: string
  success: string
  warning: string
}
```

**FAIL fixtures** (grep gate returns >0):

```typescript
export type ThemeToken = {
  primary: string          // BAN-04
  accent1: string          // BAN-05
  claudeShimmer: string    // BAN-01 (for a NEW addition; legacy allow-list exempts existing occurrence)
  mainColor: string        // BAN-06
  background: string       // BAN-07 (standalone); 'orbitalRingBackground' would pass
}
```

## 5 · Compliance gate location

- **Spec**: this contract file + `docs/design/brand-system.md` §2.
- **Implementation** (Deferred): `.github/workflows/brand-guardian.yml` running `scripts/lint-tokens.mjs` or equivalent; emits Check Run result; gate fails PR if any identifier violates §2.
- **Invocation**: runs on every PR touching `tui/src/theme/**` or `docs/design/brand-system.md` §1 (ministry roster changes that could unlock new satellite names).

## 6 · Rationale (for Brand Guardian review)

Why `{metaphorRole}{Variant}?` instead of Tailwind/Chakra-style tokens?

- **KOSMOS = 은하계 metaphor** (ADR-006 A-9). Visual tokens carry semantic weight tied to the multi-ministry orchestration story. A reader of `orbitalRingShimmer` immediately understands it decorates the tool-loop visual affordance; a reader of `accent2` understands nothing.
- **Brand Guardian can reject with a single citation**: BAN rules map 1:1 to a §2 subsection. No judgment call required.
- **Cross-Epic consistency** (SC-012 test): a simulated ad-hoc proposal like `primary`, `accent1`, or `claudeShimmer` can be rejected by citing BAN-04, BAN-05, or BAN-01 respectively.
