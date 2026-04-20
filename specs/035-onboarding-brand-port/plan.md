# Implementation Plan: Onboarding + Brand Port

**Branch**: `035-onboarding-brand-port` | **Date**: 2026-04-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/035-onboarding-brand-port/spec.md`
**Epic**: [#1302 — Onboarding + brand port (binds ADR-006 A-9)](https://github.com/umyunsang/openKOSMOS/issues/1302)

**Note**: This plan fills the `/speckit-plan` template for Epic H. Phase 0 consults `docs/vision.md § Reference materials` (Constitution Principle I — Reference-Driven Development) and every design decision is anchored to a concrete reference cited inline.

## Summary

Deliver the three-step KOSMOS citizen onboarding flow (**splash → PIPA consent → ministry-scope acknowledgment**) plus the KOSMOS-metaphor token contract (`tokens.ts` type surface + `dark.ts` palette map) plus the eight LogoV2 / FastIcon REWRITE visual specs that bring the ADR-006 A-9 orbital-ring splash to life on the Ink+React+Bun TUI (ADR-003/004) without introducing any runtime dependency. The Python backend persists PIPA consent + ministry-scope acknowledgments to the memdir USER tier (Spec 027 infrastructure) via a new append-only JSON record schema, and the main-tool router (Spec 022) refuses tool calls against declined ministries at the pre-network boundary. Technical approach: TypeScript REWRITE ported directly from `.references/claude-code-sourcemap/restored-src/src/components/{Onboarding,LogoV2/*}.tsx` with developer-domain content replaced by citizen-domain content per ADR-006 A-9; no inventive UI framework work. Palette values extracted from `assets/kosmos-logo.svg` + `assets/kosmos-banner-dark.svg`. Contrast measurements published in `docs/design/contrast-measurements.md` (new).

## Technical Context

**Language/Version**: TypeScript 5.6+ (TUI layer, Bun v1.2.x runtime — existing Spec 287 stack); Python 3.12+ (backend memdir + main-tool router — existing stack from Specs 022 / 027).
**Primary Dependencies**: `ink` (React for CLIs), `react`, `bun:test`, Spec 287-introduced Ink stack (unchanged). Python: `pydantic >= 2.13` (consent-record schema), stdlib `pathlib` / `json` / `datetime`. **Zero new runtime dependencies** (AGENTS.md hard rule; SC-008 of Spec 034).
**Storage**: Memdir USER tier at `~/.kosmos/memdir/user/consent/` (Spec 027 infrastructure). Append-only JSON records per consent event. `~/.kosmos/memdir/user/ministry-scope/` for ministry opt-in state. No database, no external queue. POSIX filesystem only.
**Testing**: `bun test` (Ink snapshot + interaction tests — existing Spec 287 harness); `uv run pytest` for memdir schema + main-tool refusal tests. Visual regression via `ink-testing-library` (installed under Spec 287).
**Target Platform**: terminal emulator on macOS (Terminal.app, iTerm2), Linux (xterm, Alacritty), Windows Terminal (future). ≥ 80 columns canonical; ≥ 50 columns degrades; < 50 columns renders a single-line fallback.
**Project Type**: TUI component library + Python contract schema (KOSMOS is a two-process system — Python backend ↔ Ink TUI over stdio JSONL per Spec 032).
**Performance Goals**: first-frame splash render < 250 ms on cold launch (Ink equivalent of CC `LogoV2` first-paint budget); full happy-path onboarding (splash + consent + scope) ≤ 90 s (SC-002); returning-citizen fast-path ≤ 3 s (SC-012); ministry-refusal latency < 100 ms (SC-009). Shimmer animation frame budget ≤ 60 fps equivalent (CC `useShimmerAnimation.ts` unchanged).
**Constraints**: palette pairs ≥ 4.5 : 1 (body text) / ≥ 3 : 1 (non-text) per `docs/tui/accessibility-gate.md § 7` (non-negotiable); no new runtime dependency; no SVG rendering in TUI; Korean output only for citizen-facing labels; English-only source text (AGENTS.md); IME-safe on every keyboard affordance (Spec 287 `useKoreanIME()`).
**Scale/Scope**: ≈ 8 REWRITE files + 1 PORT file (LogoV2 family) + 3 new onboarding step components + 2 theme files (`tokens.ts`, `dark.ts`) + 6 `docs/design/brand-system.md` sections (§ 3/§ 4/§ 5/§ 6/§ 7/§ 9) + 1 new `docs/design/contrast-measurements.md` + 2 memdir schema contracts (Python side) + 1 main-tool refusal path. Affected citizen surface: entire first-launch UX + every subsequent session's splash.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Verdict | Evidence |
|---|---|---|
| I. Reference-Driven Development | **PASS** | Every FR in spec.md cites a concrete reference: ADR-006 A-9 (palette anchors, step sequence), brand-system.md § 1–§ 2 (token grammar), accessibility-gate.md § 7 (contrast constraint), component-catalog Epic H rows (REWRITE verdicts), and `.references/claude-code-sourcemap/restored-src/src/components/{Onboarding,LogoV2/*}.tsx` (CC source). Phase 0 below maps each design decision to its reference. No decision invented outside of `docs/vision.md § Reference materials`. |
| II. Fail-Closed Security | **PASS** | PIPA consent defaults to non-consent (declining exits session with no ministry call possible, FR-014). Ministry opt-in defaults to off — every ministry must be explicitly acknowledged before any tool call to it is honoured (FR-016 + SC-009). No "YOLO" or "skip consent" mode. Consent bump forces re-confirm. |
| III. Pydantic v2 Strict Typing | **PASS (scoped)** | Python-side memdir schemas (PIPAConsentRecord, MinistryScopeAcknowledgment) use Pydantic v2 `frozen=True` models with no `Any`. TUI side is TypeScript — Pydantic N/A — but TUI uses Zod discriminated unions for IPC frames (consistent with Spec 032 pattern). All JSON records validate at write-time and read-time. |
| IV. Government API Compliance | **PASS (N/A)** | This spec does not call any `data.go.kr` endpoint. It enforces the acknowledgment gate that subsequent ministry-call specs consume. No live-API test is introduced. Existing `data.go.kr` quota / `rate_limit_per_minute` contracts inherited from Spec 022 remain untouched. |
| V. Policy Alignment | **PASS** | Principle 8 (single conversational window) satisfied structurally by the splash rendering "one KOSMOS" above four ministry satellite nodes. Principle 9 (Open API and OpenMCP for public service integration) satisfied by the explicit ministry-enumeration step. Principle 5 (consent-based data access) satisfied by the PIPA consent record preceding every ministry call. Public AI Impact Assessment bias / transparency requirements served by the pre-network refusal path (SC-009). |
| VI. Deferred Work Accountability | **PASS** | spec.md § Scope Boundaries contains 4 Out-of-Scope (Permanent) items and 10 Deferred-to-Future-Work rows with target Epic / Phase for each. Phase 0 Research below re-validates these per the `/speckit-plan` template. No free-text "future phase" prose without a matching table row. |

**Initial Gate result**: **PASS** — all six principles green. Proceed to Phase 0 Research. No violations require `Complexity Tracking` entries.

## Project Structure

### Documentation (this feature)

```text
specs/035-onboarding-brand-port/
├── plan.md                                # This file (/speckit-plan output)
├── spec.md                                # Feature spec (/speckit-specify output)
├── research.md                            # Phase 0 output — 10 reference-mapped decisions
├── data-model.md                          # Phase 1 — 6 entities (BrandPalette, OnboardingStep, ...)
├── contracts/
│   ├── brand-token-surface.md             # Phase 1 — ThemeToken delete/add set + hex binding
│   ├── onboarding-step-registry.md        # Phase 1 — 3-step state machine + skip logic
│   ├── memdir-consent-schema.md           # Phase 1 — PIPAConsentRecord JSON schema
│   ├── memdir-ministry-scope-schema.md    # Phase 1 — MinistryScopeAcknowledgment JSON schema
│   ├── logov2-rewrite-visual-specs.md     # Phase 1 — per-file visual spec (8 REWRITE + 1 PORT)
│   └── contrast-measurements.md           # Phase 1 — every pair + measured ratio
├── quickstart.md                          # Phase 1 — dev launches TUI, verifies splash + consent
├── checklists/
│   └── requirements.md                    # From /speckit-specify (already present)
└── tasks.md                               # Phase 2 output (/speckit-tasks command — NOT created here)
```

### Source Code (repository root)

```text
tui/
├── src/
│   ├── components/
│   │   ├── onboarding/                    # NEW directory (first PORT/REWRITE into family)
│   │   │   ├── Onboarding.tsx             # REWRITE from .references/.../components/Onboarding.tsx (row 165)
│   │   │   ├── PIPAConsentStep.tsx        # NEW — spec FR-012/FR-013; no CC analog
│   │   │   ├── MinistryScopeStep.tsx      # NEW — spec FR-015/FR-016; no CC analog
│   │   │   └── LogoV2/                    # REWRITE family (rows 31/35/37/38/39/41/45)
│   │   │       ├── AnimatedAsterisk.tsx   # REWRITE (row 31)
│   │   │       ├── CondensedLogo.tsx      # REWRITE (row 35)
│   │   │       ├── Feed.tsx               # REWRITE (row 37)
│   │   │       ├── FeedColumn.tsx         # PORT    (row 38)
│   │   │       ├── feedConfigs.tsx        # REWRITE (row 39)
│   │   │       ├── LogoV2.tsx             # REWRITE (row 41)
│   │   │       └── WelcomeV2.tsx          # REWRITE (row 45)
│   │   └── chrome/
│   │       └── KosmosCoreIcon.tsx         # REWRITE from .references/.../components/FastIcon.tsx (row 162)
│   ├── theme/
│   │   ├── dark.ts                        # MUTATE — DELETE 7 CC-brand tokens, ADD 10 KOSMOS tokens, REPLACE background
│   │   ├── tokens.ts                      # MUTATE — same DELETE/ADD against the ThemeToken type alias
│   │   └── (default.ts, light.ts, provider.tsx) # UNCHANGED
│   └── hooks/
│       └── useReducedMotion.ts            # NEW — reads NO_COLOR + KOSMOS_REDUCED_MOTION env flags (consumed by FR-024)
└── tests/
    ├── onboarding/
    │   ├── Onboarding.snap.test.tsx       # Ink snapshot — 3-step flow happy path
    │   ├── PIPAConsentStep.snap.test.tsx  # Ink snapshot + accept/decline branches
    │   └── MinistryScopeStep.snap.test.tsx # Ink snapshot + partial opt-in
    ├── LogoV2/
    │   ├── LogoV2.snap.test.tsx           # reduced-motion + 80-col + 50-col variants
    │   └── AnimatedAsterisk.snap.test.tsx # shimmer + static fallback
    └── theme/
        └── tokens.compile.test.ts         # compile-time assertion: 7 deletes + 10 adds

src/kosmos/
└── memdir/
    ├── user_consent.py                    # NEW — Pydantic v2 PIPAConsentRecord + reader/writer
    ├── ministry_scope.py                  # NEW — Pydantic v2 MinistryScopeAcknowledgment + reader/writer
    └── __init__.py                        # UPDATE — export new models

src/kosmos/tools/
└── main_router.py                         # UPDATE — add ministry-scope guard (SC-009 pre-network refusal)

tests/memdir/
├── test_user_consent.py                   # schema round-trip + append-only invariant
└── test_ministry_scope.py                 # opt-in/opt-out persistence + refusal at router

docs/design/
├── brand-system.md                        # POPULATE § 3, § 4, § 5, § 6, § 7, § 9 (FR-027)
└── contrast-measurements.md               # NEW — per-pair contrast table (FR-003)

docs/tui/
└── accessibility-gate.md                  # UPDATE § 7 handoff note — acknowledge Epic H's contrast measurements
```

**Structure Decision**: This is a **multi-surface feature** spanning TypeScript TUI components + Python memdir schema + docs. The KOSMOS monorepo already has `tui/` (Bun/TypeScript) and `src/kosmos/` (Python) as peer root directories per Spec 287 + Spec 032. No new top-level directory is introduced. New subdirectories `tui/src/components/onboarding/`, `tui/src/components/chrome/`, `src/kosmos/memdir/` (already exists under Spec 027 but extended here with two new modules) follow the conventions established by the component-catalog mapping in `docs/tui/component-catalog.md § Epic H rows` (kosmos-tree-map.md `onboarding/` and `chrome/` targets).

## Phase 0 — Outline & Research

Phase 0 resolves every open design decision by mapping it to a reference source from `docs/vision.md § Reference materials` + the spec-specific upstream sources (ADR-006 A-9, brand-system.md § 1–§ 2, accessibility-gate.md § 7, component-catalog Epic H rows, CC restored-src tree). Output: `research.md` with a Decision / Rationale / Alternatives-considered block for each item below.

### Research tasks

**R-1 — `MinistryCode` TitleCase normalisation in token names**
- *Question*: Epic body spelled `agentSatelliteMOHW` / `agentSatelliteKOROAD` with all-caps; `docs/design/brand-system.md § 2` BNF requires `MinistryCode` to be TitleCased proper-noun form (`Koroad`, `Kma`, `Hira`, `Nmc`).
- *Primary reference*: `docs/design/brand-system.md § 2` BNF block — `MinistryCode ::= "Koroad" | "Kma" | "Hira" | "Nmc" | …`.
- *Decision to record*: adopt TitleCase throughout this spec's artefacts. `tokens.ts` ships `agentSatelliteKoroad`, `agentSatelliteKma`, `agentSatelliteHira`, `agentSatelliteNmc`.
- *Alternatives rejected*: all-caps (would fail the BNF parser in `specs/034-tui-component-catalog/contracts/grep-gate-rules.md § 4`).

**R-2 — Shimmer-variant hex selection for `kosmosCore` and `orbitalRing`**
- *Question*: FR-010 commits to drawing shimmer hex from the 16-hex superset in `assets/kosmos-logo.svg` — which shade is authoritatively correct for each shimmer slot?
- *Primary reference*: `assets/kosmos-logo.svg` (16-hex palette: `#0a0e27`, `#1a1040`, `#34d399`, `#60a5fa`, `#6366f1`, `#6ee7b7`, `#818cf8`, `#93c5fd`, `#94a3b8`, `#a5b4fc`, `#a78bfa`, `#c4b5fd`, `#c7d2fe`, `#e0e7ff`, `#f472b6`, `#f9a8d4`). CC parallel: `claudeShimmer = rgb(235,159,127)` is a lightened shade of `claude = rgb(215,119,87)` (dark.ts lines 15–16).
- *Decision to record*: `kosmosCoreShimmer = #a5b4fc` (lightened `#818cf8` → `#6366f1` gradient base), `orbitalRingShimmer = #c7d2fe` (lightened `#60a5fa` → `#a78bfa` gradient). Both pass 4.5 : 1 against `#0a0e27` background.
- *Alternatives considered*: `#6ee7b7` (mint) and `#f9a8d4` (pink) — rejected because they belong to the ministry-satellite family and would collide semantically.

**R-3 — Contrast-ratio measurement methodology**
- *Question*: FR-003 and SC-001 require every colour pair to meet the WCAG 2.1 AA threshold. Which tooling / formula / rounding rule is authoritative?
- *Primary reference*: WCAG 2.1 Success Criterion 1.4.3 formula (relative-luminance ratio). `docs/tui/accessibility-gate.md § 7` imposes the threshold but delegates measurement choice to Epic H.
- *Decision to record*: use the W3C published formula via a self-contained Bun script (`scripts/compute-contrast.mjs`) that reads tokens from `tui/src/theme/dark.ts`, pairs each foreground slot with every background slot it renders against, and emits a Markdown table to `docs/design/contrast-measurements.md`. Rounding: two decimals. Threshold: ≥ 4.5 (body) / ≥ 3.0 (non-text), inclusive.
- *Alternatives considered*: npm `wcag-contrast` package (rejected — new runtime dep violates AGENTS.md); online audit tools (rejected — not reproducible in CI).

**R-4 — Memdir USER-tier record file layout**
- *Question*: FR-013 / FR-016 persist records to memdir USER tier. Which directory layout, file-naming convention, and append semantics apply?
- *Primary reference*: `docs/vision.md § Context assembly — memdir tiers`; Spec 027 §4 mailbox pattern (`KOSMOS_AGENT_MAILBOX_ROOT` = `~/.kosmos/mailbox/`); Spec 032 `SessionRingBuffer` precedent for append-only state.
- *Decision to record*: consent records at `~/.kosmos/memdir/user/consent/<iso-timestamp>-<session-id>.json`; ministry-scope records at `~/.kosmos/memdir/user/ministry-scope/<iso-timestamp>-<session-id>.json`. Latest record per kind is the effective state; older records are kept for audit (append-only). POSIX `fsync` on write per Spec 027 §4.
- *Alternatives considered*: single file overwritten on each consent update (rejected — violates audit-log requirement from Constitution Principle II + vision.md Layer 3 permission-pipeline auditability).

**R-5 — AAL gate value taxonomy**
- *Question*: FR-013 records an AAL field. Which value set applies and who owns it?
- *Primary reference*: `specs/033-permission-v2-spectrum/` — PermissionMode spectrum (`plan`, `default`, `acceptEdits`, `bypassPermissions`, etc.) + AAL layer.
- *Decision to record*: reuse Spec 033's `AuthenticatorAssuranceLevel` enum — values `{AAL1, AAL2, AAL3}`. Onboarding records the citizen's current AAL at consent time (default `AAL1` — pre-identity-verification). Subsequent upgrades write new consent records per R-4.
- *Alternatives considered*: inventing a local enum (rejected — would duplicate Spec 033 contract).

**R-6 — Onboarding state-machine re-entry**
- *Question*: FR-014 allows escape-exit mid-onboarding; SC-012 fast-paths returning citizens. How is the state machine structured and when does it re-render?
- *Primary reference*: `.references/claude-code-sourcemap/restored-src/src/components/Onboarding.tsx` (CC step registry: indexed `useState<number>` currentStepIndex; linear advance via `goToNextStep`).
- *Decision to record*: straight line `splash → pipa-consent → ministry-scope-ack → done`. No branching, no back-navigation. Escape at any step exits session (calls `process.exit(0)` equivalent via Ink `useApp().exit()`). Re-entry on next launch checks memdir USER consent record against the current `CONSENT_VERSION` constant; match → skip to splash-only fast-path; mismatch → re-render PIPA step with new version.
- *Alternatives considered*: Wizard-style back-navigation (rejected — defer to `wizard/*` REWRITE, a Deferred Items row; not needed for 3-step linear flow).

**R-7 — CC LogoV2 layout-mode calculation reuse**
- *Question*: FR-017 preserves the CC layout-mode switch. Which CC utility files are ported vs. rewritten?
- *Primary reference*: `.references/claude-code-sourcemap/restored-src/src/utils/logoV2Utils.ts` (exports `getLayoutMode`, `calculateLayoutDimensions`, `calculateOptimalLeftWidth`, `formatWelcomeMessage`, `truncatePath`, `getRecentActivitySync`, `getRecentReleaseNotesSync`, `getLogoDisplayData`).
- *Decision to record*: PORT `getLayoutMode`, `calculateLayoutDimensions`, `calculateOptimalLeftWidth`, `formatWelcomeMessage` (generic terminal-size math — no CC content). REWRITE `getRecentActivitySync` → `getKosmosSessionHistorySync` (memdir Session tier). REWRITE `getRecentReleaseNotesSync` → `getMinistryAvailabilitySync` (Spec 022 adapter registry). DISCARD CC-specific `getLogoDisplayData` (includes Anthropic branding).
- *Alternatives considered*: Rewrite all of `logoV2Utils.ts` (rejected — wastes reusable layout math; violates PORT-first principle of catalog).

**R-8 — Reduced-motion env flag handling**
- *Question*: FR-024 + accessibility-gate.md § 1.1 require honouring `NO_COLOR` and `KOSMOS_REDUCED_MOTION=1`. Which hook emits the render-time decision?
- *Primary reference*: accessibility-gate.md § 1.1 pathway 2 ("Reduced-motion fallback"). CC `useShimmerAnimation.ts` has no reduced-motion gate; KOSMOS must add one.
- *Decision to record*: new `tui/src/hooks/useReducedMotion.ts` reads `process.env.NO_COLOR` and `process.env.KOSMOS_REDUCED_MOTION`; returns boolean `prefersReducedMotion`. Consumed by `AnimatedAsterisk` (skips `useShimmerAnimation`), by `orbitalRing` shimmer (static gradient only), by LogoV2 splash (skips per-frame re-render). Follows the pattern of Spec 287's `useKoreanIME`.
- *Alternatives considered*: conditional `useEffect` gates per-component (rejected — scatters the flag read; centralising in a hook matches Spec 287 conventions).

**R-9 — Hangul and Korean-label rendering under Ink**
- *Question*: Every citizen-facing label in this spec is Korean. Does Ink handle Hangul width, combining characters, and wide-char alignment correctly out of the box?
- *Primary reference*: Spec 287 `stringWidth.ts` (already ported from CC for East-Asian wide-char measurement); `docs/vision.md § TUI experience surface`; CC `src/ink/stringWidth.ts`.
- *Decision to record*: rely on Spec 287's `stringWidth` for all label width calculations (already handles Hangul syllable blocks as wide-char width 2). No new measurement utility. Ministry labels use Korean names ("한국도로공사", "기상청", "건강보험심사평가원", "국립중앙의료원") with English adapter codes (KOROAD, KMA, HIRA, NMC) in parentheses for screen-reader disambiguation.
- *Alternatives considered*: English-only labels (rejected — citizen-facing surface must be Korean per `docs/vision.md § Citizen onboarding`).

**R-10 — `kosmos-logo-dark.svg` doc-drift fix**
- *Question*: `docs/design/brand-system.md § 1` cross-references `assets/kosmos-logo-dark.svg` which does not exist on disk.
- *Primary reference*: filesystem inspection (`ls assets/` returns only `kosmos-logo.svg`, `kosmos-banner-dark.svg`, and their PNG equivalents).
- *Decision to record*: single-line doc fix in Epic H PR — replace the `§ 1` cross-reference `assets/kosmos-logo-dark.svg` with `assets/kosmos-banner-dark.svg` (the file that actually holds the dark-background palette and is cited by ADR-006 A-9 as the authoritative extraction source). No new SVG file is authored.
- *Alternatives considered*: author the missing SVG (rejected — TUI does not render SVG; redundant work).

### Validate Deferred Items (Constitution Principle VI gate)

- Deferred Items table in spec.md § Scope Boundaries contains **10 rows**. 2 rows cite concrete GitHub issue numbers (#1308, #25, #1310). 8 rows are marked `NEEDS TRACKING` — these will be resolved to placeholder issues by `/speckit-taskstoissues`.
- Out-of-Scope (Permanent) subsection contains **4 rows** (light/high-contrast themes, SVG rendering, audio, browser/mobile).
- **Scan result**: spec.md prose contains the phrases "follow-up spec", "future phase", "deferred" — every occurrence is matched by a Deferred Items row. No ghost deferrals detected.
- **Open-issue verification**: #1308 (Epic K Settings) OPEN, #25 (deep 4.1.2 compliance) OPEN, #1310 (Epic M component catalog) OPEN as of 2026-04-20 `gh api graphql` check.
- **Gate result**: **PASS** — deferred items consistent with Principle VI.

### Phase 0 output

`research.md` will consolidate R-1 through R-10 in the Decision / Rationale / Alternatives format, followed by the Deferred Items validation summary. All `NEEDS CLARIFICATION` markers from the spec template are resolved (the spec contains zero such markers — every ambiguity was pre-resolved into the Assumptions section during `/speckit-specify`).

## Phase 1 — Design & Contracts

**Prerequisites**: `research.md` complete.

### Entities → `data-model.md`

- **`BrandPalette`** — closed mapping `(MetaphorRole × Variant?) → hex`. Fields: `tokenName: str`, `primaryHex: str`, `shimmerHex: Optional[str]`, `ministryBinding: Optional[Literal[KOROAD, KMA, HIRA, NMC]]`, `measuredContrastRatio: Optional[float]`, `measuredContrastAgainst: Optional[str]`. Invariants: `tokenName` matches `brand-system.md § 2` BNF; `ministryBinding` set iff `tokenName` starts with `agentSatellite`; `measuredContrastRatio ≥ 4.5` for body-text tokens, `≥ 3.0` for non-text.
- **`OnboardingStep`** — registry entry. Fields: `stepId: Literal[splash, pipa-consent, ministry-scope-ack, done]`, `component: React.FC`, `advanceCondition: () => boolean`, `skipCondition: (userTier: MemdirUserTier) => boolean`. Invariants: `stepId` ordering fixed; no branching; `skipCondition` may only evaluate memdir USER state, never session or system state.
- **`PIPAConsentRecord`** — append-only memdir USER entry. Fields: `consentVersion: str` (semantic `vN` string), `timestamp: datetime` (UTC, ISO-8601), `aalGate: AuthenticatorAssuranceLevel`, `sessionId: UUID`. Invariants: immutable after write; `consentVersion` monotonically non-decreasing; `timestamp` ≤ `datetime.now(UTC)` at write; `aalGate` from Spec 033 enum.
- **`MinistryScopeAcknowledgment`** — memdir USER entry recording opt-in state. Fields: `scopeVersion: str`, `timestamp: datetime`, `sessionId: UUID`, `ministries: frozenset[MinistryOptIn]` where `MinistryOptIn = (ministryCode: Literal[KOROAD, KMA, HIRA, NMC], optIn: bool)`. Invariants: exactly 4 entries (one per Phase 1 ministry); frozenset enforced by Pydantic v2.
- **`KosmosThemeToken`** — TypeScript type alias exported by `tui/src/theme/tokens.ts`. Fields: union of 10 metaphor tokens (FR-006) + retained semantic slots (FR-007). Invariants: zero intersection with DELETE set from FR-005; every string-valued at runtime.
- **`LogoV2RewriteComponent`** — catalog row materialisation. Fields: `ccSourcePath: str`, `kosmosTargetPath: str`, `verdict: Literal[PORT, REWRITE]`, `accessibilityGateAnchor: str` (`[ag-logov2]` / `[ag-onboarding]` / `[ag-logo-wordmark]`), `reducedMotionBehaviour: str` (static fallback description). Invariants: 9 rows total (spec FR-017 through FR-023); every row has an accessibility-gate anchor.

### Contracts → `contracts/`

- **`contracts/brand-token-surface.md`** — the exact `ThemeToken` delete set (FR-005, 7 identifiers), add set (FR-006, 10 identifiers), preserve set (FR-007, enumerated), header-comment text (FR-008), and the `dark.ts` hex binding table (FR-009, FR-010, FR-011). Authoritative for the Brand Guardian grep gate.
- **`contracts/onboarding-step-registry.md`** — the 3-step state machine specified as a pure-function reducer (`(state, action) → state`), the keybinding surface for each step (Enter = advance, Escape = exit, ↑/↓ = selection in ministry-scope step), and the memdir USER read/write pattern at session start and step completion.
- **`contracts/memdir-consent-schema.md`** — the PIPAConsentRecord JSON schema (Pydantic v2-generated), directory layout (`~/.kosmos/memdir/user/consent/`), file-naming convention, `fsync` + rename atomicity pattern, and the current `CONSENT_VERSION` constant declaration.
- **`contracts/memdir-ministry-scope-schema.md`** — the MinistryScopeAcknowledgment JSON schema, directory layout, and the main-tool-router guard contract — `router.resolve(tool_id, params) → Refusal | Invoke` — with the refusal payload shape and the citizen-visible Korean error copy.
- **`contracts/logov2-rewrite-visual-specs.md`** — per-file visual spec for the 9 components: input props, token references (`useTheme()` keys), text content (Korean + English), layout rules (width, height, breakpoints), animation behaviour (shimmer vs. static), and the reduced-motion fallback rendering. One section per component.
- **`contracts/contrast-measurements.md`** — the fg/bg pair matrix with measured ratios. Populated by `scripts/compute-contrast.mjs` (R-3). Every pair ≥ threshold; any pair that fails triggers a token-value bump in FR-011.

### Quickstart → `quickstart.md`

Developer-facing walk-through:
1. `bun install` (no new deps expected).
2. `bun run tui/src/main.tsx` on a fresh machine → verify splash renders the orbital-ring composition.
3. `bun test tui/tests/onboarding/` → three-step snapshot suite passes.
4. `uv run pytest tests/memdir/` → consent + ministry-scope round-trip passes.
5. `bun run scripts/compute-contrast.mjs` → prints pair table; exit status 0 iff every pair ≥ threshold.
6. `NO_COLOR=1 bun run tui/src/main.tsx` → verify static-text fallback (no shimmer).
7. `KOSMOS_REDUCED_MOTION=1 bun run tui/src/main.tsx` → same as above.
8. `COLUMNS=70 bun run tui/src/main.tsx` → verify condensed-header layout.
9. `COLUMNS=45 bun run tui/src/main.tsx` → verify single-line fallback.
10. Decline the PIPA consent → session exits cleanly, no memdir record written.

### Agent context update

Run `.specify/scripts/bash/update-agent-context.sh claude` after Phase 1 artefacts land. This merges the new technology surface (`Bun scripts`, `Ink hooks`, `memdir user-tier models`) into the agent-specific context file, preserving manual additions between markers.

### Phase 1 output

`data-model.md`, `contracts/brand-token-surface.md`, `contracts/onboarding-step-registry.md`, `contracts/memdir-consent-schema.md`, `contracts/memdir-ministry-scope-schema.md`, `contracts/logov2-rewrite-visual-specs.md`, `contracts/contrast-measurements.md`, `quickstart.md`, updated agent-context file.

## Post-Design Constitution Check (re-evaluation after Phase 1)

| Principle | Post-design verdict | Notes |
|---|---|---|
| I. Reference-Driven Development | **PASS** | Every Phase 1 contract cites its CC source (LogoV2/*, Onboarding.tsx, logoV2Utils.ts, stringWidth.ts) and/or KOSMOS precedent (Spec 022 / 027 / 032 / 033 / 287). No invented abstraction. |
| II. Fail-Closed Security | **PASS** | `memdir-ministry-scope-schema.md` router guard is fail-closed by default — absent opt-in record ⇒ refusal. `memdir-consent-schema.md` refuses session start if consent record missing or version mismatch. |
| III. Pydantic v2 Strict Typing | **PASS** | `memdir-consent-schema.md` and `memdir-ministry-scope-schema.md` are `frozen=True` Pydantic v2 models; no `Any`; enums typed against Spec 033. |
| IV. Government API Compliance | **PASS (N/A)** | No live-API call introduced; SC-009 refusal is pre-network. Existing quota contracts preserved. |
| V. Policy Alignment | **PASS** | Public-API scope step materially implements Principle 8 + 9. |
| VI. Deferred Work Accountability | **PASS** | Phase 0 re-validated the 10-row Deferred table; 0 ghost deferrals. |

**Post-design result**: **PASS** — no principle regresses under the Phase 1 design. No Complexity Tracking entry required.

## Complexity Tracking

> Not required — Constitution Check passes both before Phase 0 and after Phase 1 with zero violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| (none) | — | — |

## Phase 2 planning

Phase 2 (tasks.md) is the output of `/speckit-tasks`, not of this command. Expected task shape: ≤ 90 sub-issues (AGENTS.md Sub-Issue 100-cap budget from `feedback_subissue_100_cap.md` memory), grouped by layer — Theme contract → Onboarding step registry → LogoV2 REWRITE family → memdir schemas → main-tool router guard → brand-system.md § 3–§ 9 authoring → contrast measurement → quickstart verification. Parallel-safe rows candidate: the 9 LogoV2 component REWRITEs (independent files, shared token contract only).
