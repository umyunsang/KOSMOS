# Audit: `tui/src/theme/tokens.ts` — Epic M #1310 FR-030 Compliance

**Auditor**: Team Z (Frontend Developer Sonnet teammate)
**Date**: 2026-04-20
**Branch**: 034-tui-component-catalog
**Scope**: FR-008, FR-009, FR-010, FR-030, FR-031

---

## Pre-audit Identifier Count

**69** — exactly matches `specs/034-tui-component-catalog/artifacts/existing-tokens.txt`.

---

## BAN-01..BAN-07 Compliance Check

### BAN-01 `^claude[A-Za-z0-9_]*$` — CC-legacy prefix

| Identifier | Status |
|---|---|
| `claude` | CC-legacy allow-list (pre-existing). DO NOT rename. |
| `claudeShimmer` | CC-legacy allow-list (pre-existing). DO NOT rename. |
| `claudeBlue_FOR_SYSTEM_SPINNER` | CC-legacy allow-list (pre-existing). DO NOT rename. |
| `claudeBlueShimmer_FOR_SYSTEM_SPINNER` | CC-legacy allow-list (pre-existing). DO NOT rename. |
| `briefLabelClaude` | Qualified compound — BAN-01 regex `^claude.*$` does NOT match (starts `briefLabel`, not `claude`). **PASSES**. |

### BAN-02 `^clawd[A-Za-z0-9_]*$` — leaked-source prefix

| Identifier | Status |
|---|---|
| `clawd_body` | CC-legacy allow-list (pre-existing). DO NOT rename. |
| `clawd_background` | CC-legacy allow-list (pre-existing). DO NOT rename. |

### BAN-03 `^anthropic[A-Za-z0-9_]*$` — vendor-specific prefix

**No identifiers matching this pattern.** COMPLIANT.

### BAN-04 `^(primary|secondary|tertiary)$` — content-free tokens

**No identifiers matching this pattern.** COMPLIANT.

Note: `success`, `error`, `warning` are semantic-safety keywords exempt from BAN-04 per grammar §3.

### BAN-05 `^accent[0-9]+$` — numeric-suffix ordinal tokens

**No identifiers matching this pattern.** COMPLIANT.

### BAN-06 `^mainColor$` — undescriptive token

**No identifiers matching this pattern.** COMPLIANT.

### BAN-07 `^(background|foreground)$` — standalone unqualified tokens

| Identifier | Status |
|---|---|
| `background` | Matches BAN-07 regex. However, this is a CC-legacy allow-list member (pre-existing at grep-gate ship commit). **PASSES via allow-list**. DO NOT rename under this Epic (Deferred Items row 10). |

All other `*Background*` identifiers (`clawd_background`, `userMessageBackground`, `userMessageBackgroundHover`, `messageActionsBackground`, `bashMessageBackgroundColor`, `memoryBackgroundColor`) are qualified compound forms — BAN-07 standalone regex `^(background|foreground)$` does NOT match them. **PASS**.

---

## Full Identifier Classification Table

| # | Identifier | BAN check | Disposition |
|---|---|---|---|
| 1 | `autoAccept` | None triggered | Semantic role; allow-list legacy |
| 2 | `background` | BAN-07 match | Allow-list legacy; no rename |
| 3 | `bashBorder` | None | Allow-list legacy |
| 4 | `bashMessageBackgroundColor` | None | Allow-list legacy |
| 5 | `blue_FOR_SUBAGENTS_ONLY` | None | Allow-list legacy |
| 6 | `briefLabelClaude` | None (not `^claude`) | Allow-list legacy |
| 7 | `briefLabelYou` | None | Allow-list legacy |
| 8 | `chromeYellow` | None | Allow-list legacy |
| 9 | `claude` | BAN-01 match | Allow-list legacy; no rename |
| 10 | `claudeBlue_FOR_SYSTEM_SPINNER` | BAN-01 match | Allow-list legacy; no rename |
| 11 | `claudeBlueShimmer_FOR_SYSTEM_SPINNER` | BAN-01 match | Allow-list legacy; no rename |
| 12 | `claudeShimmer` | BAN-01 match | Allow-list legacy; no rename |
| 13 | `clawd_background` | BAN-02 match | Allow-list legacy; no rename |
| 14 | `clawd_body` | BAN-02 match | Allow-list legacy; no rename |
| 15 | `cyan_FOR_SUBAGENTS_ONLY` | None | Allow-list legacy |
| 16 | `diffAdded` | None | Allow-list legacy |
| 17 | `diffAddedDimmed` | None | Allow-list legacy |
| 18 | `diffAddedWord` | None | Allow-list legacy |
| 19 | `diffRemoved` | None | Allow-list legacy |
| 20 | `diffRemovedDimmed` | None | Allow-list legacy |
| 21 | `diffRemovedWord` | None | Allow-list legacy |
| 22 | `error` | None (semantic-safety exempt) | Pass |
| 23 | `fastMode` | None | Allow-list legacy |
| 24 | `fastModeShimmer` | None | Allow-list legacy |
| 25 | `green_FOR_SUBAGENTS_ONLY` | None | Allow-list legacy |
| 26 | `ide` | None | Allow-list legacy |
| 27 | `inactive` | None (semantic role) | Pass |
| 28 | `inactiveShimmer` | None | Allow-list legacy |
| 29 | `inverseText` | None (semantic role) | Pass |
| 30 | `memoryBackgroundColor` | None | Allow-list legacy |
| 31 | `merged` | None | Allow-list legacy |
| 32 | `messageActionsBackground` | None | Allow-list legacy |
| 33 | `orange_FOR_SUBAGENTS_ONLY` | None | Allow-list legacy |
| 34 | `permission` | None | Allow-list legacy |
| 35 | `permissionShimmer` | None | Allow-list legacy |
| 36 | `pink_FOR_SUBAGENTS_ONLY` | None | Allow-list legacy |
| 37 | `planMode` | None | Allow-list legacy |
| 38 | `professionalBlue` | None | Allow-list legacy |
| 39 | `promptBorder` | None | Allow-list legacy |
| 40 | `promptBorderShimmer` | None | Allow-list legacy |
| 41 | `purple_FOR_SUBAGENTS_ONLY` | None | Allow-list legacy |
| 42 | `rainbow_blue` | None | Allow-list legacy |
| 43 | `rainbow_blue_shimmer` | None | Allow-list legacy |
| 44 | `rainbow_green` | None | Allow-list legacy |
| 45 | `rainbow_green_shimmer` | None | Allow-list legacy |
| 46 | `rainbow_indigo` | None | Allow-list legacy |
| 47 | `rainbow_indigo_shimmer` | None | Allow-list legacy |
| 48 | `rainbow_orange` | None | Allow-list legacy |
| 49 | `rainbow_orange_shimmer` | None | Allow-list legacy |
| 50 | `rainbow_red` | None | Allow-list legacy |
| 51 | `rainbow_red_shimmer` | None | Allow-list legacy |
| 52 | `rainbow_violet` | None | Allow-list legacy |
| 53 | `rainbow_violet_shimmer` | None | Allow-list legacy |
| 54 | `rainbow_yellow` | None | Allow-list legacy |
| 55 | `rainbow_yellow_shimmer` | None | Allow-list legacy |
| 56 | `rate_limit_empty` | None | Allow-list legacy |
| 57 | `rate_limit_fill` | None | Allow-list legacy |
| 58 | `red_FOR_SUBAGENTS_ONLY` | None | Allow-list legacy |
| 59 | `remember` | None (semantic role) | Pass |
| 60 | `selectionBg` | None | Allow-list legacy |
| 61 | `subtle` | None (semantic role) | Pass |
| 62 | `success` | None (semantic-safety exempt) | Pass |
| 63 | `suggestion` | None (semantic role) | Pass |
| 64 | `text` | None (semantic role) | Pass |
| 65 | `userMessageBackground` | None | Allow-list legacy |
| 66 | `userMessageBackgroundHover` | None | Allow-list legacy |
| 67 | `warning` | None (semantic-safety exempt) | Pass |
| 68 | `warningShimmer` | None | Allow-list legacy |
| 69 | `yellow_FOR_SUBAGENTS_ONLY` | None | Allow-list legacy |

