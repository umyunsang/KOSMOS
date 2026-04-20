---
description: "Phase 2 task list for Epic H #1302 — Onboarding + brand port"
---

# Tasks: Onboarding + Brand Port

**Feature**: Epic H [#1302 — Onboarding + brand port (binds ADR-006 A-9)](https://github.com/umyunsang/KOSMOS/issues/1302)
**Branch**: `035-onboarding-brand-port`
**Input**: Design documents from `/specs/035-onboarding-brand-port/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Test tasks are included because every spec user story declares an "Independent Test" block and because `contracts/*.md § Traceability` rows bind each FR to a named test artefact. TDD discipline per `superpowers:test-driven-development` applies.

**Task budget**: 52 tasks (≤ 90 per AGENTS.md Sub-Issue 100-cap; reserves 38 slots for `[Deferred]` placeholders + mid-cycle additions).

**Format**: `[ID] [P?] [Story?] Description`
- **[P]**: different file, no dependency on another incomplete task.
- **[Story]**: `[US1]`–`[US5]` maps to `spec.md § User Scenarios`. Setup / Foundational / Polish carry no story label.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Pre-work that every downstream task consumes.

- [X] T001 Create new component + hook directories: `tui/src/components/onboarding/`, `tui/src/components/onboarding/LogoV2/`, `tui/src/components/chrome/`, `tui/src/hooks/`, `tui/src/memdir/`, and the test mirrors `tui/tests/onboarding/`, `tui/tests/LogoV2/`, `tui/tests/theme/`, `tui/tests/memdir/`; Python side `tests/memdir/` + ensure `src/kosmos/memdir/` exists with an importable `__init__.py` re-exporting the two new modules introduced in later tasks (empty stubs acceptable at this task).
- [X] T002 [P] Create `tui/src/hooks/useReducedMotion.ts` — reads `process.env.NO_COLOR` and `process.env.KOSMOS_REDUCED_MOTION`, returns `{ prefersReducedMotion: boolean }`. Pattern mirrors Spec 287's `useKoreanIME`. Consumed by FR-024 components (AnimatedAsterisk, LogoV2, orbitalRing shimmer). Reference: `plan.md § Phase 0 R-8`.
- [X] T003 [P] Scaffold `scripts/compute-contrast.mjs` (Bun-executable, stdlib only — zero dependency) with CLI shape: reads `tui/src/theme/dark.ts`, iterates the pair matrix defined in `contracts/contrast-measurements.md § 2`, writes Markdown table. Implementation body in T045; this task lands the file stub + the pair-matrix constant. Reference: `contracts/contrast-measurements.md § 1` WCAG formula.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Theme contract (tokens.ts + dark.ts) is the compile-time foundation every downstream story consumes. No US phase may begin until this phase is green.

**CRITICAL**: A TypeScript compile failure here fails every downstream snapshot and Ink build.

- [X] T004 Update `tui/src/theme/tokens.ts` — DELETE the 7 identifiers from `contracts/brand-token-surface.md § 1` (`claude`, `claudeShimmer`, `claudeBlue_FOR_SYSTEM_SPINNER`, `claudeBlueShimmer_FOR_SYSTEM_SPINNER`, `clawd_body`, `clawd_background`, `briefLabelClaude`); ADD the 10 identifiers from § 2 (`kosmosCore`, `kosmosCoreShimmer`, `orbitalRing`, `orbitalRingShimmer`, `wordmark`, `subtitle`, `agentSatelliteKoroad`, `agentSatelliteKma`, `agentSatelliteHira`, `agentSatelliteNmc`); append the FR-008 header comment `// KOSMOS 브랜드 토큰으로 리네이밍됨 (ADR-006 A-9)` directly beneath the existing `// Source:` line. Satisfies FR-005, FR-006, FR-008.
- [X] T005 Update `tui/src/theme/dark.ts` — REPLACE `background: 'rgb(0,204,204)'` with `'rgb(10,14,39)'` per § 3; ADD the 10 new `rgb(...)` bindings from § 2 table (primary hex → rgb form); raise any preserve-set token whose new contrast against `#0a0e27` falls below threshold (deferred measurement to T045); append the same FR-008 header comment. Satisfies FR-009, FR-010, FR-011, FR-008.
- [X] T006 [P] Create `tui/tests/theme/tokens.compile.test.ts` — Bun compile-time assertion: zero occurrences of the 7 DELETE identifiers in `ThemeToken`; exactly the 10 ADD identifiers present; preserve-set cardinality matches `contracts/brand-token-surface.md § 4` (62). Fails the build if the type surface drifts. Satisfies SC-003.

**Checkpoint**: `bun tsc --noEmit` passes on `tui/` with zero errors. Every downstream story can now begin.

---

## Phase 3: User Story 1 — Citizen sees the KOSMOS orbital-ring splash on first launch (Priority: P1) 🎯 MVP

**Goal**: Fresh-launch TUI renders the splash composition — KOSMOS wordmark, subtitle, orbital-ring, kosmosCore asterisk, 4 ministry satellite nodes, navy `#0a0e27` background — replacing the CC `rgb(0,204,204)` placeholder and CC "Welcome to Claude Code" wordmark. Covers FR-017 through FR-025 for splash-rendering surface.

**Independent Test**: Launch the TUI on a fresh machine. Frame 1 MUST show wordmark "KOSMOS" on `#0a0e27` navy, orbital-ring composition, and 4 satellite nodes. `LogoV2.snap.test.tsx` snapshot passes at 80/60/45 col breakpoints with reduced-motion on/off.

### Implementation for User Story 1

- [X] T007 [P] [US1] REWRITE `tui/src/components/onboarding/LogoV2/AnimatedAsterisk.tsx` — render U+002A asterisk in `kosmosCore` token with shimmer cycle to `kosmosCoreShimmer` at 6 fps; gate animation on `!useReducedMotion().prefersReducedMotion`; remove CC teardrop glyph and `chromeYellow` binding. Props: `{ width?: number; height?: number; prefersReducedMotion?: boolean }`. Reference: `contracts/logov2-rewrite-visual-specs.md § 1`.
- [X] T008 [P] [US1] REWRITE `tui/src/components/onboarding/LogoV2/CondensedLogo.tsx` — one-line header `<KosmosCoreIcon/> KOSMOS — <model> · <effort> · <coordinatorMode>` in `wordmark` on `background`; props `{ model?; effort?; coordinatorMode? }`; delete CC Clawd poses, GuestPassesUpsell, referral strings. Reference: `contracts/logov2-rewrite-visual-specs.md § 2`.
- [X] T009 [P] [US1] PORT `tui/src/components/onboarding/LogoV2/FeedColumn.tsx` — verbatim token-only swap from CC source (`.references/claude-code-sourcemap/restored-src/src/components/LogoV2/FeedColumn.tsx`); consumes `text` + `subtle` semantic slots (no rename needed). No structural changes. Reference: `contracts/logov2-rewrite-visual-specs.md § 4`.
- [X] T010 [P] [US1] REWRITE `tui/src/components/onboarding/LogoV2/feedConfigs.tsx` — export `createKosmosSessionHistoryFeed(sessions) → FeedConfig` + `createMinistryAvailabilityFeed(status) → FeedConfig`; delete CC's 5 feed factories (`createRecentActivityFeed`, `createWhatsNewFeed`, `createProjectOnboardingFeed`, `createGuestPassesFeed`, `createOverageCreditFeed`). Reference: `contracts/logov2-rewrite-visual-specs.md § 5`.
- [X] T011 [P] [US1] REWRITE `tui/src/components/onboarding/LogoV2/WelcomeV2.tsx` — `KOSMOS에 오신 것을 환영합니다 vN.N.N` wordmark + kosmosCore asterisk cluster; delete Apple-Terminal-specific ASCII art and CC "Welcome to Claude Code" copy; retain only dark theme branch. Reference: `contracts/logov2-rewrite-visual-specs.md § 7`.
- [X] T012 [P] [US1] REWRITE `tui/src/components/chrome/KosmosCoreIcon.tsx` (NEW file, CC source `FastIcon.tsx`) — emit `*` glyph in `kosmosCore`, shimmer to `kosmosCoreShimmer` when `shimmering && !useReducedMotion()`; props `{ shimmering?: boolean }`. Satisfies FR-023. Reference: `contracts/logov2-rewrite-visual-specs.md § 8`.
- [X] T013 [US1] REWRITE `tui/src/components/onboarding/LogoV2/Feed.tsx` — composes `<FeedColumn>` × 2: left "최근 세션" bound to memdir Session tier (via `createKosmosSessionHistoryFeed`), right "부처 상태" bound to Spec 022 adapter registry (via `createMinistryAvailabilityFeed`); ministry names coloured with `agentSatellite{MINISTRY}` accents; availability indicator `●`/`○`. Depends on T009 + T010. Reference: `contracts/logov2-rewrite-visual-specs.md § 3`.
- [X] T014 [US1] Create `tui/src/components/onboarding/LogoV2/logoV2Utils.ts` — PORT `getLayoutMode` + `calculateLayoutDimensions` + `calculateOptimalLeftWidth` + `formatWelcomeMessage` verbatim from CC `restored-src/src/utils/logoV2Utils.ts`; REWRITE `getRecentActivitySync → getKosmosSessionHistorySync` reading memdir Session tier; REWRITE `getRecentReleaseNotesSync → getMinistryAvailabilitySync` reading Spec 022 registry; DISCARD `getLogoDisplayData` (Anthropic-branded). Reference: `plan.md § Phase 0 R-7`.
- [X] T015 [US1] REWRITE `tui/src/components/onboarding/LogoV2/LogoV2.tsx` — compose splash per `contracts/logov2-rewrite-visual-specs.md § 6`: wordmark + subtitle + orbitalRing arc + `<AnimatedAsterisk/>` + 4 satellite nodes + `<Feed>`; mode switch `full` (≥ 80 col) / `condensed` (< 80 col via `<CondensedLogo>`) / fallback (< 50 col single-line `KOSMOS — 한국 공공서비스 대화창`); banned imports compile-time excluded (`Clawd`, `AnimatedClawd`, `ChannelsNotice`, `GuestPassesUpsell`, `EmergencyTip`, `VoiceModeNotice`, `Opus1mMergeNotice`, `OverageCreditUpsell`). Depends on T007–T014.
- [X] T016 [US1] Create `tui/src/components/onboarding/Onboarding.tsx` skeleton — step registry per `contracts/onboarding-step-registry.md § 1` with 4 entries (`splash` wired to `<LogoV2/>`; `pipa-consent` + `ministry-scope-ack` as placeholder `<Text>pending</Text>` components to be replaced in T022/T030; `done` passthrough); `CURRENT_CONSENT_VERSION = "v1"` + `CURRENT_SCOPE_VERSION = "v1"` constants; `resolveStartStep(memdir)` session-start resolver per § 3; Enter / Escape / Ctrl+C / Ctrl+D keybinding table per § 2 with `useApp().exit()` on Escape; IME-gated via `!useKoreanIME().isComposing`; `kosmos.onboarding.step` OTEL span emission (Spec 021).
- [X] T017 [US1] Create `tui/tests/LogoV2/LogoV2.snap.test.tsx` — snapshot matrix: `{ 80, 60, 45 } × { prefersReducedMotion: true, false }` = 6 snapshots; asserts banned-import grep returns zero hits on rendered component output. Verifies SC-006 + SC-007 for the splash component.
- [X] T018 [P] [US1] Create `tui/tests/LogoV2/AnimatedAsterisk.snap.test.tsx` — 2 snapshots (shimmering frame @ t=0, reduced-motion static); verifies FR-018 + FR-024.

**Checkpoint**: `bun test tui/tests/LogoV2/LogoV2.snap.test.tsx` + `AnimatedAsterisk.snap.test.tsx` pass. US1 splash renders end-to-end with the Onboarding placeholder shell.

---

## Phase 4: User Story 2 — Citizen records PIPA consent with version, timestamp, AAL (Priority: P1)

**Goal**: Onboarding's second step renders PIPA consent UI, writes an append-only `PIPAConsentRecord` to `~/.kosmos/memdir/user/consent/` on accept, exits cleanly on decline. Covers FR-012 (scoped to pipa step), FR-013, FR-014.

**Independent Test**: Fresh session → accept PIPA → verify one JSON record exists in memdir with `consent_version=v1` + UTC timestamp + `aal_gate=AAL1` + UUIDv7 `session_id` + `citizen_confirmed=true` + `schema_version="1"`. Decline → session exits, no file written.

### Implementation for User Story 2

- [X] T019 [US2] Create `src/kosmos/memdir/user_consent.py` — Pydantic v2 `PIPAConsentRecord(frozen=True, extra="forbid")` per `contracts/memdir-consent-schema.md § 2`; `latest_consent(base: Path) → PIPAConsentRecord | None` reader that scans `base.glob("*.json")` descending, skips validation failures; `write_consent_atomic(record, base)` implementing the § 4 tmp + `fsync` + `os.rename` pattern; imports `AuthenticatorAssuranceLevel` from `kosmos.permissions` (Spec 033). Exported from `src/kosmos/memdir/__init__.py`.
- [X] T020 [P] [US2] Create `tui/src/memdir/consent.ts` — Zod mirror `PIPAConsentRecordSchema` per § 3; exports `type PIPAConsentRecord = z.infer<typeof ...>`; runtime validator consumed by `PIPAConsentStep` on accept.
- [X] T021 [US2] Create `tui/src/components/onboarding/PIPAConsentStep.tsx` — renders consent version, PIPA § 26 수탁자 plain-language Korean summary, enumerated ministry recipient list, current AAL gate (`AAL1` → "기본 인증 단계"); Enter → construct + validate `PIPAConsentRecord` via Zod → IPC write to Python side (atomic write through stdio JSONL per Spec 032) → `onAdvance()`; Escape → `onExit()`; IME-gated per `contracts/onboarding-step-registry.md § 2`. Props `{ onAdvance; onExit }`. Satisfies FR-012 pipa-step + FR-013 + FR-014.
- [X] T022 [US2] Update `tui/src/components/onboarding/Onboarding.tsx` — replace placeholder `pipa-consent` step with real `<PIPAConsentStep>`; wire `exitSideEffect: "write-consent-record"` to trigger consent-record write via the stdio IPC path; handle `consent_version` mismatch bump by forcing re-render per research R-6.
- [X] T023 [US2] Create `tests/memdir/test_user_consent.py` — `test_schema_roundtrip` (model_dump → model_validate_json), `test_append_only` (two writes → two files, neither overwritten), `test_latest_consent` (returns most recent valid record, skips corrupt), `test_decline_writes_nothing` (negative path — no side effect when `citizen_confirmed=False` validation blocks write). Covers I-9, I-10, I-11, I-12.
- [X] T024 [P] [US2] Create `tui/tests/memdir/consent.zod.test.ts` — asserts Zod schema accepts valid record, rejects missing `citizen_confirmed`, rejects non-UTC timestamp (`+09:00` offset form), rejects `consent_version` not matching `/^v\d+$/`. Mirrors `test_user_consent.py` at TS layer.
- [X] T025 [P] [US2] Create `tui/tests/onboarding/PIPAConsentStep.snap.test.tsx` — 3 snapshots: (a) initial render showing consent version + Korean § 26 summary + AAL, (b) accept branch (record-write side effect mocked, `onAdvance` called once), (c) decline branch (`onExit` called once, no write-record mock invoked).

**Checkpoint**: `uv run pytest tests/memdir/test_user_consent.py` + `bun test tui/tests/onboarding/PIPAConsentStep.snap.test.tsx` pass. US2 record write + decline branches proven independently testable.

---

## Phase 5: User Story 3 — Citizen opts in to Phase 1 ministry API scopes (Priority: P1)

**Goal**: Third onboarding step enumerates KOROAD / KMA / HIRA / NMC with Korean names + accent colours + opt-in toggles; writes `MinistryScopeAcknowledgment` record; main-tool router refuses declined-ministry tool calls pre-network in < 100 ms. Covers FR-015, FR-016, SC-005, SC-009.

**Independent Test**: Complete onboarding with KOROAD+KMA selected, HIRA+NMC declined. Verify scope record lists all 4 with correct `opt_in` booleans. Attempt a HIRA-prefixed tool call via `resolve_with_scope_guard` → raises `MinistryOptOutRefusal` with Korean message in < 100 ms.

### Implementation for User Story 3

- [X] T026 [US3] Create `src/kosmos/memdir/ministry_scope.py` — Pydantic v2 `MinistryOptIn(frozen=True, extra="forbid")` + `MinistryScopeAcknowledgment(frozen=True, extra="forbid")` per `contracts/memdir-ministry-scope-schema.md § 2`; `@model_validator(mode="after") _check_four_unique` enforcing exactly `{KOROAD, KMA, HIRA, NMC}`; `latest_scope(base)` reader + `write_scope_atomic` writer mirroring the consent pattern. Exported from `src/kosmos/memdir/__init__.py`. Covers I-13, I-14, I-15.
- [X] T027 [P] [US3] Create `tui/src/memdir/ministry-scope.ts` — Zod mirror `MinistryOptInSchema` + `MinistryScopeAcknowledgmentSchema` per § 3, including the `.refine` predicates enforcing 4-unique + full coverage of the 4 codes.
- [X] T028 [US3] Extend `src/kosmos/tools/main_router.py` — add `MINISTRY_TOOL_PREFIX: dict[str, MinistryCode]` (`{koroad_: KOROAD, kma_: KMA, hira_: HIRA, nmc_: NMC}`); `_ministry_for_tool(tool_id)` + `_ministry_korean_name(code)` helpers per `contracts/memdir-ministry-scope-schema.md § 5–§ 6`; `MinistryOptOutRefusal(Exception)` typed exception with `ministry: MinistryCode` + `message: str`; `resolve_with_scope_guard(tool_id, params, memdir_root)` fail-closed refusal when `latest_scope()` returns `None` OR the matching `MinistryOptIn.opt_in is False`. Raise MUST complete before any outbound HTTP — verified in T033 with explicit timing assertion.
- [X] T029 [US3] Create `tui/src/components/onboarding/MinistryScopeStep.tsx` — 4 toggle rows (KOROAD / KMA / HIRA / NMC) each showing `<Korean-name> (<English-code>)` per research R-9 + one-line Korean description + `agentSatellite{MINISTRY}` accent; default "all four" aggregate affordance; ↑/↓ moves selection, Space toggles current, Enter confirms all + triggers scope-record write via IPC; Escape → `onExit()`. Props `{ onAdvance; onExit }`. Satisfies FR-015, FR-016.
- [X] T030 [US3] Update `tui/src/components/onboarding/Onboarding.tsx` — replace placeholder `ministry-scope-ack` step with real `<MinistryScopeStep>`; wire `exitSideEffect: "write-scope-record"`; ensure `session_id` used for scope record MATCHES the consent record written in T022 (binds X-2 cross-entity invariant); resolver per § 3 now branches `consentFresh && !scopeFresh → ministry-scope-ack`.
- [X] T031 [US3] Create `tests/memdir/test_ministry_scope.py` — `test_schema_roundtrip`, `test_four_unique` (rejects 3-item or 5-item ministries), `test_duplicate_codes_rejected` (frozenset-level), `test_append_only`, `test_latest_scope`. Covers I-13 through I-16.
- [X] T032 [P] [US3] Create `tui/tests/memdir/ministry-scope.zod.test.ts` — mirrors T031 assertions at TS layer including the `.refine` predicate tests.
- [X] T033 [US3] Create `tests/tools/test_main_router.py` — `test_opt_out_refusal` (declined ministry → `MinistryOptOutRefusal` raised; elapsed `time.perf_counter()` < 100 ms per SC-009; Korean message snapshot matches `{ministry_korean}의 데이터 사용에 동의하지 않으셨습니다...`); `test_opt_in_success` (opted-in ministry call passes through `resolve()`); `test_no_scope_record_refuses_all` (fail-closed default); `test_non_ministry_tool_bypasses_guard`. Covers X-3.
- [X] T034 [P] [US3] Create `tui/tests/onboarding/MinistryScopeStep.snap.test.tsx` — 3 snapshots: initial 4-row render, partial opt-in selection (KOROAD+KMA only), all-declined terminal state.
- [X] T035 [US3] Create `tui/tests/onboarding/Onboarding.snap.test.tsx` — full 3-step happy-path snapshot (`splash → pipa-consent → ministry-scope-ack → done`); escape-exit branch at each step (verifies FR-014 from each origin); returning-citizen fast-path snapshot (memdir pre-populated with `v1` records → splash-only path). Covers FR-012 end-to-end + SC-002 + SC-012.

**Checkpoint**: `uv run pytest tests/memdir/ tests/tools/test_main_router.py` + `bun test tui/tests/onboarding/` all pass. SC-009 < 100 ms refusal proven in T033. All three P1 stories independently testable.

---

## Phase 6: User Story 4 — Brand Guardian reads a coherent KOSMOS token type surface (Priority: P2)

**Goal**: Engineers + Brand Guardian observe that `tokens.ts` + `dark.ts` carry KOSMOS metaphor identifiers + header comments, and that the grep gate rejects any reintroduction of `claude*` / `clawd_*` / `briefLabelClaude` identifiers. Covers FR-005 through FR-008 (verification tier; core mutations done in Phase 2 Foundational).

**Independent Test**: Run Brand Guardian grep gate on this branch → PASS with 10 new tokens recognised and zero BAN violations. Run `tokens.compile.test.ts` + header-comment assertion → both green.

### Implementation for User Story 4

- [X] T036 [US4] Update `docs/design/brand-system.md § 1 Brand metaphor` — (a) confirm/add the 4 `MinistryCode` roster entries (`Koroad`, `Kma`, `Hira`, `Nmc`) required by the grep gate for the new `agentSatellite*` tokens; (b) replace the broken cross-reference `assets/kosmos-logo-dark.svg` with `assets/kosmos-banner-dark.svg` per research R-10; (c) add ministry-to-accent binding table `{KOROAD → #f472b6, KMA → #34d399, HIRA → #93c5fd, NMC → #c4b5fd}` cross-referenced from § 4. Satisfies FR-004.
- [X] T037 [US4] Run the Brand Guardian grep gate (`specs/034-tui-component-catalog/contracts/grep-gate-rules.md § 4`) against this branch's diff of `tui/src/theme/**` + `tui/src/components/**`; capture the PASS output into `specs/035-onboarding-brand-port/artifacts/grep-gate-run.txt` (new file); if any BAN-01…BAN-07 violation surfaces on a newly added identifier, fix the identifier and re-run. Satisfies SC-011.
- [X] T038 [P] [US4] Create `tui/tests/theme/header-comment.test.ts` — reads `tui/src/theme/tokens.ts` + `tui/src/theme/dark.ts` file bodies, asserts each contains both the `// Source: .references/...` line AND the `// KOSMOS 브랜드 토큰으로 리네이밍됨 (ADR-006 A-9)` line per `contracts/brand-token-surface.md § 5`. Satisfies I-20 + FR-008.

**Checkpoint**: Grep gate green, compile test green, header-comment test green. Token contract locked for downstream PORT Tasks.

---

## Phase 7: User Story 5 — TUI renders the LogoV2 REWRITE family with the KOSMOS metaphor (Priority: P2)

**Goal**: Each Epic H-owned catalog row (31 / 32 / 33 / 35 / 36 / 37 / 45 / 154 / 156) has a working REWRITE/PORT target, a passing snapshot, a zero-CC-import compile-time guarantee, and a green `[ag-logov2] / [ag-onboarding] / [ag-logo-wordmark]` accessibility-gate annotation. Quality-bar verification layer on top of US1 components.

**Independent Test**: Every LogoV2 / chrome component has a corresponding snapshot file under `tui/tests/LogoV2/` that passes; accessibility-gate.md § 3 rows are annotated `SHIPPED-Epic-H`; a greppable scan for banned CC identifiers in the rendered output of each component returns zero hits.

### Implementation for User Story 5

- [X] T039 [US5] Create `tui/tests/LogoV2/CondensedLogo.snap.test.tsx` — snapshot with mock `{model: "K-EXAONE", effort: "normal", coordinatorMode: "default"}`; asserts wordmark = "KOSMOS", zero "Claude" / "Clawd" / "GuestPasses" strings in rendered output. Verifies FR-019.
- [X] T040 [P] [US5] Create the Feed family test trio `tui/tests/LogoV2/{Feed,FeedColumn,feedConfigs}.test.tsx` — (i) `Feed.snap.test.tsx` 2-column render with mock sessionHistory + ministryStatus, (ii) `FeedColumn.snap.test.tsx` primitive PORT (generic layout), (iii) `feedConfigs.test.tsx` unit tests for `createKosmosSessionHistoryFeed` + `createMinistryAvailabilityFeed` factory output shape. Verifies FR-021 + FR-022. Cohesion-merge per tasks-skill rule (same test-subdir + same verb).
- [X] T041 [P] [US5] Create `tui/tests/LogoV2/WelcomeV2.snap.test.tsx` — Korean welcome header "KOSMOS에 오신 것을 환영합니다" + kosmosCore cluster render; zero Apple-Terminal ASCII art in output. Verifies FR-020.
- [X] T042 [P] [US5] Create `tui/tests/LogoV2/KosmosCoreIcon.snap.test.tsx` — 2 snapshots (shimmering vs. static); zero "FastIcon" / "chromeYellow" / lightning-glyph references. Verifies FR-023 + I-22.
- [X] T043 [US5] Create `tui/tests/LogoV2/banned-imports.compile.test.ts` — static source-scan of every file in `tui/src/components/onboarding/LogoV2/**` + `tui/src/components/chrome/KosmosCoreIcon.tsx` + `tui/src/components/onboarding/Onboarding.tsx`; asserts zero matches of the regex `/(?:^|\W)(Clawd|AnimatedClawd|GuestPassesUpsell|EmergencyTip|VoiceModeNotice|Opus1mMergeNotice|ChannelsNotice|OverageCreditUpsell)(?:$|\W)/m`. Fails build on any reintroduction. Satisfies I-22.
- [X] T044 [US5] Update `docs/tui/accessibility-gate.md § 3` rows 31 / 32 / 33 / 35 / 36 / 37 / 45 / 154 / 156 — annotate status `SHIPPED-Epic-H` with PR link placeholder; update § 7 handoff note to acknowledge Epic H's measured contrast ratios (populated by T046). Satisfies SC-008 + the component-catalog Epic H row closure.

**Checkpoint**: `bun test tui/tests/LogoV2/` all pass. Catalog rows + a11y-gate annotations show SHIPPED. Component-catalog Epic H rows reconciled.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Populate brand-system.md sections, run contrast measurement, update catalog + accessibility-gate docs, execute full quickstart.md validation.

- [X] T045 Implement `scripts/compute-contrast.mjs` body — parse `rgb(r,g,b)` literals from `tui/src/theme/dark.ts`, compute WCAG 2.1 relative-luminance + contrast ratio per `contracts/contrast-measurements.md § 1` formula, iterate the full pair matrix from § 2 (11 body-text + 4 non-text + 2 diff pairs = 17 pairs), emit the Markdown table to `docs/design/contrast-measurements.md`, exit non-zero on any threshold failure. Uses Bun + stdlib only (no new deps per research R-3).
- [X] T046 Run `bun run scripts/compute-contrast.mjs` → create `docs/design/contrast-measurements.md` with populated ratios; if any pair fails, raise the failing token's value in `dark.ts` per `contracts/contrast-measurements.md § 3` remediation contract (raise-only) and re-run until all 17 pairs PASS. Satisfies SC-001 + SC-010.
- [X] T047 Populate `docs/design/brand-system.md § 3 Logo usage` + § 5 Typography scale + § 6 Spacing/grid — § 3 cites `assets/kosmos-banner-dark.svg` + wordmark clear-space rule; § 5 enumerates Hangul-safe monospace stack per research R-9 (Spec 287 `stringWidth` precedent); § 6 documents 1-cell vs 2-cell Hangul-syllable spacing rules for terminal grid. Zero "TBD" / "placeholder" strings remain. Cohesion-merge (same file + same deliverable type).
- [X] T048 Populate `docs/design/brand-system.md § 4 Palette values` — full table: token name, primary hex, shimmer variant, ministry binding, measured contrast ratio (from T046), `background` pair column. Cross-reference `docs/design/contrast-measurements.md` for authoritative ratios. Covers FR-002 + FR-003.
- [X] T049 Populate `docs/design/brand-system.md § 7 Motion` + § 9 Iconography — § 7 documents 6 fps shimmer frame budget + `useReducedMotion` contract + `NO_COLOR` equivalence per research R-8; § 9 documents the U+002A `*` glyph + kosmosCore asterisk cluster spec + Korean-safe fallback glyph policy. Zero "TBD" remains. Cohesion-merge. Satisfies FR-027.
- [X] T050 Update `docs/tui/component-catalog.md` rows 31 / 32 / 33 / 35 / 36 / 37 / 45 / 154 / 156 — status `SHIPPED-Epic-H`, PR link placeholder, port-vs-rewrite verdict matches `contracts/logov2-rewrite-visual-specs.md § 10` matrix. Completes Epic H row closure.
- [X] T051 Run the Phase 1–6 quickstart validation from `specs/035-onboarding-brand-port/quickstart.md § 1–§ 13` (skip § 14 manual VoiceOver); record results (PASS/FAIL per step) in `specs/035-onboarding-brand-port/artifacts/quickstart-run.md` (new file); if any step fails, file a Task issue for remediation rather than inline-fixing (preserves checkpoint boundaries).
- [X] T052 Tick every box in `specs/035-onboarding-brand-port/quickstart.md § 15 CI gate checklist` — verify `bun test` + `uv run pytest` + contrast script + grep gate + brand-system.md placeholder scan + contrast-measurements.md existence + accessibility-gate § 7 handoff + snapshot-file pairing. Open the Epic H PR only when every box ticks. Final Phase 8 exit criterion.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies; can start immediately.
- **Foundational (Phase 2)**: depends on Phase 1. BLOCKS every user story.
- **User Stories (Phase 3+)**: all depend on Phase 2 (theme contract).
  - US1 (P1) → US2 (P1) → US3 (P1) may proceed sequentially OR US1 parallel with US2+US3 if Onboarding.tsx placeholder contract from T016 is respected.
  - US4 (P2) is mostly verification — can start any time after T004 + T005 land.
  - US5 (P2) verification depends on US1 components existing.
- **Polish (Phase 8)**: depends on all 5 user stories complete; T045/T046 may start after Phase 2.

### User-story-level dependency graph

```
Phase 2 ──┬──▶ US1 ──┬──▶ US2 ──▶ US3 ──▶ Phase 8
          │          │
          │          └──▶ US5 (verification, parallel with US2/US3)
          │
          └──▶ US4 (verification, parallel with everything)
```

### Parallel Opportunities (explicit [P] tasks)

Phase 1: T002 || T003
Phase 2: T006 runs after T004+T005 land; no intra-phase parallelism (both file mutations precede it).
Phase 3 (US1): T007 || T008 || T009 || T010 || T011 || T012 (6-way parallel LogoV2 REWRITE). Then T013 after T009+T010, T014 independently, T015 after all, T016 after T015, T017 serial, T018 [P] with T017.
Phase 4 (US2): T020 || T024 || T025 (3-way parallel tests + Zod mirror).
Phase 5 (US3): T027 || T032 || T034 (3-way parallel).
Phase 6 (US4): T038 runs in parallel with T036+T037.
Phase 7 (US5): T040 || T041 || T042 (3-way parallel snapshot tests).

### The 6-way LogoV2 parallel swarm (T007–T012)

Per user's Epic H guidance (`parallel-safe 라벨 후보: 9 LogoV2 REWRITE 파일`), the 9 catalog rows decompose into:

- **Independent** (pure leaf files, `[P]`): T007 AnimatedAsterisk, T008 CondensedLogo, T009 FeedColumn, T010 feedConfigs, T011 WelcomeV2, T012 KosmosCoreIcon → **6-way Agent Team parallel**.
- **Dependent** (single file, serial after leaves): T013 Feed (needs FeedColumn + feedConfigs), T014 logoV2Utils (leaf, could also be [P] but already low-priority), T015 LogoV2.tsx (needs all).

Recommended Agent Teams staffing at `/speckit-implement`: Frontend Developer × 6 in parallel for T007–T012, then Frontend Developer × 1 for T013–T015 sequentially.

---

## Parallel Example: LogoV2 REWRITE swarm (US1)

```bash
# Launch all 6 leaf-level LogoV2 REWRITE tasks together:
Task: "REWRITE tui/src/components/onboarding/LogoV2/AnimatedAsterisk.tsx per contracts/logov2-rewrite-visual-specs.md § 1"
Task: "REWRITE tui/src/components/onboarding/LogoV2/CondensedLogo.tsx per § 2"
Task: "PORT tui/src/components/onboarding/LogoV2/FeedColumn.tsx per § 4"
Task: "REWRITE tui/src/components/onboarding/LogoV2/feedConfigs.tsx per § 5"
Task: "REWRITE tui/src/components/onboarding/LogoV2/WelcomeV2.tsx per § 7"
Task: "REWRITE tui/src/components/chrome/KosmosCoreIcon.tsx per § 8"
```

---

## Implementation Strategy

### MVP scope (US1 alone)

1. Phase 1 → Phase 2 (theme contract) → Phase 3 (US1 splash) → Phase 8 T051–T052 partial.
2. **STOP + VALIDATE**: launch TUI, confirm splash renders; consent + scope flow not yet wired (Onboarding.tsx placeholders) but the SC-006 + SC-007 + SC-008 splash criteria are measurable.
3. This MVP is demoable to KSC 2026 reviewers as "KOSMOS brand visible on fresh TUI launch".

### Incremental P1 delivery

4. Add US2 → consent record written on accept (SC-004 half) → demo-ready.
5. Add US3 → ministry-scope record + router refusal < 100 ms (SC-009, SC-005) → all three P1 stories testable independently.

### P2 quality-bar delivery

6. Add US4 → grep gate + header-comment + tokens compile test green.
7. Add US5 → all 9 LogoV2 rows SHIPPED-Epic-H.
8. Phase 8 polish → brand-system.md populated + contrast measurements published + catalog reconciled.

### Agent Teams staffing (at /speckit-implement)

- Phase 3 T007–T012: 6× Frontend Developer (Sonnet) in parallel.
- Phase 4 T019 + T021 + T022: Backend Architect + Frontend Developer sequential.
- Phase 5 T026 + T028 + T029: Backend Architect (memdir + router) + Frontend Developer (MinistryScopeStep) parallel.
- Phase 8 T045 + T046: Backend Architect for script, then single run.

---

## Notes

- `[P]` = different file, no dependency on another incomplete task.
- `[Story]` label maps to spec.md user story for sub-issue traceability at `/speckit-taskstoissues` time.
- Tests are included (TDD) because each contract § Traceability row names a specific test artefact.
- Three tasks (T016, T022, T030) mutate the same file (`Onboarding.tsx`) sequentially — this is intentional per `contracts/onboarding-step-registry.md § 1` placeholder-replace pattern. Each subsequent task guarantees the previous task's step still renders (regression proof via `Onboarding.snap.test.tsx`).
- Never introduce a new runtime dependency (AGENTS.md hard rule; SC-008 of Spec 034). `scripts/compute-contrast.mjs` uses Bun stdlib only.
- Commit after each task or after a cohesion-merged group; run `bun test` + `uv run pytest` before committing; PR title follows Conventional Commits (`feat(035): <subject>` per AGENTS.md).
- Task budget consumed: 52 / 90. 38-task reserve protects against mid-cycle additions + the `[Deferred]` placeholder rows `/speckit-taskstoissues` will materialise from spec.md § Deferred Items table.
- Open-ended Deferred-item tracking (8 `NEEDS TRACKING` rows in spec.md § Scope Boundaries) resolves at `/speckit-taskstoissues` — those placeholder issues are NOT counted in this budget.

---

## Task Count Summary

| Phase | Tasks | [P] count | Story bindings |
|---|---|---|---|
| 1 — Setup | 3 (T001–T003) | 2 | — |
| 2 — Foundational | 3 (T004–T006) | 1 | — |
| 3 — US1 Splash | 12 (T007–T018) | 7 | US1 ×12 |
| 4 — US2 PIPA consent | 7 (T019–T025) | 3 | US2 ×7 |
| 5 — US3 Ministry scope | 10 (T026–T035) | 3 | US3 ×10 |
| 6 — US4 Token surface verif. | 3 (T036–T038) | 1 | US4 ×3 |
| 7 — US5 LogoV2 quality gate | 6 (T039–T044) | 3 | US5 ×6 |
| 8 — Polish | 8 (T045–T052) | 0 | — |
| **Total** | **52** | **20** | — |

Sub-issue 100-cap budget: 52 / 90 (42 % of ceiling; 38-slot reserve).
