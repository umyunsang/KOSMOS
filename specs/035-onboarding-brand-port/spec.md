# Feature Specification: Onboarding + Brand Port

**Feature Branch**: `035-onboarding-brand-port`
**Created**: 2026-04-20
**Status**: Draft
**Input**: User description: "Epic H #1302 — Onboarding + 브랜드 port. 참조: docs/tui/component-catalog.md (Epic H row), docs/design/brand-system.md §1-§2, docs/tui/accessibility-gate.md §7, ADR-006 Part A-9 (kosmosCore/orbitalRing), .references/claude-code-sourcemap/restored-src/src/components/LogoV2/ + Onboarding.tsx. 목표: 브랜드 팔레트 값 확정 + Onboarding 스플래시 + LogoV2 REWRITE 시각 사양."

**Epic**: [#1302 — Onboarding + brand port (binds ADR-006 A-9)](https://github.com/umyunsang/KOSMOS/issues/1302)
**Parent Initiative**: [#2 — Phase 2 Multi-Agent Swarm](https://github.com/umyunsang/KOSMOS/issues/2)

**Primary upstream sources**:
- `docs/adr/ADR-006-cc-migration-vision-update.md § A-9` (normative brand splash + palette anchor)
- `docs/design/brand-system.md § 1 — Brand metaphor` and `§ 2 — Token naming doctrine` (immutable naming contract)
- `docs/tui/component-catalog.md` rows 31 · 35 · 37 · 38 · 39 · 41 · 45 · 162 · 165 (Epic H-owned LogoV2 / FastIcon / Onboarding)
- `docs/tui/accessibility-gate.md § 3 (rows 31–37, 154, 156) + § 7` (contrast + REWRITE annotations, Epic H handoff)
- `.references/claude-code-sourcemap/restored-src/src/components/Onboarding.tsx` (CC step registry shape)
- `.references/claude-code-sourcemap/restored-src/src/components/LogoV2/{LogoV2,WelcomeV2,CondensedLogo,AnimatedAsterisk,Feed,FeedColumn,feedConfigs}.tsx`
- `assets/kosmos-logo.svg`, `assets/kosmos-banner-dark.svg` (authoritative palette extraction source per ADR-006 A-9)
- `tui/src/theme/{dark.ts,tokens.ts}` (current 69-token CC-inherited state)

**Palette-selection constraint (non-negotiable, FR-022 of Epic M § 7)**: every foreground/background pair rendered by any PORT or REWRITE component MUST meet **≥ 4.5 : 1** for body text and **≥ 3 : 1** for large text / non-text UI chrome. This constraint is acknowledged and binds every FR below that introduces a colour pair.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Citizen sees the KOSMOS orbital-ring splash on first launch (Priority: P1)

A first-time citizen user launches the KOSMOS TUI from a terminal. Instead of the current placeholder screen that inherits the Claude Code "Welcome to Claude Code" wordmark on a cyan (`rgb(0,204,204)`) background, the user sees the KOSMOS galaxy splash: a navy deep-space background, a glowing central asterisk ("kosmosCore") surrounded by an orbital ring, with the wordmark "KOSMOS" and subtitle "KOREAN PUBLIC SERVICE MULTI-AGENT OS", and four satellite nodes around the ring indicating the Phase 1 ministry adapters. The splash communicates the 은하계 metaphor — one conversational window unifying many ministry APIs — without requiring the citizen to read any documentation.

**Why this priority**: The splash is the first citizen-facing surface in the entire session. Shipping the TUI with Claude Code brand residue (`Welcome to Claude Code` wordmark, `claude` / `clawd` tokens, placeholder cyan background) directly contradicts the KOSMOS mission stated in `docs/vision.md § What is original to KOSMOS` and the ADR-006 A-9 commitment to a citizen-legible Korean public-service brand. Without this, no downstream citizen-facing claim (Korea AI Action Plan 공공AX Principle 9, PIPA transparency, "single conversational window") is honestly testable.

**Independent Test**: Launch the TUI in a fresh session. Verify that within the first frame (a) the wordmark is "KOSMOS", not "Claude Code", (b) the background anchor colour is navy `#0a0e27`, not cyan `rgb(0,204,204)`, (c) the orbital-ring and core gradients render using the ADR-006 A-9 palette, (d) four labelled satellite nodes are visible for the Phase 1 ministries.

**Acceptance Scenarios**:

1. **Given** a fresh KOSMOS session with no prior onboarding state, **When** the TUI renders its first frame, **Then** the splash displays the "KOSMOS" wordmark in the `wordmark` token (`#e0e7ff`), the "KOREAN PUBLIC SERVICE MULTI-AGENT OS" subtitle in the `subtitle` token (`#94a3b8`), against a navy background (`#0a0e27` → `#1a1040` gradient anchor).
2. **Given** the splash is rendered, **When** the user observes the centre of the screen, **Then** a glowing "kosmosCore" asterisk (`#818cf8` → `#6366f1` gradient) is visible, surrounded by an "orbitalRing" arc (`#60a5fa` → `#a78bfa` gradient).
3. **Given** the splash is rendered, **When** the user observes the area around the ring, **Then** four satellite nodes are visible, each labelled with a Phase 1 ministry adapter code and rendered in a distinct `agentSatellite{MINISTRY}` accent colour.
4. **Given** the splash is rendered in a terminal with `NO_COLOR=1` or `KOSMOS_REDUCED_MOTION=1`, **When** the first frame renders, **Then** a static-text equivalent is emitted (no shimmer animation) that still conveys the wordmark, subtitle, and ministry roster in a screen-reader-consumable text stream.
5. **Given** the splash is rendered in a terminal with ≤ 80 columns, **When** the layout computes, **Then** the splash degrades to a condensed form (header-only wordmark + subtitle + ministry list) without visual truncation of any label.

---

### User Story 2 — Citizen records PIPA consent with version, timestamp, and AAL (Priority: P1)

During onboarding, after the splash, the citizen is presented with a PIPA (개인정보 보호법 — Personal Information Protection Act) consent step. The step displays the consent version identifier, a plain-language explanation in Korean of what personal information KOSMOS processes (PIPA §26 처리위탁 role per `project_pipa_role.md` memory), which ministry APIs may receive that information, and the current Authenticator Assurance Level (AAL) gate. The citizen confirms consent with an explicit keyboard action. The consent decision is recorded with the three mandatory fields — consent version, ISO-8601 timestamp, and AAL gate — and pinned to the memdir USER tier so that a subsequent session does not re-prompt unless the consent version changes.

**Why this priority**: Without a recorded consent trail, any ministry API call made in a subsequent session is an unlawful processing event under PIPA § 22 (개인정보 수집 이용 동의). The Epic body explicitly binds this to ADR-006 A-9 and to the `project_pipa_role.md` memory which establishes KOSMOS as a PIPA § 26 processor (수탁자) by default. This makes the consent record a hard compliance prerequisite for Phase 2 adapter rollout (`specs/029-phase2-adapters-119-mohw/` and successors).

**Independent Test**: Complete the onboarding flow. Inspect the memdir USER tier after onboarding exits. Verify that a consent record exists containing exactly the three fields (consent version matching the prompt shown, ISO-8601 timestamp within the onboarding session window, AAL gate value drawn from the Spec 033 Permission v2 spectrum).

**Acceptance Scenarios**:

1. **Given** a fresh session with no prior consent record in memdir USER, **When** the onboarding sequence advances past the splash, **Then** a PIPA consent step renders showing the consent version, a Korean-language summary of processed personal information, the enumerated ministry recipient list, and the current AAL gate.
2. **Given** the PIPA consent step is displayed, **When** the citizen presses Enter (or the equivalent "I consent" affordance), **Then** a consent record is written to memdir USER containing consent version + ISO-8601 timestamp + AAL gate, and the onboarding sequence advances to the Public-API scope step.
3. **Given** the PIPA consent step is displayed, **When** the citizen presses Escape (or declines), **Then** the session exits without writing any consent record, and no subsequent ministry API call may occur in that session.
4. **Given** a citizen has completed onboarding previously with consent version `v1` and the consent version has since been bumped to `v2`, **When** the citizen launches a new session, **Then** the PIPA consent step re-renders with the `v2` prompt and the citizen must re-confirm; the existing `v1` record remains in memdir USER as an append-only history entry.
5. **Given** the consent record exists and the consent version has not changed, **When** the citizen launches a subsequent session, **Then** the onboarding flow skips the PIPA consent step and advances directly to the main TUI (splash still renders but is not interactive).

---

### User Story 3 — Citizen opts in to Phase 1 ministry API scopes (Priority: P1)

Following the PIPA consent step, the citizen is presented with a Public-API scope acknowledgment step that explicitly enumerates the four Phase 1 seed ministry adapters (KOROAD, KMA, HIRA, NMC). Each ministry is listed with its Korean name, a one-line plain-language description of what kind of request KOSMOS may make on the citizen's behalf (e.g. "KOROAD — 교통사고 위험 구간 조회"), and its accent colour drawn from the `agentSatellite{MINISTRY}` palette. The citizen opts in to each ministry individually or accepts the default "all four" aggregate. This makes ministry API invocation visible to the citizen at the moment of consent — unlike the fragmented status-quo DX where each ministry portal collects its own consent silently.

**Why this priority**: The DX → AX migration framing in the Epic body names this as a first-class citizen-legibility requirement. Korea AI Action Plan 공공AX Principle 9 requires citizen-facing public-service AI to communicate which ministries are answering; honouring that principle structurally starts at onboarding. The four-ministry enumeration is also the concrete evidence that KOSMOS's Spec 022 main-tool resolves to exactly this seed adapter set.

**Independent Test**: Complete the onboarding flow selecting "KOROAD + KMA only". Inspect the resulting scope acknowledgment in memdir USER. Verify (a) all four ministries were enumerated in the step UI, (b) the two not selected (HIRA, NMC) are recorded as `opt-in=false`, (c) subsequent tool calls in the session that target the declined ministries are refused before network invocation with a clear citizen-facing message.

**Acceptance Scenarios**:

1. **Given** the PIPA consent step has been completed, **When** the onboarding sequence advances, **Then** a Public-API scope acknowledgment step renders listing KOROAD, KMA, HIRA, NMC with Korean names, one-line descriptions, and their `agentSatellite{MINISTRY}` accent colours.
2. **Given** the scope acknowledgment step is displayed, **When** the citizen confirms all four ministries, **Then** each ministry is recorded as `opt-in=true` in memdir USER with the same ISO-8601 timestamp, and the onboarding sequence completes.
3. **Given** the scope acknowledgment step is displayed, **When** the citizen declines one or more ministries, **Then** each declined ministry is recorded as `opt-in=false`, and any subsequent tool call targeting a declined ministry in the same or later session is refused at the main-tool router with a citizen-visible "ministry opt-out" message.
4. **Given** a ministry is displayed, **When** the citizen uses a screen reader, **Then** the ministry name, description, and accent-role are announced as plain UTF-8 text in the terminal output buffer; colour alone never conveys the ministry identity.

---

### User Story 4 — Engineer and Brand Guardian read a coherent KOSMOS brand token type surface (Priority: P2)

A developer working on a downstream PORT task opens `tui/src/theme/tokens.ts` and `tui/src/theme/dark.ts` to select a colour for a new component. They find a type surface whose identifiers encode the KOSMOS 은하계 metaphor (kosmosCore, orbitalRing, wordmark, subtitle, agentSatelliteKoroad, etc.) rather than Claude Code vendor names (claude, claudeShimmer, clawd_body, briefLabelClaude). The dark-theme palette map resolves those names to the ADR-006 A-9 hex values. A PR that adds a new `claude*` or `clawd*` identifier is rejected by the Brand Guardian grep gate defined in `specs/034-tui-component-catalog/contracts/grep-gate-rules.md`.

**Why this priority**: The token surface is the downstream interface that every component PORT (Epic H follow-up Tasks, Epic M) inherits. Leaving CC-branded identifiers on the surface pollutes every future import-site with vendor-mismatch evidence. However, this is P2 (not P1) because it is visible only to engineers, while P1 stories cover citizen-visible surfaces.

**Independent Test**: Run the grep gate against a simulated PR that adds a token named `claudeHover`. The gate MUST reject with BAN-01 citing `docs/design/brand-system.md § 2`. Separately, compile `tui/src/theme/tokens.ts` and verify the TypeScript type `ThemeToken` has DELETED `claude`, `claudeShimmer`, `claudeBlue_FOR_SYSTEM_SPINNER`, `claudeBlueShimmer_FOR_SYSTEM_SPINNER`, `clawd_body`, `clawd_background`, `briefLabelClaude` and ADDED the 10 KOSMOS metaphor tokens from FR-010.

**Acceptance Scenarios**:

1. **Given** `tui/src/theme/tokens.ts` at the tip of this Epic's PR, **When** the file is compiled by the TUI's TypeScript build, **Then** the `ThemeToken` type alias exports the full KOSMOS surface (10 new metaphor tokens + semantic slots retained) and rejects at compile time any consumer still referencing one of the seven deleted identifiers.
2. **Given** a PR adds `claudeHover` to `tokens.ts`, **When** the Brand Guardian grep gate runs, **Then** the gate fails with a BAN-01 violation citing `docs/design/brand-system.md § 2`.
3. **Given** a PR adds `agentSatelliteMohw` to `tokens.ts`, **When** the grep gate runs and `docs/design/brand-system.md § 1` roster does NOT list MOHW, **Then** the gate fails with an unrecognised `MinistryCode` error; once a PR to § 1 merges adding MOHW, the gate accepts the token.
4. **Given** the header comment of `tui/src/theme/dark.ts`, **When** a human or automated reviewer inspects it, **Then** the comment explicitly notes "KOSMOS 브랜드 토큰으로 리네이밍됨 (ADR-006 A-9)" in addition to the original "Source: .references/..." line.

---

### User Story 5 — TUI renders the LogoV2 REWRITE family with the KOSMOS metaphor (Priority: P2)

The eight Epic H-owned LogoV2 / root-logo catalog rows (AnimatedAsterisk, CondensedLogo, Feed, FeedColumn, feedConfigs, LogoV2, WelcomeV2, FastIcon) render in the TUI using KOSMOS tokens and KOSMOS content semantics — not Claude Code vendor content. Specifically: `AnimatedAsterisk` renders the kosmosCore glyph with the `rainbow_*` shimmer animation engine ported from CC; `CondensedLogo` renders a KOSMOS wordmark + session/model header line; `LogoV2` renders the orbital-ring splash composition; `WelcomeV2` renders the citizen welcome screen; `FastIcon` becomes `KosmosCoreIcon` (renamed file) and renders the kosmosCore asterisk instead of the CC fast-mode lightning glyph; `Feed` + `FeedColumn` + `feedConfigs` render ministry-availability and recent-session feeds instead of CC-specific activity / changelog / guest-pass feeds.

**Why this priority**: These files are the concrete rendering surfaces that bring the palette contract to life on-screen. They are P2 because the P1 splash behaviour (User Story 1) is observable without internally consistent REWRITE wiring — a prototype could inline-render the splash directly. Shipping the full REWRITE family is the engineering-quality bar that prevents regressions once downstream PORT work consumes these components.

**Independent Test**: For each of the eight catalog rows, run the REWRITE-target file under a visual-regression fixture and confirm: (a) no CC-branded identifier appears in the rendered output (no "Claude Code", "Clawd", "guest pass", "Opus"), (b) the KOSMOS token surface is referenced (via `useTheme()` → KOSMOS tokens), (c) the `[ag-logov2]` / `[ag-onboarding]` / `[ag-logo-wordmark]` accessibility-gate rows pass (WCAG 1.4.3 + 4.1.2 + reduced-motion fallback).

**Acceptance Scenarios**:

1. **Given** the REWRITE target `tui/src/components/onboarding/LogoV2/AnimatedAsterisk.tsx`, **When** the component renders, **Then** it emits the kosmosCore asterisk glyph (not the CC teardrop) using the `rainbow_*` shimmer engine unchanged from CC, and no CC-specific rainbow cycle ordering is hard-coded.
2. **Given** the REWRITE target `tui/src/components/chrome/KosmosCoreIcon.tsx` (renamed from `FastIcon.tsx`), **When** the component renders, **Then** the file emits a kosmosCore asterisk in the `kosmosCore` token colour and NOT the CC fast-mode `chromeYellow` lightning glyph.
3. **Given** the REWRITE target `tui/src/components/onboarding/LogoV2/LogoV2.tsx`, **When** the component renders on first launch, **Then** it composes the splash (wordmark + subtitle + orbitalRing + kosmosCore + satellite-node row + session metadata) and does NOT import `Clawd`, `GuestPassesUpsell`, `EmergencyTip`, `VoiceModeNotice`, `Opus1mMergeNotice`, `ChannelsNotice`, or `OverageCreditUpsell`.
4. **Given** the REWRITE target `tui/src/components/onboarding/LogoV2/Feed.tsx` + `feedConfigs.tsx`, **When** the splash renders, **Then** the feed column shows (a) a "최근 세션" column bound to KOSMOS session history and (b) a "부처 상태" column bound to ministry-adapter availability; it does NOT render CC recent-activity, guest-pass, or referral feeds.
5. **Given** every LogoV2 REWRITE file, **When** the accessibility-gate rows 31 · 32 · 33 · 35 · 36 · 37 · 154 · 156 are validated by `/speckit-analyze`, **Then** each row's WCAG criteria + KWCAG notes + contrast constraint are satisfied by the implementation.

---

### Edge Cases

- **Screen reader in terminal mode** — VoiceOver / NVDA / JAWS consume the splash via the text-stream pathway in `docs/tui/accessibility-gate.md § 1.1`. Animated shimmer MUST NOT be the sole carrier of information; every ministry node, the wordmark, the subtitle, and the consent prompt MUST be rendered as plain UTF-8 text that reads left-to-right, top-to-bottom in reading order.
- **Reduced-motion environment** (`NO_COLOR=1` or `KOSMOS_REDUCED_MOTION=1`) — the splash emits a static-text equivalent on a single render; the orbital-ring shimmer and the kosmosCore pulse animation are skipped; the ministry-node row remains fully legible.
- **Terminal width < 80 columns** — the splash degrades to a condensed header form. The wordmark, subtitle, and four-ministry row remain visible without label truncation; the orbital-ring visual may be omitted.
- **Terminal width < 50 columns** — the splash renders as a single "KOSMOS — 한국 공공서비스 대화창" text line plus the ministry list; this is below the practical TUI threshold but must degrade without erroring.
- **Colour-blind citizen** — the four `agentSatellite{MINISTRY}` accents pass the 4.5 : 1 contrast minimum against the navy background and are distinguishable from each other in deuteranopia and protanopia simulations; the ministry name label always accompanies the accent colour so colour is never the sole discriminator.
- **Already-consented returning user** — splash renders on launch (for brand consistency) but the PIPA consent step and the ministry scope step are skipped; an existing consent record in memdir USER whose version matches the current consent-version constant is sufficient.
- **Consent version bump mid-session** — consent versions only apply at session start; a bumped version deployed while a session is active does NOT invalidate the in-flight session's consent.
- **IME composition during onboarding navigation** — if the citizen's keyboard state is mid-Hangul-composition when the Enter / Escape key fires, the Epic E #1300 IME-safe gate MUST suppress the navigation action until composition commits. This inherits the `IME-safe = yes` invariants for row 156 (Onboarding.tsx) via acceptance-gate AG-04.
- **Missing `kosmos-logo-dark.svg` asset** — `docs/design/brand-system.md § 1` cross-reference points to a file not present on disk (only `kosmos-logo.svg` and `kosmos-banner-dark.svg` exist). The TUI does NOT render SVG; the hex values are extracted from the existing SVG files; this spec does not require authoring the missing file but documents the reference-drift as an assumption.
- **Grep gate false positive on semantic slot** — a PR that adds `successShimmer` must pass despite looking similar to BAN-04; the grep gate's allow-list for semantic slots from `docs/design/brand-system.md § 2 Exceptions` covers this.
- **`agentSatellite{MINISTRY}` without § 1 roster entry** — a PR that adds `agentSatelliteMohw` without first merging a § 1 roster entry fails the grep gate; the author opens a § 1 roster PR first (single-line addition), then the ministry token PR.

---

## Requirements *(mandatory)*

### Functional Requirements — Brand palette & token contract

- **FR-001**: System MUST define the canonical KOSMOS brand palette whose hex values are drawn from `assets/kosmos-logo.svg` and `assets/kosmos-banner-dark.svg`. The palette anchors are: background `#0a0e27` → `#1a1040`; kosmosCore `#818cf8` → `#6366f1`; orbitalRing `#60a5fa` → `#a78bfa`; wordmark `#e0e7ff`; subtitle `#94a3b8`; four `agentSatellite{MINISTRY}` accents drawn from `{#34d399, #f472b6, #93c5fd, #c4b5fd}`.
- **FR-002**: System MUST publish the final palette values into `docs/design/brand-system.md § 4 (Palette values)`, which today is a placeholder owned by Epic H. The § 4 section MUST enumerate every brand token name introduced in this spec, its primary hex value, any shimmer / muted variant hex value, and the ministry binding for each `agentSatellite{MINISTRY}` accent.
- **FR-003**: Every foreground / background colour pair introduced by this spec MUST meet the palette-selection constraint of `docs/tui/accessibility-gate.md § 7` — body text ≥ 4.5 : 1 against its background, large text and non-text UI chrome ≥ 3 : 1. System MUST record the measured contrast ratio for each pair in § 4 of `brand-system.md`.
- **FR-004**: System MUST assign the four Phase 1 `agentSatellite{MINISTRY}` hex values to KOROAD / KMA / HIRA / NMC (NOT to MOHW). The binding MUST be recorded in `docs/design/brand-system.md § 1` ministry-roster table and cross-referenced from § 4. The Epic body's `agentSatelliteMOHW` label is replaced by `agentSatelliteKma` because MOHW is not in the § 1 roster while KMA is a Phase 1 seed adapter (see Assumptions).

### Functional Requirements — `tokens.ts` type surface

- **FR-005**: System MUST DELETE the following seven identifiers from the `ThemeToken` type alias in `tui/src/theme/tokens.ts`: `claude`, `claudeShimmer`, `claudeBlue_FOR_SYSTEM_SPINNER`, `claudeBlueShimmer_FOR_SYSTEM_SPINNER`, `clawd_body`, `clawd_background`, `briefLabelClaude`.
- **FR-006**: System MUST ADD the following ten identifiers to `ThemeToken`, in the order and naming specified by `docs/design/brand-system.md § 2` grammar: `kosmosCore`, `kosmosCoreShimmer`, `orbitalRing`, `orbitalRingShimmer`, `wordmark`, `subtitle`, `agentSatelliteKoroad`, `agentSatelliteKma`, `agentSatelliteHira`, `agentSatelliteNmc`. Identifier casing conforms to the § 2 BNF (camelCase `MetaphorRole` + optional TitleCase `Variant`).
- **FR-007**: System MUST preserve the semantic-slot identifiers (`success`, `error`, `warning`, `text`, `inverseText`, `inactive`, `subtle`, `suggestion`, `remember`, all `diff*`, all `*_FOR_SUBAGENTS_ONLY`, all `rainbow_*` and `rainbow_*_shimmer`, all `rate_limit_*`, `autoAccept`, `bashBorder`, `permission`, `permissionShimmer`, `planMode`, `ide`, `promptBorder`, `promptBorderShimmer`, `merged`, `professionalBlue`, `chromeYellow`, `userMessageBackground`, `userMessageBackgroundHover`, `messageActionsBackground`, `selectionBg`, `bashMessageBackgroundColor`, `memoryBackgroundColor`, `fastMode`, `fastModeShimmer`, `briefLabelYou`, `warningShimmer`, `inactiveShimmer`) unchanged in `ThemeToken`. Semantic-slot identifiers are explicitly exempt from the DELETE list under `docs/design/brand-system.md § 2 Exceptions`.
- **FR-008**: System MUST update the header comment of `tui/src/theme/tokens.ts` and `tui/src/theme/dark.ts` to explicitly note "KOSMOS 브랜드 토큰으로 리네이밍됨 (ADR-006 A-9)" alongside the existing "Source: .references/claude-code-sourcemap/..." line.

### Functional Requirements — `dark.ts` palette map

- **FR-009**: System MUST REPLACE the placeholder `background: 'rgb(0,204,204)'` in `tui/src/theme/dark.ts` with the KOSMOS navy anchor `'rgb(10,14,39)'` (equivalent to `#0a0e27`). The gradient endpoint `#1a1040` is consumed by the LogoV2 REWRITE composition, not by the `background` token.
- **FR-010**: System MUST bind each of the ten new `ThemeToken` identifiers to its FR-001 hex value in `dark.ts` using the `rgb(...)` form consistent with the existing file. The shimmer variants (`kosmosCoreShimmer`, `orbitalRingShimmer`) MUST use a lightened shade drawn from the 16-hex palette present in `assets/kosmos-logo.svg` (plan phase selects among `#a5b4fc`, `#c7d2fe`, `#6ee7b7`, `#f9a8d4`).
- **FR-011**: System MUST NOT bump any semantic-slot token value in `dark.ts` beyond what is necessary to satisfy FR-003 contrast requirements against the new `background` anchor. If a semantic slot fails 4.5 : 1 against `#0a0e27`, its dark-theme value is raised (never lowered), and the new value is recorded alongside the contrast measurement in `docs/design/brand-system.md § 4`.

### Functional Requirements — Onboarding step registry

- **FR-012**: System MUST author a new `tui/src/components/onboarding/Onboarding.tsx` whose step registry replaces the CC developer-domain steps (`preflight`, `theme`, `oauth`, `api-key`, `security`, `terminal-setup`) with the following citizen-domain sequence: `splash` → `pipa-consent` → `ministry-scope-ack` → `done`. The step-id type, step-index advancement, and Ctrl+C / Ctrl+D exit wiring derive from the CC step-registry shape but no CC-specific step is retained.
- **FR-013**: System MUST record the citizen's PIPA consent as a memdir USER-tier record containing exactly three fields: consent version (string identifier), ISO-8601 timestamp (UTC), and AAL gate (value drawn from the Spec 033 Permission v2 spectrum). The record is append-only; a subsequent consent-version bump produces a new record without rewriting prior records.
- **FR-014**: System MUST provide a citizen-facing "skip" affordance — pressing Escape during the PIPA consent step or the ministry-scope step exits the session cleanly without writing any consent or scope record; no ministry API call is permitted for that session.
- **FR-015**: System MUST enumerate the four Phase 1 ministries (KOROAD, KMA, HIRA, NMC) in the ministry-scope-ack step, each with (a) Korean ministry name, (b) one-line Korean description of the kind of citizen request that ministry serves, (c) the `agentSatellite{MINISTRY}` accent colour, (d) an individual opt-in affordance. A default "all four" aggregate affordance MUST also be offered.
- **FR-016**: System MUST persist the ministry-scope acknowledgment as a memdir USER-tier record mapping each of the four ministries to `opt-in=true` or `opt-in=false`, with a single ISO-8601 timestamp covering the whole decision. Attempted tool calls against a declined ministry MUST be refused at the main-tool router (Spec 022) before any network invocation, with a citizen-facing Korean message naming the declined ministry.

### Functional Requirements — LogoV2 REWRITE visual specs

- **FR-017**: System MUST rewrite `tui/src/components/onboarding/LogoV2/LogoV2.tsx` to render the splash composition: wordmark + subtitle + orbitalRing + kosmosCore + satellite-node row + session metadata. The rewrite MUST NOT import `Clawd`, `GuestPassesUpsell`, `EmergencyTip`, `VoiceModeNotice`, `Opus1mMergeNotice`, `ChannelsNotice`, or `OverageCreditUpsell`. The layout-mode switch (condensed vs. full) inherited from CC `logoV2Utils.ts` MUST be preserved and parameterised on `useTerminalSize().columns`.
- **FR-018**: System MUST rewrite `tui/src/components/onboarding/LogoV2/AnimatedAsterisk.tsx` to render the kosmosCore asterisk glyph using the `rainbow_*` shimmer engine. The CC `chromeYellow` binding and the teardrop-asterisk glyph MUST be removed.
- **FR-019**: System MUST rewrite `tui/src/components/onboarding/LogoV2/CondensedLogo.tsx` to render a KOSMOS wordmark header + a compressed session-metadata line (model / effort / coordinator-mode from Spec 033). The CC "Claude Code" wordmark and Clawd / GuestPassesUpsell references MUST be removed.
- **FR-020**: System MUST rewrite `tui/src/components/onboarding/LogoV2/WelcomeV2.tsx` to render a KOSMOS welcome screen. The "Welcome to Claude Code" wordmark and the Apple-terminal-specific ASCII art for CC branding MUST be replaced with a "KOSMOS에 오신 것을 환영합니다" wordmark and the kosmosCore + orbitalRing visual.
- **FR-021**: System MUST port `tui/src/components/onboarding/LogoV2/FeedColumn.tsx` verbatim (palette-only swap) — this row is a generic multi-feed column layout with no CC-specific logic. The PORT includes renaming any imported token identifier to its KOSMOS equivalent.
- **FR-022**: System MUST rewrite `tui/src/components/onboarding/LogoV2/Feed.tsx` and `tui/src/components/onboarding/LogoV2/feedConfigs.tsx` to emit exactly two feed columns on the splash: "최근 세션" (bound to KOSMOS session history, sourced from memdir Session tier) and "부처 상태" (bound to adapter-availability signals from the Spec 022 registry). The four CC feed factories (`createRecentActivityFeed`, `createWhatsNewFeed`, `createProjectOnboardingFeed`, `createGuestPassesFeed`) and the `OverageCreditFeed` MUST be deleted.
- **FR-023**: System MUST rewrite `tui/src/components/FastIcon.tsx` as `tui/src/components/chrome/KosmosCoreIcon.tsx` (file renamed). The rewrite removes the `chromeYellow` lightning glyph and emits the kosmosCore asterisk glyph tinted with the `kosmosCore` token. Existing consumers of `FastIcon` in the TUI are updated to import `KosmosCoreIcon` as part of this PR.

### Functional Requirements — Reduced-motion, screen-reader, and contrast guarantees

- **FR-024**: Every REWRITE file listed in FR-017 through FR-023 MUST honour `NO_COLOR=1` and `KOSMOS_REDUCED_MOTION=1` env flags. Under either flag, animation (shimmer, asterisk pulse) is skipped and a static-text equivalent renders that carries the same information. This satisfies `docs/tui/accessibility-gate.md § 1.1` pathway 2.
- **FR-025**: Every REWRITE file MUST render exclusively as plain UTF-8 text in the terminal output buffer (no escape sequences that hide text from the stream). Every ministry node, the wordmark, the subtitle, and the consent prompt MUST be legible to a terminal-mode screen reader without relying on colour or animation to convey meaning.
- **FR-026**: The REWRITE family MUST NOT regress any `PORT` row in the Epic H catalog set — specifically, `LogoV2/FeedColumn.tsx` and the 26 `design-system/*` rows (palette-only PORT) are NOT in this spec's scope but MUST remain buildable after the `tokens.ts` + `dark.ts` swap. Downstream PORT Tasks inherit the token contract without further modification (see Scope Boundaries).

### Functional Requirements — `brand-system.md` authoring

- **FR-027**: System MUST populate the Epic H-owned placeholder sections in `docs/design/brand-system.md`: § 3 (Logo usage), § 4 (Palette values), § 5 (Typography scale), § 6 (Spacing / grid), § 7 (Motion), § 9 (Iconography). Each section MUST be concrete (hex values, measurement rules, named glyphs) — no "TBD" strings remain.
- **FR-028**: System MUST leave § 8 (Voice & tone) and § 10 (Component usage guidelines) unchanged — § 8 is co-owned with Epic K #1308 and § 10 is a collaborative appendix maintained across Epics B / C / D / E / H / I / J / K / L / M.

### Key Entities

- **BrandPalette** — the closed mapping from `MetaphorRole × Variant?` to a hex value, authoritatively defined in `docs/design/brand-system.md § 4` and materialised in `tui/src/theme/dark.ts`. Fields: token name, primary hex, shimmer-variant hex (optional), ministry binding (for `agentSatellite{MINISTRY}` only), measured contrast ratio against `background` anchor.
- **OnboardingStep** — an entry in the citizen-domain step registry. Fields: step-id (`splash` | `pipa-consent` | `ministry-scope-ack` | `done`), component reference, advance-condition, skip-condition. Ordering is fixed; branching is forbidden at spec scope (re-entry is session-level, not step-level).
- **PIPAConsentRecord** — an append-only memdir USER-tier entry recording one consent decision. Fields: consent-version (string), timestamp (ISO-8601 UTC), AAL-gate (Spec 033 spectrum value). A record is never mutated after creation; a consent-version bump produces a second record.
- **MinistryScopeAcknowledgment** — a memdir USER-tier entry mapping each Phase 1 ministry to an opt-in decision. Fields: {KOROAD, KMA, HIRA, NMC} → {`opt-in`: boolean}, timestamp (ISO-8601 UTC shared across all four mappings). Updated by re-running onboarding; the prior record remains as history.
- **KosmosThemeToken** — the TypeScript type alias exported from `tui/src/theme/tokens.ts`. Fields: union of `MetaphorRole` + `SemanticRole` identifiers, each typed `string` (hex value). The type is the upstream contract consumed by every component `useTheme()` call.
- **LogoV2RewriteComponent** — a REWRITE catalog row whose target lives under `tui/src/components/onboarding/LogoV2/` or `tui/src/components/chrome/`. Each row carries: CC source path, REWRITE verdict, KOSMOS target path, token surface it consumes, accessibility-gate anchor, reduced-motion behaviour.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100 % of foreground / background colour pairs introduced or modified by this spec meet the `docs/tui/accessibility-gate.md § 7` threshold (body text ≥ 4.5 : 1, large text / non-text ≥ 3 : 1). Verified by a contrast-measurement table in `docs/design/brand-system.md § 4` listing every pair with its measured ratio.
- **SC-002**: A first-time citizen completes the full onboarding flow (splash + PIPA consent + ministry-scope-ack → main TUI) in under **90 seconds** on the happy path (all four ministries opted in).
- **SC-003**: The `tui/src/theme/tokens.ts` type surface contains **zero** occurrences of the regexes `^claude[A-Za-z0-9_]*$`, `^clawd[A-Za-z0-9_]*$`, `^briefLabelClaude$` as NEW additions in this PR's diff. Verified by the Brand Guardian grep gate.
- **SC-004**: Every completed onboarding session produces exactly **one** PIPA consent record with exactly **three** fields (version + timestamp + AAL) and exactly **one** ministry-scope acknowledgment record covering all four Phase 1 ministries.
- **SC-005**: **4 / 4** Phase 1 seed ministries (KOROAD, KMA, HIRA, NMC) are enumerated in the ministry-scope step. No Phase 2 ministry (119 NFA, Geocoding, MOHW, MOLIT, etc.) is mentioned in the UI of this spec.
- **SC-006**: The splash (LogoV2) renders without any label truncation in a **80-column** terminal and degrades to a condensed header in terminals narrower than 80 columns; below **50 columns** it degrades to a single-line text form without erroring.
- **SC-007**: With `NO_COLOR=1` or `KOSMOS_REDUCED_MOTION=1` set, every REWRITE row in FR-017 — FR-023 emits a static-text equivalent on the first frame; no shimmer, no pulse, no asterisk animation is attempted.
- **SC-008**: The eight Epic H-owned REWRITE catalog rows (31 · 32 · 33 · 35 · 36 · 37 · 45 · 162 · 165 per `docs/tui/component-catalog.md`) pass their accessibility-gate rows (WCAG + KWCAG + contrast) verified by `/speckit-analyze` with zero violations.
- **SC-009**: A tool call against a declined ministry is refused at the main-tool router with a Korean-language citizen-visible message within **100 ms** of invocation, before any outbound network call is attempted.
- **SC-010**: `docs/design/brand-system.md` § 3, § 4, § 5, § 6, § 7, § 9 are concrete at PR-merge time — zero occurrences of "TBD", "placeholder", or "Epic H (pending)" remain in those sections.
- **SC-011**: The grep gate specified in `specs/034-tui-component-catalog/contracts/grep-gate-rules.md` passes on this PR (every new `agentSatellite{MINISTRY}` identifier has a corresponding `docs/design/brand-system.md § 1` roster entry; zero BAN-01 through BAN-07 violations among newly added identifiers).
- **SC-012**: A returning citizen whose memdir USER tier already contains a valid consent record for the current consent version skips the PIPA and ministry-scope steps; onboarding completes in under **3 seconds** (splash render time only).

---

## Assumptions

- **PIPA role binding inherits from project memory.** Per `memory/project_pipa_role.md` (2026-04-19 entry), KOSMOS is a PIPA § 26 processor (수탁자) by default, with the controller-level carve-out applying only at the LLM synthesis stage. The onboarding consent prompt wording in FR-013 and FR-015 reflects this split; the plain-language Korean summary clarifies that KOSMOS forwards the citizen's request to ministry portals on their behalf.
- **`agentSatelliteMohw` → `agentSatelliteKma` substitution.** The Epic body's proposed token `agentSatelliteMOHW` names a ministry (보건복지부) that is not in `docs/design/brand-system.md § 1` ministry roster. To remain compliant with the grep gate and with the Phase 1 seed-adapter set (Spec 022 § FR-001), this spec replaces the `MOHW` label with `KMA` (기상청) and transfers the `#34d399` hex value unchanged. Should a future ADR amend § 1 to add MOHW, the ministry can be added alongside via the roster-PR mechanism (§ 2 Exceptions — Ministry satellite extensions).
- **Phase 1 ministry → accent mapping is Epic H's determination.** The § 1 roster provides semantic guidance (KOROAD = road-safety orange, etc.) which does not cleanly match the four ADR-006 A-9 splash hex values (`#34d399` mint, `#f472b6` pink, `#93c5fd` sky blue, `#c4b5fd` lavender). This spec proposes the binding {KOROAD → `#f472b6`, KMA → `#34d399`, HIRA → `#93c5fd`, NMC → `#c4b5fd`} and records the binding in § 1 + § 4. The proposed binding preserves Epic body's original KOROAD / HIRA / NMC assignments and reassigns the fourth slot from MOHW to KMA.
- **`kosmos-logo-dark.svg` is a doc-drift reference.** `docs/design/brand-system.md § 1` cross-references an `assets/kosmos-logo-dark.svg` file that does not exist on disk (the actual assets are `kosmos-logo.svg`, `kosmos-banner-dark.svg`, etc.). Because the TUI does not render SVG and the palette hex values are extracted from existing SVG sources, this spec does not require authoring the missing file. A follow-up Brand Guardian doc fix (a one-line correction in § 1) is tracked under the `brand-system-doc-fix` Deferred row below.
- **Epic H scope is narrow per the Epic body's seven-point acceptance, not per the catalog ownership breadth.** `docs/tui/component-catalog.md` lists approximately 50 rows whose "Owning Epic" column names H #1302 (design-system PORT, CustomSelect PORT, wizard REWRITE, etc.). The Epic body explicitly scopes this spec to (1) onboarding splash + PIPA + public-API-scope, (2) LogoV2 REWRITEs, (3) dark.ts / tokens.ts swap, (4) § 3/§ 4/§ 5/§ 6/§ 7/§ 9 brand-system.md authoring. The remaining palette-swap-only catalog rows inherit the token contract established here and are executed as follow-up Tasks (see Deferred Items below).
- **Shimmer-variant hex selection is a plan-phase decision.** FR-010 commits to pulling `kosmosCoreShimmer` and `orbitalRingShimmer` values from the 16-hex superset present in `assets/kosmos-logo.svg` (`#a5b4fc`, `#c7d2fe`, `#6ee7b7`, `#f9a8d4` are candidates). The specific hex for each shimmer is selected in `/speckit-plan` phase based on the measured contrast against `#0a0e27`.
- **AAL gate source is Spec 033 Permission v2 spectrum.** FR-013's AAL-gate field draws its value from the permission spectrum defined in `specs/033-permission-v2-spectrum/`. Adding an AAL value requires an amendment to Spec 033, not to this spec.
- **Memdir USER tier is Spec 027 (Agent Swarm Core) / Spec 029 (Phase 2 Adapters) infrastructure.** FR-013 / FR-016 write records into the memdir USER tier established elsewhere. This spec does not define memdir schema; it consumes the existing contract.
- **CC source commit is `a8a678c`.** The `.references/claude-code-sourcemap/restored-src/` tree reflects CC 2.1.88 at commit `a8a678c` as cited throughout `docs/tui/component-catalog.md`. Any CC-source citation in this spec MUST resolve under that commit.
- **Korean label conventions.** Citizen-facing Korean labels (`최근 세션`, `부처 상태`, `KOSMOS에 오신 것을 환영합니다`, ministry names) are final at spec scope. Minor copy edits are allowed in the plan / implement phases provided they do not alter the meaning or break a screen-reader narration.

---

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **Light and high-contrast themes.** Phase 1 ships the `dark` theme only. The `light.ts` / `default.ts` modules in `tui/src/theme/` remain stubs; any citizen-facing theme choice surfaces are permanently out of scope for Epic H.
- **SVG-to-terminal rendering.** The TUI is Ink + React + Bun over a character grid; SVG assets are consumed as colour sources, not rendered. Any proposal to render the KOSMOS SVG logo as a terminal image is permanently out of scope (no `kitty-image-protocol` integration, no `term-img`).
- **Sound / voice feedback during onboarding.** KOSMOS has no audio subsystem (§ 8 Voice & tone concerns prose, not audible voice). Adding audio cues to the splash or consent step is permanently out of scope.
- **Browser or mobile equivalent.** KOSMOS is terminal-only; an "onboarding web page" or "mobile splash" is permanently out of scope (AGENTS.md hard rule — TypeScript is allowed only for the TUI layer).

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Theme picker (light + high-contrast + citizen-chosen theme) | Phase 1 ships `dark` only per Epic body acceptance # 4 | Epic K #1308 — Settings surface | #1308 |
| `design-system/*` palette-swap-only PORT (26 rows) | Depends on the token contract landing first; pure palette-swap work is a follow-up Task once `tokens.ts` + `dark.ts` are stable | Epic H #1302 follow-up spec OR Epic M #1310 depending on catalog ownership decision | #1538 |
| `CustomSelect/*` palette-swap-only PORT (10 rows) | Same as above — depends on token contract | Epic H #1302 follow-up spec OR Epic M #1310 | #1539 |
| `wizard/*` REWRITE (4 rows) | Catalog Epic H-owned but not required for the citizen onboarding flow specified here; `wizard/*` is a generic step-container used by future settings / config flows, not by the 3-step onboarding in FR-012 | Epic H #1302 follow-up spec | #1540 |
| `TagTabs.tsx` PORT (catalog row 155) | Catalog Epic H-owned palette-swap; not touched by the Onboarding / LogoV2 / token contract surface | Epic H #1302 follow-up spec | #1541 |
| Full mass-rename of the 69 legacy CC-branded tokens in `tokens.ts` allow-list | Epic M `.brand-guardian-allowlist.txt` tracks this under Deferred row 10; this spec only introduces the 10 KOSMOS additions and 7 CC deletes, not the 69-token mass rename | Epic M #1310 Deferred row 10 | #1542 |
| `brand-system.md § 8 Voice & tone` authoring | Co-owned with Epic K #1308 (Settings); Epic K authors the § 8 prose once the Settings surface (language/locale) is defined | Epic K #1308 | #1308 |
| `brand-system.md § 10 Component usage guidelines` appendix | Collaborative appendix; each downstream Epic appends its H3 subheading when shipping | Epics B / C / D / E / H / I / J / K / L / M — ongoing | #1310 (anchor) |
| `agentSatellite119Nfa`, `agentSatelliteGeocoding`, `agentSatelliteMohw`, other MOLIT / KOGL ministry tokens | Phase 2 adapter roster; added as each adapter ships under its own Epic with a § 1 roster PR | Phase 2 adapter Epics (e.g. `specs/029-phase2-adapters-119-mohw/` and successors) | #1543 |
| `brand-system.md § 1` doc-fix: replace `kosmos-logo-dark.svg` cross-reference with an existing file name | Single-line doc fix bundled into Epic H PR — resolved inline (tasks.md T036) | Epic H #1302 (this spec) | Resolved inline — tasks.md T036 |
| Deep ARIA-style role / name / value conformance (WCAG 4.1.2) for the Ink virtual DOM | Terminal-mode screen readers consume the text stream, not a DOM accessibility tree; deep compliance is deferred platform-wide | Issue #25 (`4.1.2 Name Role Value — deep compliance`) | #25 |