---

## Epic H REWRITE Cross-Reference (Step 3)

Catalog REWRITE rows owned by Epic H #1302 that reference new token names:

- `AnimatedAsterisk.tsx` — references `kosmosCore` glyph (ADR-006 A-9), but this is a **component vocabulary** reference, not a token name required in `tokens.ts` today. Epic H will define the `kosmosCore*` token values.
- `WelcomeV2.tsx` — references `kosmosCore` metaphor; same as above.
- `KosmosCoreIcon.tsx` (`FastIcon.tsx` REWRITE) — references `kosmosCore` asterisk; same as above.
- `CondensedLogo.tsx`, `Feed.tsx`, `feedConfigs.tsx`, `LogoV2.tsx` — brand rewrite targets; no token surface additions required today.

**Conclusion**: All Epic H REWRITE rows that reference `kosmosCore*`, `orbitalRing*`, or `agentSatellite*` names are planned under Epic H #1302's own Spec Kit cycle. No Epic M REWRITE row requires a new token identifier to be added to `tokens.ts` under this Epic.

Epic M REWRITE rows (Spinner/TeammateSpinnerLine, TeammateSpinnerTree, TaskAssignmentMessage, UserTeammateMessage, etc.) reference KOSMOS agent swarm vocabulary at the component and copy level, not at the theme token level.

---

## Post-audit Identifier Count

**69** — unchanged.

## Net-new Identifiers Added

**None.**

## Rationale

No additions are required under Epic M #1310. All candidate KOSMOS brand tokens (`kosmosCore*`, `orbitalRing*`, `agentSatellite{Ministry}*`, `wordmark*`, `subtitle*`) are planned as Epic H #1302's deliverables under its own Spec Kit cycle. Adding token NAME surface ahead of Epic H's palette VALUE definitions (FR-010 explicitly separates name surface from palette values) would create orphaned stubs with no palette binding and no consuming component — a spec violation of the Epic boundary contract.

The statement from `plan.md §Project Structure` is confirmed: **"Most Epics require zero additions — this Task completes as a no-op with an audit summary comment."**

---

## `tokens.ts` Modified?

**No.**

---

## Files Read

- `/Users/um-yunsang/KOSMOS/tui/src/theme/tokens.ts`
- `/Users/um-yunsang/KOSMOS/specs/034-tui-component-catalog/artifacts/existing-tokens.txt`
- `/Users/um-yunsang/KOSMOS/specs/034-tui-component-catalog/contracts/token-naming-grammar.md`
- `/Users/um-yunsang/KOSMOS/specs/034-tui-component-catalog/contracts/grep-gate-rules.md`
- `/Users/um-yunsang/KOSMOS/specs/034-tui-component-catalog/spec.md` (lines 125–154)
- `/Users/um-yunsang/KOSMOS/docs/tui/component-catalog.md` (grep scan for REWRITE rows + `kosmosCore` references)

## Audit File Written

- `/Users/um-yunsang/KOSMOS/specs/034-tui-component-catalog/artifacts/tokens-ts-audit.md`
