# Contract: Brand token surface

**Feature**: Epic H #1302
**Phase**: 1
**Owner of authoritative source**: `tui/src/theme/tokens.ts` + `tui/src/theme/dark.ts`
**Grammar reference**: `docs/design/brand-system.md § 2`
**Grep gate reference**: `specs/034-tui-component-catalog/contracts/grep-gate-rules.md`

This contract enumerates every identifier change the Epic H PR makes to the `ThemeToken` type surface and the `darkTheme` value map. The Brand Guardian grep gate parses this contract as its source of truth for "what new tokens this PR intends to add."

---

## § 1 · DELETE set (7 identifiers)

Removed from `ThemeToken` in `tui/src/theme/tokens.ts` AND the corresponding `darkTheme` literal in `tui/src/theme/dark.ts`:

| # | Identifier | Current value | Reason for removal |
|---|---|---|---|
| 1 | `claude` | `rgb(215,119,87)` | BAN-01 — CC-legacy vendor name. |
| 2 | `claudeShimmer` | `rgb(235,159,127)` | BAN-01. |
| 3 | `claudeBlue_FOR_SYSTEM_SPINNER` | `rgb(147,165,255)` | BAN-01. |
| 4 | `claudeBlueShimmer_FOR_SYSTEM_SPINNER` | `rgb(177,195,255)` | BAN-01. |
| 5 | `clawd_body` | `rgb(215,119,87)` | BAN-02 — CC-internal source prefix. |
| 6 | `clawd_background` | `rgb(0,0,0)` | BAN-02. |
| 7 | `briefLabelClaude` | `rgb(215,119,87)` | BAN-01. |

**Migration note**: any KOSMOS component currently importing one of the 7 DELETE identifiers MUST be updated to reference the equivalent KOSMOS metaphor token in the ADD set. A TypeScript compile failure at a consumer site is the intended safety net — it is the signal that the consumer site has not been renamed.

---

## § 2 · ADD set (10 identifiers)

Added to `ThemeToken` + `darkTheme`:

| # | Identifier | Primary hex (→ rgb) | Role | Ministry binding |
|---|---|---|---|---|
| 1 | `kosmosCore` | `#6366f1` → `rgb(99,102,241)` | structural (metaphor) | — |
| 2 | `kosmosCoreShimmer` | `#a5b4fc` → `rgb(165,180,252)` | structural (metaphor, shimmer variant) | — |
| 3 | `orbitalRing` | `#60a5fa` → `rgb(96,165,250)` | structural (metaphor) | — |
| 4 | `orbitalRingShimmer` | `#c7d2fe` → `rgb(199,210,254)` | structural (metaphor, shimmer variant) | — |
| 5 | `wordmark` | `#e0e7ff` → `rgb(224,231,255)` | structural (metaphor) | — |
| 6 | `subtitle` | `#94a3b8` → `rgb(148,163,184)` | structural (metaphor) | — |
| 7 | `agentSatelliteKoroad` | `#f472b6` → `rgb(244,114,182)` | ministry satellite | Koroad |
| 8 | `agentSatelliteKma` | `#34d399` → `rgb(52,211,153)` | ministry satellite | Kma |
| 9 | `agentSatelliteHira` | `#93c5fd` → `rgb(147,197,253)` | ministry satellite | Hira |
| 10 | `agentSatelliteNmc` | `#c4b5fd` → `rgb(196,181,253)` | ministry satellite | Nmc |

**Notes**:

- `kosmosCore` uses the gradient-end value `#6366f1`. The gradient-start `#818cf8` is applied at rendering time via layered `<Text>` elements in `AnimatedAsterisk.tsx`; it is NOT a separate token.
- `kosmosCoreShimmer` and `orbitalRingShimmer` values are selected per research R-2 and verified against WCAG contrast in `contracts/contrast-measurements.md`.
- Ministry-to-accent mapping follows the Assumption recorded in `spec.md` (KOROAD → pink, KMA → mint, HIRA → sky, NMC → lavender). Rationale: the ADR-006 A-9 palette values are accepted verbatim; ministry assignment is Epic H's determination per `docs/design/brand-system.md § 1` explicit deferral.
- Every `agentSatellite*` MinistryCode appears in the `docs/design/brand-system.md § 1` ministry roster. The `Koroad`, `Kma`, `Hira`, `Nmc` entries are required by the grep gate; a PR adding these tokens must either confirm the roster entries exist or include the § 1 edit in the same PR.

---

## § 3 · REPLACE — `background` token

| Field | Before | After |
|---|---|---|
| Identifier | `background` | `background` (preserved) |
| Value in `dark.ts` | `rgb(0,204,204)` (cyan placeholder inherited from CC) | `rgb(10,14,39)` (KOSMOS navy, `#0a0e27`) |

