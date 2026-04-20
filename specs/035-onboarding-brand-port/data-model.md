# Phase 1 Data Model: Onboarding + Brand Port

**Feature**: Epic H #1302 — Onboarding + brand port (binds ADR-006 A-9)
**Branch**: `035-onboarding-brand-port`
**Date**: 2026-04-20
**Input**: [plan.md § Phase 1](./plan.md#phase-1--design--contracts), [spec.md § Key Entities](./spec.md), [research.md](./research.md)

**Scope**: This model is **contract-level**, not implementation-level. It enumerates every entity, its fields, relationships, invariants, and state transitions — in a form that both the TypeScript TUI layer and the Python backend layer can consume without ambiguity. Pydantic v2 class stubs are declarative; the actual class bodies land in Phase 3 implementation per Constitution Principle III. Zod schemas for the TUI side mirror the Pydantic contracts field-for-field.

---

## Entity 1 — `BrandPalette`

**Purpose**: Closed mapping from `(MetaphorRole × Variant?)` to hex value. Source of truth for `tui/src/theme/dark.ts` and `docs/design/brand-system.md § 4`.

**Representation**: Markdown table in `docs/design/brand-system.md § 4` + deterministic TypeScript literal in `tui/src/theme/dark.ts`. No Pydantic / Zod schema at runtime — the palette is a compile-time constant.

**Fields**:

| Field | Type | Required | Notes |
|---|---|---|---|
| `tokenName` | `string` conforming to `MetaphorRole Variant?` per `docs/design/brand-system.md § 2` BNF | yes | Primary key. camelCase `MetaphorRole` + TitleCase optional `Variant`. |
| `primaryHex` | `string` matching `/^#[0-9a-f]{6}$/` | yes | Primary value. Lowercase hex. Must appear in `assets/kosmos-logo.svg` palette. |
| `shimmerHex` | `string | null` | no | Present iff a `Shimmer` variant ships for this token. |
| `ministryBinding` | `MinistryCode | null` | no | Non-null iff `tokenName` starts with `agentSatellite`. Values: `Koroad`, `Kma`, `Hira`, `Nmc`. |
| `measuredContrastRatio` | `float | null` | no | Measured against `backgroundHex` via WCAG formula. Two-decimal rounding. |
| `measuredContrastAgainst` | `string | null` | no | Hex value the contrast was measured against (usually `#0a0e27`). |
| `role` | `"structural" | "ministry" | "harness-state" | "semantic"` | yes | Category per brand-system.md § 2 Grammar. |

**Invariants**:

- **I-1**: `tokenName` MUST match the `docs/design/brand-system.md § 2` BNF. Failing tokens are rejected by the Brand Guardian grep gate.
- **I-2**: `primaryHex` lowercase (`#a78bfa`, not `#A78BFA`). Consistent with existing SVG source files.
- **I-3**: If `tokenName` starts with `agentSatellite`, `ministryBinding` MUST be set and MUST match the `MinistryCode` suffix (`agentSatelliteKoroad` ↔ `Koroad`).
- **I-4**: `measuredContrastRatio` ≥ 4.5 for any token rendered as body text in any component (FR-003); ≥ 3.0 for non-text UI chrome.
- **I-5**: `primaryHex` MUST be drawn from the authoritative 16-hex palette in `assets/kosmos-logo.svg` OR inherit from a preserved semantic slot in the pre-edit `dark.ts`.

**Relationships**:

- Consumed by every `LogoV2RewriteComponent` via the `ThemeToken` lookup in `useTheme()`.
- Referenced by `docs/design/brand-system.md § 4 Palette values`.
- Validated by `scripts/compute-contrast.mjs` against WCAG formula (per research R-3).

---

## Entity 2 — `OnboardingStep`

**Purpose**: Registry entry for one step in the 3-step citizen onboarding state machine (splash → PIPA consent → ministry-scope → done).

**Representation**: TypeScript const object in `tui/src/components/onboarding/Onboarding.tsx`. Mirrors CC `Onboarding.tsx` L22–26 shape.

**Fields**:

| Field | Type | Required | Notes |
|---|---|---|---|
| `stepId` | `"splash" | "pipa-consent" | "ministry-scope-ack" | "done"` | yes | Primary key; ordering fixed. |
| `component` | `React.FC<{onAdvance: () => void; onExit: () => void}>` | yes | Ink functional component. |
| `advanceCondition` | `() => boolean` | yes | Called on Enter; false suppresses advance (e.g. pending toggle selection). |
| `skipCondition` | `(memdirState: MemdirUserState) => boolean` | yes | Evaluated at session start only, never mid-flow. True ⇒ skip on return visit. |
| `exitSideEffect` | `"write-consent-record" | "write-scope-record" | "none"` | yes | What the advance action persists. |

**Invariants**:

- **I-6**: `stepId` ordering is fixed at `splash (0) → pipa-consent (1) → ministry-scope-ack (2) → done (3)`; no registry may re-order.
- **I-7**: `skipCondition` may evaluate **only** `memdirState` — never `Date.now()`, `process.env`, or network state. This preserves audit determinism.
- **I-8**: `exitSideEffect` writes are synchronous + `fsync`ed before advancement (see `PIPAConsentRecord` I-10 and `MinistryScopeAcknowledgment` I-13).

**State transitions**:

```
  ┌──────────┐  Enter   ┌──────────────┐  Enter   ┌──────────────────────┐  Enter
  │  splash  │ ───────▶ │ pipa-consent │ ───────▶ │ ministry-scope-ack   │ ───────▶ done
  └────┬─────┘          └──────┬───────┘          └──────────┬───────────┘
       │ Escape                │ Escape                      │ Escape
       └───────────────────────┴─────────────────────────────┘
                                       ▼
                                 exit(0) — no record written
```

Session-start decision (from research R-6):

```
read latest PIPAConsentRecord from memdir → match CONSENT_VERSION?
    ├─ no  → render full flow from `splash`
    └─ yes → read latest MinistryScopeAcknowledgment → match SCOPE_VERSION?
                ├─ no  → render from `ministry-scope-ack`, skip `pipa-consent`
                └─ yes → render `splash` only, 3 s budget, advance to `done` on keypress
```

**Relationships**:

- Consumes `MemdirUserState` (Spec 027 infrastructure).
- Writes `PIPAConsentRecord` + `MinistryScopeAcknowledgment`.

---

## Entity 3 — `PIPAConsentRecord`

**Purpose**: Append-only memdir USER-tier record capturing one PIPA consent decision.

**Representation**: Pydantic v2 `frozen=True` model on Python side; Zod discriminated union on TypeScript side. Serialised as JSON at `~/.kosmos/memdir/user/consent/<timestamp>-<session_id>.json`.

**Fields**:

| Field | Type | Required | Notes |
|---|---|---|---|
| `consent_version` | `str` matching `/^v\d+$/` | yes | `v1`, `v2`, ...; bumps when consent copy changes. |
| `timestamp` | `datetime` (UTC, ISO-8601 with `Z`) | yes | `datetime.now(tz=UTC)` at write. |
| `aal_gate` | `AuthenticatorAssuranceLevel` (from Spec 033) | yes | Snapshot at consent time; `AAL1` default. |
| `session_id` | `UUID` (UUIDv7 per Spec 032 precedent) | yes | Timestamp-prepended UUIDv7. |
| `citizen_confirmed` | `bool` | yes | `True` on accept; record NOT written on decline (see I-11). |
| `schema_version` | `Literal["1"]` | yes | Immutable at `"1"`; bump via ADR amendment only. |

**Invariants**:

- **I-9**: Immutable after write — enforced by Pydantic v2 `model_config = ConfigDict(frozen=True)`.
- **I-10**: Atomic write: `open(tmp_path, "w") → json.dump → fsync → os.rename(tmp_path, final_path)`. Any partial write remains invisible to reader.
- **I-11**: Decline path writes **no** record. This is intentional — a decline is an opt-out, not a recordable assent.
- **I-12**: `consent_version` monotonically non-decreasing per citizen — reader rejects any record whose `consent_version` parses as numerically less than a prior record's.

**Relationships**:

- Read by `OnboardingStep.skipCondition` at session start.
- Written by `OnboardingStep[pipa-consent].exitSideEffect`.
- Inspected by the permission pipeline Step 5 ("Ministry terms-of-use — has the citizen consented") per `docs/vision.md § Permission pipeline`.

**Example** (reference only, not authoritative):

```json
{
  "consent_version": "v1",
  "timestamp": "2026-04-20T14:32:05Z",
  "aal_gate": "AAL1",
  "session_id": "018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60",
  "citizen_confirmed": true,
  "schema_version": "1"
}
```

---

## Entity 4 — `MinistryScopeAcknowledgment`

**Purpose**: Memdir USER-tier record capturing the citizen's per-ministry opt-in decisions.

**Representation**: Pydantic v2 `frozen=True` model on Python side; Zod schema on TypeScript side. Serialised as JSON at `~/.kosmos/memdir/user/ministry-scope/<timestamp>-<session_id>.json`.

**Fields**:

| Field | Type | Required | Notes |
|---|---|---|---|
| `scope_version` | `str` matching `/^v\d+$/` | yes | Bumps when ministry roster or description text changes. |
| `timestamp` | `datetime` (UTC, ISO-8601 `Z`) | yes | Single timestamp covering all 4 ministry decisions. |
| `session_id` | `UUID` (UUIDv7) | yes | Same session as the preceding `PIPAConsentRecord`. |
| `ministries` | `frozenset[MinistryOptIn]` | yes | Exactly 4 entries (FR-015). See `MinistryOptIn` below. |
| `schema_version` | `Literal["1"]` | yes | Immutable. |

**Nested value — `MinistryOptIn`**:

| Field | Type | Required | Notes |
|---|---|---|---|
| `ministry_code` | `Literal["KOROAD", "KMA", "HIRA", "NMC"]` | yes | Phase 1 seed set (FR-015). |
| `opt_in` | `bool` | yes | `True` = tool calls against this ministry are permitted. |

**Invariants**:

- **I-13**: Exactly 4 `MinistryOptIn` entries, one per Phase 1 ministry. Missing or extra entries fail Pydantic validation.
- **I-14**: `frozenset` membership — duplicate ministry codes are impossible at model level.
- **I-15**: Atomic write (same pattern as I-10).
- **I-16**: `session_id` MUST match the PIPAConsentRecord written in the same onboarding session.

**Relationships**:

- Read by `MainToolRouter.resolve(tool_id, params)` per the contract in `contracts/memdir-ministry-scope-schema.md`.
- Written by `OnboardingStep[ministry-scope-ack].exitSideEffect`.

**Example**:

```json
{
  "scope_version": "v1",
  "timestamp": "2026-04-20T14:33:17Z",
  "session_id": "018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60",
  "ministries": [
    {"ministry_code": "KOROAD", "opt_in": true},
    {"ministry_code": "KMA", "opt_in": true},
    {"ministry_code": "HIRA", "opt_in": false},
    {"ministry_code": "NMC", "opt_in": true}
  ],
  "schema_version": "1"
}
```

---

## Entity 5 — `KosmosThemeToken`

**Purpose**: TypeScript type alias exported by `tui/src/theme/tokens.ts`; closed union of KOSMOS metaphor tokens + retained semantic slots.

**Representation**: TypeScript `type` alias with `string` field values. No runtime validation — the contract is compile-time only.

**Field set (DELETE)**: 7 identifiers removed from `ThemeToken` per FR-005.

```
claude, claudeShimmer,
claudeBlue_FOR_SYSTEM_SPINNER, claudeBlueShimmer_FOR_SYSTEM_SPINNER,
clawd_body, clawd_background,
briefLabelClaude
```

**Field set (ADD)**: 10 identifiers added per FR-006.

```
kosmosCore, kosmosCoreShimmer,
orbitalRing, orbitalRingShimmer,
wordmark, subtitle,
agentSatelliteKoroad, agentSatelliteKma,
agentSatelliteHira, agentSatelliteNmc
```

**Field set (PRESERVE)**: All 62 identifiers listed in FR-007 remain unchanged.

**Invariants**:

- **I-17**: Zero intersection between DELETE set and ADD set (enforced by unique-name property of TypeScript types).
- **I-18**: The type surface compiles only if every consumer site has been updated to use the new identifier — a consumer still referencing `claude` fails at compile time.
- **I-19**: Every token name passes the Brand Guardian grep gate BAN-01 through BAN-07 (see R-1).
- **I-20**: Header comment in `tokens.ts` AND `dark.ts` includes the two lines required by FR-008 (upstream source + "KOSMOS 브랜드 토큰으로 리네이밍됨 (ADR-006 A-9)").

**Relationships**:

- Concretised by `darkTheme: ThemeToken` in `dark.ts` (the type's canonical value instance).
- Referenced by `useTheme()` in every KOSMOS TUI component.

---

## Entity 6 — `LogoV2RewriteComponent`

**Purpose**: Materialised catalog row for each of the 9 components in the LogoV2 / Onboarding / FastIcon REWRITE family owned by Epic H.

**Representation**: Row in `contracts/logov2-rewrite-visual-specs.md` + corresponding `.tsx` file under `tui/src/components/onboarding/LogoV2/` or `tui/src/components/chrome/`. No runtime model.

**Fields**:

| Field | Type | Required | Notes |
|---|---|---|---|
| `ccSourcePath` | `str` | yes | Path under `.references/claude-code-sourcemap/restored-src/src/components/` @ `a8a678c`. |
| `kosmosTargetPath` | `str` | yes | Path under `tui/src/components/`. |
| `verdict` | `"PORT" | "REWRITE"` | yes | 1 PORT (FeedColumn) + 8 REWRITE. |
| `accessibilityGateAnchor` | `"[ag-logov2]" | "[ag-onboarding]" | "[ag-logo-wordmark]"` | yes | Anchor in `docs/tui/accessibility-gate.md § 3`. |
| `tokenReferences` | `list[ThemeToken-key]` | yes | Which tokens `useTheme()` reads. |
| `reducedMotionFallback` | `str` (prose description) | yes | What renders when `useReducedMotion() === true`. |
| `koreanLabel` | `str | null` | no | Primary Korean label if the component renders text content. |
| `layoutBreakpoints` | `list[int]` | yes | Column thresholds for layout changes (e.g. `[50, 80]`). |

**The 9 rows**:

| # | ccSourcePath | kosmosTargetPath | verdict | anchor | primary tokens |
|---|---|---|---|---|---|
| 1 | `LogoV2/AnimatedAsterisk.tsx` | `onboarding/LogoV2/AnimatedAsterisk.tsx` | REWRITE | `[ag-logov2]` | `kosmosCore`, `kosmosCoreShimmer` |
| 2 | `LogoV2/CondensedLogo.tsx` | `onboarding/LogoV2/CondensedLogo.tsx` | REWRITE | `[ag-logov2]` | `wordmark`, `subtitle` |
| 3 | `LogoV2/Feed.tsx` | `onboarding/LogoV2/Feed.tsx` | REWRITE | `[ag-logov2]` | `text`, `subtle`, `agentSatellite*` |
| 4 | `LogoV2/FeedColumn.tsx` | `onboarding/LogoV2/FeedColumn.tsx` | PORT | `[ag-logov2]` | `subtle`, `text` |
| 5 | `LogoV2/feedConfigs.tsx` | `onboarding/LogoV2/feedConfigs.tsx` | REWRITE | `[ag-logov2]` | `agentSatellite*` |
| 6 | `LogoV2/LogoV2.tsx` | `onboarding/LogoV2/LogoV2.tsx` | REWRITE | `[ag-logov2]` | all 10 new tokens |
| 7 | `LogoV2/WelcomeV2.tsx` | `onboarding/LogoV2/WelcomeV2.tsx` | REWRITE | `[ag-logov2]` | `wordmark`, `subtitle`, `kosmosCore` |
| 8 | `FastIcon.tsx` | `chrome/KosmosCoreIcon.tsx` | REWRITE | `[ag-logo-wordmark]` | `kosmosCore` |
| 9 | `Onboarding.tsx` | `onboarding/Onboarding.tsx` | REWRITE | `[ag-onboarding]` | `wordmark`, `subtitle`, `kosmosCore`, `orbitalRing` |

**Invariants**:

- **I-21**: Every row has a corresponding accessibility-gate row in `docs/tui/accessibility-gate.md § 3` at rows 31 / 32 / 33 / 35 / 36 / 37 / 45 / 154 / 156.
- **I-22**: No row imports `Clawd`, `AnimatedClawd`, `GuestPassesUpsell`, `EmergencyTip`, `VoiceModeNotice`, `Opus1mMergeNotice`, `ChannelsNotice`, or `OverageCreditUpsell`. Compile-time guarantee.
- **I-23**: Every row honours `useReducedMotion()` (FR-024) and renders plain UTF-8 text (FR-025).

**Relationships**:

- Consumes `BrandPalette` via `useTheme()`.
- Referenced by `OnboardingStep[splash].component` (LogoV2 is the splash's root).
- Measured by `contrast-measurements.md`.

---

## Cross-entity invariants

- **X-1 — Version coherence**: when `PIPAConsentRecord.consent_version` or `MinistryScopeAcknowledgment.scope_version` bumps, the corresponding `OnboardingStep.skipCondition` begins returning `false`, forcing a re-prompt.
- **X-2 — Session binding**: a PIPAConsentRecord and its following MinistryScopeAcknowledgment share the same `session_id` (enforced by `OnboardingStep` writing both within the same flow).
- **X-3 — Router refusal**: `MainToolRouter.resolve()` reads the latest `MinistryScopeAcknowledgment`; any ministry with `opt_in = false` triggers the SC-009 pre-network refusal with a Korean citizen-facing message.
- **X-4 — Palette → component closure**: every `LogoV2RewriteComponent.tokenReferences` entry is a member of the DELETE-stripped / ADD-augmented `KosmosThemeToken` surface. No component references a token that does not exist.

---

## Summary

| Entity | Representation | Owner | Mutability |
|---|---|---|---|
| `BrandPalette` | MD table + TS literal | `docs/design/brand-system.md § 4` | compile-time constant |
| `OnboardingStep` | TS const | `tui/src/components/onboarding/Onboarding.tsx` | compile-time constant |
| `PIPAConsentRecord` | Pydantic v2 + Zod mirror | `src/kosmos/memdir/user_consent.py` | immutable (frozen=True) |
| `MinistryScopeAcknowledgment` | Pydantic v2 + Zod mirror | `src/kosmos/memdir/ministry_scope.py` | immutable (frozen=True) |
| `KosmosThemeToken` | TS type alias | `tui/src/theme/tokens.ts` | compile-time contract |
| `LogoV2RewriteComponent` | MD catalog + .tsx files | `contracts/logov2-rewrite-visual-specs.md` | source-controlled |

6 entities, 23 numbered invariants (I-1 … I-23), 4 cross-entity invariants (X-1 … X-4), 0 unresolved `NEEDS CLARIFICATION` markers.

**Next**: Phase 1 contracts — six files under `contracts/`.
