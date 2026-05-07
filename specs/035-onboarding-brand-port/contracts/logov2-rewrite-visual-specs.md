# Contract: LogoV2 REWRITE visual specs

**Feature**: Epic H #1302
**Phase**: 1
**Catalog reference**: `docs/tui/component-catalog.md` rows 31 / 32 / 33 / 35 / 36 / 37 / 45 / 154 / 156
**Accessibility reference**: `docs/tui/accessibility-gate.md` rows 31–37, 154, 156
**CC reference**: `.references/claude-code-sourcemap/restored-src/src/components/LogoV2/*` + `FastIcon.tsx` + `Onboarding.tsx` @ `a8a678c`

Per-component visual + behavioural spec for the 9 Epic H-owned REWRITE / PORT rows.

---

## § 1 · `AnimatedAsterisk.tsx` (REWRITE, row 31)

**Verdict**: REWRITE
**KOSAX target**: `tui/src/components/onboarding/LogoV2/AnimatedAsterisk.tsx`
**Tokens consumed**: `kosaxCore`, `kosaxCoreShimmer`
**Accessibility anchor**: `[ag-logov2]`

### Input props

```typescript
type Props = {
  width?: number        // default 5 (cells); width must be odd
  height?: number       // default 3 (cells)
  prefersReducedMotion?: boolean  // defaults to useReducedMotion()
}
```

### Visual

An asterisk glyph (`*`) rendered in the `kosaxCore` colour, with a shimmer-cycle animation that cycles through `kosaxCoreShimmer` → `kosaxCore` → `kosaxCoreShimmer` at 6 fps (same frame budget as CC `useShimmerAnimation.ts`).

### Reduced-motion fallback

Static `*` in `kosaxCore` colour; no shimmer; no re-render triggered by the animation hook.

### CC content removed

- Teardrop-asterisk glyph (CC-specific design) — replaced with a standard `*` (U+002A).
- `chromeYellow` colour binding — replaced with `kosaxCore`.

---

## § 2 · `CondensedLogo.tsx` (REWRITE, row 35)

**Verdict**: REWRITE
**KOSAX target**: `tui/src/components/onboarding/LogoV2/CondensedLogo.tsx`
**Tokens consumed**: `wordmark`, `subtitle`, `kosaxCore`, `background`
**Accessibility anchor**: `[ag-logov2]`

### Input props

```typescript
type Props = {
  model?: string        // e.g. "K-EXAONE"
  effort?: string       // e.g. "normal"
  coordinatorMode?: string  // from Spec 033 PermissionMode
}
```

### Visual

One-line header: `[kosaxCore] KOSAX — <model> · <effort> · <coordinatorMode>` rendered in the `wordmark` token on the `background` token.

### Reduced-motion fallback

Same rendering (CondensedLogo is already static).

### CC content removed

- "Claude Code" wordmark → "KOSAX".
- `Clawd` poses, GuestPassesUpsell references, referral API strings — all removed.

---

## § 3 · `Feed.tsx` (REWRITE, row 37)

**Verdict**: REWRITE
**KOSAX target**: `tui/src/components/onboarding/LogoV2/Feed.tsx`
**Tokens consumed**: `text`, `subtle`, `agentSatelliteKoroad`, `agentSatelliteKma`, `agentSatelliteHira`, `agentSatelliteNmc`
**Accessibility anchor**: `[ag-logov2]`

### Input props

```typescript
type Props = {
  sessionHistory: KosaxSession[]     // from memdir Session tier
  ministryStatus: MinistryStatus[]    // from Spec 022 adapter registry
}
```

### Visual

Two-column feed:

- **Left column — "최근 세션"**: up to 5 recent KOSAX session entries (query summary + timestamp). Each entry styled in `text` token; timestamp in `subtle`.
- **Right column — "부처 상태"**: 4 ministry-status rows (KOROAD / KMA / HIRA / NMC). Ministry name in `agentSatellite{MINISTRY}` accent; availability indicator (●/○) next to name.

### Reduced-motion fallback

Same rendering (no animation on Feed).

### CC content removed

- `createRecentActivityFeed`, `createWhatsNewFeed`, `createProjectOnboardingFeed`, `createGuestPassesFeed`, `createOverageCreditFeed` — all deleted.