**Rationale**: ADR-006 A-9 explicitly flags `rgb(0,204,204)` as a "placeholder inherited from CC that must be replaced with the KOSMOS navy (`#0a0e27`) in the same PR that ports the onboarding splash." The identifier `background` is retained (no grep-gate conflict because `background` is a pre-existing allow-listed token). The gradient endpoint `#1a1040` is NOT a separate token — it is applied at LogoV2 rendering time.

---

## § 4 · PRESERVE set (62 identifiers)

Unchanged in both `ThemeToken` and `darkTheme`:

**Harness-state tokens** (7): `autoAccept`, `bashBorder`, `permission`, `permissionShimmer`, `planMode`, `ide`, `promptBorder`, `promptBorderShimmer`, `merged`, `professionalBlue`, `chromeYellow`, `fastMode`, `fastModeShimmer`.

**Semantic tokens** (10): `text`, `inverseText`, `inactive`, `inactiveShimmer`, `subtle`, `suggestion`, `remember`, `success`, `error`, `warning`, `warningShimmer`, `briefLabelYou`.

**Diff tokens** (6): `diffAdded`, `diffRemoved`, `diffAddedDimmed`, `diffRemovedDimmed`, `diffAddedWord`, `diffRemovedWord`.

**Subagent tokens** (8): `red_FOR_SUBAGENTS_ONLY`, `blue_FOR_SUBAGENTS_ONLY`, `green_FOR_SUBAGENTS_ONLY`, `yellow_FOR_SUBAGENTS_ONLY`, `purple_FOR_SUBAGENTS_ONLY`, `orange_FOR_SUBAGENTS_ONLY`, `pink_FOR_SUBAGENTS_ONLY`, `cyan_FOR_SUBAGENTS_ONLY`.

**Message-surface tokens** (6): `userMessageBackground`, `userMessageBackgroundHover`, `messageActionsBackground`, `selectionBg`, `bashMessageBackgroundColor`, `memoryBackgroundColor`.

**Rate-limit tokens** (2): `rate_limit_fill`, `rate_limit_empty`.

**Rainbow tokens** (14): `rainbow_red`, `rainbow_orange`, `rainbow_yellow`, `rainbow_green`, `rainbow_blue`, `rainbow_indigo`, `rainbow_violet`, `rainbow_red_shimmer`, `rainbow_orange_shimmer`, `rainbow_yellow_shimmer`, `rainbow_green_shimmer`, `rainbow_blue_shimmer`, `rainbow_indigo_shimmer`, `rainbow_violet_shimmer`.

**Background token** (1): `background` (value changes per § 3, identifier preserved).

**Total**: 62 identifiers preserved. Any preserve-set token whose value fails the new `#0a0e27` background contrast threshold gets its value raised per FR-011; those bumps are recorded in `contracts/contrast-measurements.md`.

---

## § 5 · Header-comment update

Both `tui/src/theme/tokens.ts` and `tui/src/theme/dark.ts` gain an additional header line per FR-008:

```typescript
// Source: .references/claude-code-sourcemap/restored-src/src/utils/theme.ts (Claude Code 2.1.88, research-use)
// KOSMOS 브랜드 토큰으로 리네이밍됨 (ADR-006 A-9)
```

The second line is literal Korean — acceptable under AGENTS.md "All source text in English. Only exception: Korean domain data" because the line is a brand-identity statement binding to the Korean domain (KOSMOS + ADR-006 A-9).

---

## § 6 · Enforcement

The Brand Guardian grep gate (`specs/034-tui-component-catalog/contracts/grep-gate-rules.md § 4`) runs on every PR that modifies `tui/src/theme/**`:

1. Parses the PR diff for newly added identifiers in `tokens.ts`.
2. For each added identifier, runs BAN-01 through BAN-07 regex checks.
3. For each `agentSatellite{MINISTRY}` identifier, verifies the `MinistryCode` suffix appears in `docs/design/brand-system.md § 1` ministry roster.
4. Exits non-zero on any violation; PR merge blocked.

This PR adds 10 identifiers (§ 2 ADD set). Expected grep-gate result: PASS — none of the 10 match any BAN regex; all 4 `agentSatellite*` MinistryCodes are roster-present.

---

## § 7 · Traceability

| Contract clause | Spec FR | Invariant | Test |
|---|---|---|---|
| § 1 DELETE set | FR-005 | I-17, I-18 | `tokens.compile.test.ts` asserts absence of 7 identifiers |
| § 2 ADD set | FR-006 | I-1, I-2, I-3, I-17 | `tokens.compile.test.ts` asserts presence of 10 identifiers |
| § 3 REPLACE background | FR-009 | I-5 | `dark.ts` value equality assertion |
| § 4 PRESERVE set | FR-007, FR-011 | — | `tokens.compile.test.ts` asserts preserve-set cardinality = 62 |
| § 5 Header comment | FR-008 | I-20 | grep assertion on file header |
| § 6 Enforcement | SC-011 | I-19 | Brand Guardian workflow outputs PASS |