---

## § 4 · `FeedColumn.tsx` (PORT, row 38)

**Verdict**: PORT (verbatim, token-only swap)
**KOSAX target**: `tui/src/components/onboarding/LogoV2/FeedColumn.tsx`
**Tokens consumed**: `text`, `subtle` (semantic slots — no rename needed)
**Accessibility anchor**: `[ag-logov2]`

### Input props

Same as CC — generic feed column primitive.

### CC content removed

None structurally; the PORT only renames imported token identifiers to their KOSAX equivalents (no occurrences of `claude*` in the original file per inspection).

---

## § 5 · `feedConfigs.tsx` (REWRITE, row 39)

**Verdict**: REWRITE
**KOSAX target**: `tui/src/components/onboarding/LogoV2/feedConfigs.tsx`
**Tokens consumed**: `agentSatellite*`, `text`, `subtle`

### Exports

```typescript
export function createKosaxSessionHistoryFeed(sessionHistory: KosaxSession[]): FeedConfig
export function createMinistryAvailabilityFeed(status: MinistryStatus[]): FeedConfig
```

### CC content removed

CC's 5 feed factories are entirely deleted. Two KOSAX factories replace them.

---

## § 6 · `LogoV2.tsx` (REWRITE, row 41)

**Verdict**: REWRITE
**KOSAX target**: `tui/src/components/onboarding/LogoV2/LogoV2.tsx`
**Tokens consumed**: all 10 new metaphor tokens + `background`
**Accessibility anchor**: `[ag-logov2]`

### Input props

```typescript
type Props = {
  mode?: "full" | "condensed"  // defaults via getLayoutMode()
}
```

### Visual composition (full mode, ≥ 80 columns)

```
           ┌─────────────────────────────────────────────┐
           │                                             │
           │              ╭─ orbitalRing ─╮              │
           │             /                 \             │
           │            │      [*]kosax   │             │
           │             \     Core       /              │
           │              ╰───────────────╯              │
           │                                             │
           │                K O S M O S                  │  ← wordmark
           │    KOREAN PUBLIC SERVICE MULTI-AGENT OS     │  ← subtitle
           │                                             │
           │   ●KOROAD  ●KMA  ●HIRA  ●NMC                │  ← 4 satellite nodes
           │                                             │
           │   최근 세션           부처 상태            │  ← Feed
           │   ...                  ...                  │
           │                                             │
           └─────────────────────────────────────────────┘
```

### Visual composition (condensed mode, < 80 columns)

Single-line header via `CondensedLogo.tsx`; ministry row + feed hidden.

### Visual composition (< 50 columns fallback)

Single-line text: `KOSAX — 한국 공공서비스 대화창`.

### Reduced-motion fallback

- `AnimatedAsterisk` static.
- `orbitalRing` rendered as static gradient (no rotation).
- Otherwise identical layout.

### CC content removed

- All imports: `Clawd`, `AnimatedClawd`, `ChannelsNotice`, `GuestPassesUpsell`, `EmergencyTip`, `VoiceModeNotice`, `Opus1mMergeNotice`, `OverageCreditUpsell`.
- CC-specific feature() gates for channels / voice mode.

---

## § 7 · `WelcomeV2.tsx` (REWRITE, row 45)

**Verdict**: REWRITE
**KOSAX target**: `tui/src/components/onboarding/LogoV2/WelcomeV2.tsx`
**Tokens consumed**: `wordmark`, `subtitle`, `kosaxCore`

### Visual

```
  KOSAX에 오신 것을 환영합니다  vN.N.N
  ────────────────────────────
          *  *  *
         *  ●  *
          *  *  *
```

Citizen welcome screen — kosaxCore asterisk cluster (static or shimmering per reduced-motion), with the Korean welcome message. Apple-Terminal-specific ASCII art branch from CC is deleted.

### CC content removed

- "Welcome to Claude Code" → "KOSAX에 오신 것을 환영합니다".
- Apple-Terminal special-case ASCII poses → replaced with the kosaxCore cluster.
- Theme-specific light/dark branching: retained only the dark branch (per Phase 1 scope).

---

## § 8 · `KosaxCoreIcon.tsx` (REWRITE from `FastIcon.tsx`, row 162)

**Verdict**: REWRITE + file rename
**CC source**: `FastIcon.tsx`
**KOSAX target**: `tui/src/components/chrome/KosaxCoreIcon.tsx`
**Tokens consumed**: `kosaxCore`, `kosaxCoreShimmer`
**Accessibility anchor**: `[ag-logo-wordmark]`

### Input props

```typescript
type Props = {
  shimmering?: boolean  // defaults to false
}
```

### Visual

Single `*` (U+002A) glyph in `kosaxCore` token; shimmers to `kosaxCoreShimmer` when `shimmering === true` AND `useReducedMotion() === false`.

### Consumers to update

Every import of `FastIcon` in the existing TUI is updated to `KosaxCoreIcon` as part of this REWRITE.

### CC content removed

- `chromeYellow` lightning-bolt glyph → replaced with `*`.
- CC fast-mode branding — entirely removed.

---

## § 9 · `Onboarding.tsx` (REWRITE, row 156/165)

**Verdict**: REWRITE
**KOSAX target**: `tui/src/components/onboarding/Onboarding.tsx`
**Tokens consumed**: indirect (composes child components)
**Accessibility anchor**: `[ag-onboarding]`

### Spec

Implements the 3-step state machine per `contracts/onboarding-step-registry.md § 1–§ 3`. Composes `LogoV2.tsx` + `PIPAConsentStep.tsx` + `MinistryScopeStep.tsx`.

### CC content removed

- CC step registry (`preflight`, `theme`, `oauth`, `api-key`, `security`, `terminal-setup`) entirely replaced.
- OAuth flow (`ConsoleOAuthFlow.tsx`), ApproveApiKey, PreflightStep, ThemePicker — NOT imported here (ThemePicker deferred to Epic K).
- `logEvent('tengu_*')` analytics — replaced with KOSAX OTEL span emission per Spec 021 (use `kosax.onboarding.step` span name).

---

## § 10 · Traceability matrix

| # | CC source | KOSAX target | Verdict | a11y anchor | FR | Test |
|---|---|---|---|---|---|---|
| 1 | `LogoV2/AnimatedAsterisk.tsx` | `onboarding/LogoV2/AnimatedAsterisk.tsx` | REWRITE | `[ag-logov2]` r31 | FR-018 | `AnimatedAsterisk.snap.test.tsx` |
| 2 | `LogoV2/CondensedLogo.tsx` | `onboarding/LogoV2/CondensedLogo.tsx` | REWRITE | `[ag-logov2]` r32 | FR-019 | `CondensedLogo.snap.test.tsx` |
| 3 | `LogoV2/Feed.tsx` | `onboarding/LogoV2/Feed.tsx` | REWRITE | `[ag-logov2]` r33 | FR-022 | `Feed.snap.test.tsx` |
| 4 | `LogoV2/FeedColumn.tsx` | `onboarding/LogoV2/FeedColumn.tsx` | PORT | `[ag-logov2]` r34 | FR-021 | `FeedColumn.snap.test.tsx` |
| 5 | `LogoV2/feedConfigs.tsx` | `onboarding/LogoV2/feedConfigs.tsx` | REWRITE | `[ag-logov2]` r35 | FR-022 | `feedConfigs.test.tsx` |
| 6 | `LogoV2/LogoV2.tsx` | `onboarding/LogoV2/LogoV2.tsx` | REWRITE | `[ag-logov2]` r36 | FR-017 | `LogoV2.snap.test.tsx` (3 width breakpoints + reduced-motion) |
| 7 | `LogoV2/WelcomeV2.tsx` | `onboarding/LogoV2/WelcomeV2.tsx` | REWRITE | `[ag-logov2]` r37 | FR-020 | `WelcomeV2.snap.test.tsx` |
| 8 | `FastIcon.tsx` | `chrome/KosaxCoreIcon.tsx` | REWRITE | `[ag-logo-wordmark]` r154 | FR-023 | `KosaxCoreIcon.snap.test.tsx` |
| 9 | `Onboarding.tsx` | `onboarding/Onboarding.tsx` | REWRITE | `[ag-onboarding]` r156 | FR-012 | `Onboarding.snap.test.tsx` |
