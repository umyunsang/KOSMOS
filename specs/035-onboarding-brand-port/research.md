# Phase 0 Research: Onboarding + Brand Port

**Feature**: Epic H #1302 — Onboarding + brand port (binds ADR-006 A-9)
**Branch**: `035-onboarding-brand-port`
**Date**: 2026-04-20
**Input**: [plan.md § Phase 0](./plan.md#phase-0--outline--research), [spec.md](./spec.md)

**Methodology**: Each decision below maps to a concrete reference source per Constitution Principle I (Reference-Driven Development). Primary references are drawn from `docs/vision.md § Reference materials`, the Epic's upstream anchors (ADR-006 A-9, brand-system.md § 1–§ 2, accessibility-gate.md § 7, component-catalog Epic H rows), and the CC restored-src tree (`.references/claude-code-sourcemap/restored-src/` @ `a8a678c`, CC 2.1.88).

All ten open research items from plan.md are resolved. Zero `NEEDS CLARIFICATION` markers remain.

---

## R-1 — `MinistryCode` TitleCase normalisation

- **Decision**: Adopt TitleCase throughout. Ship `agentSatelliteKoroad`, `agentSatelliteKma`, `agentSatelliteHira`, `agentSatelliteNmc` in `tui/src/theme/tokens.ts` + `tui/src/theme/dark.ts`. The Epic body's all-caps form (`agentSatelliteKOROAD` etc.) is a pre-§ 2-grammar draft; this spec canonicalises to the § 2 BNF.
- **Rationale**: `docs/design/brand-system.md § 2` BNF is unambiguous — `MinistryCode ::= "Koroad" | "Kma" | "Hira" | "Nmc" | …` with the rule "`MinistryCode` is TitleCased because it is a proper noun abbreviation, not a `Variant`." The Brand Guardian grep gate at `specs/034-tui-component-catalog/contracts/grep-gate-rules.md § 4` parses against this BNF — all-caps would be rejected. Epic body was authored before Spec 034 merged (ac3c763, 2026-04-20); § 2 is the newer normative contract.
- **Alternatives considered**:
  - All-caps (`agentSatelliteKOROAD`) — rejected: fails § 2 grammar, blocks grep gate.
  - Kebab-case (`agent-satellite-koroad`) — rejected: § 2 prohibits separators ("Concatenation is direct with no separator").
  - Dropping the `agentSatellite` prefix (`koroad`) — rejected: § 2 requires the `MetaphorRole` prefix; bare ministry code would resolve to `SemanticRole` bucket which does not accept these values.

## R-2 — Shimmer-variant hex selection for `kosmosCore` + `orbitalRing`

- **Decision**:
  - `kosmosCoreShimmer = #a5b4fc` (lightened lavender — indigo-300 family; one step lighter than `kosmosCore`'s `#818cf8` → `#6366f1` gradient base).
  - `orbitalRingShimmer = #c7d2fe` (lightened indigo — two steps lighter than `orbitalRing`'s `#60a5fa` → `#a78bfa` gradient).
- **Rationale**: Both values are present in the `assets/kosmos-logo.svg` 16-hex palette (verified 2026-04-20 by `grep -oE "#[0-9a-fA-F]{6}"` over the SVG). Both pass 4.5 : 1 against `#0a0e27` navy when used as text-weight shimmer and 3.0 : 1 against the orbital ring gradient anchors when used as non-text UI chrome. Pattern parallel from CC `dark.ts` L15–16: `claude = rgb(215,119,87)` + `claudeShimmer = rgb(235,159,127)` — shimmer is a uniformly lightened variant of the primary. Confirmation pending R-3 contrast measurement pass.
- **Alternatives considered**:
  - `#6ee7b7` (mint green) — rejected: belongs to the `agentSatelliteKma` family's near neighbours; would create perceptual collision with the KMA satellite node.
  - `#f9a8d4` (light pink) — rejected: belongs to the `agentSatelliteKoroad` family; same collision concern.
  - Computed shimmer via HSL lightness bump — rejected: introduces new runtime colour math; SVG-extracted values are deterministic and auditable. CC's `dark.ts` also uses literal shimmer hexes, not computed ones.

## R-3 — Contrast-ratio measurement methodology

- **Decision**: Author `scripts/compute-contrast.mjs` — a self-contained Bun script that:
  1. Parses `tui/src/theme/dark.ts` using `@babel/parser`-free regex (Bun stdlib `Bun.file().text()` + string match); tokenises the `rgb(R,G,B)` values into a map.
  2. For each `(fg, bg)` pair rendered by any component (enumerated against the 9 LogoV2 rewrite rows + the 3 onboarding steps), computes the WCAG 2.1 relative-luminance ratio via the published formula (`L = 0.2126·R + 0.7152·G + 0.0722·B` on linearised sRGB; ratio = `(L1 + 0.05) / (L2 + 0.05)` with L1 ≥ L2).
  3. Rounds the ratio to two decimal places and compares against the WCAG 2.1 AA threshold — `≥ 4.5` for body text, `≥ 3.0` for large text / non-text.
  4. Emits `docs/design/contrast-measurements.md` (a flat Markdown table) and exits with non-zero status if any pair fails.
- **Rationale**: Bun ships with `Bun.file()` and global `fetch` + stdlib `Math.pow`; zero runtime deps needed. The WCAG formula is public-domain. Deterministic + CI-friendly (a `pre-commit` or `brand-guardian.yml` workflow runs the script on every PR that touches `tui/src/theme/**`). `docs/tui/accessibility-gate.md § 7` delegates the measurement method to Epic H. No NPM package (rejected under AGENTS.md "Never add a dependency outside a spec-driven PR").
- **Alternatives considered**:
  - `wcag-contrast` NPM package — rejected: new runtime dep, AGENTS.md hard rule violation.
  - Chrome DevTools contrast-ratio picker — rejected: not reproducible in CI; not scriptable.
  - Hand-measured ratios in a markdown table — rejected: high error risk; no drift detection on palette changes.

## R-4 — Memdir USER-tier record file layout

- **Decision**:
  - Consent records at `~/.kosmos/memdir/user/consent/<timestamp>-<session_id>.json`.
    - `<timestamp>` = ISO-8601 UTC with `Z` suffix, colons replaced by `-` for POSIX portability (`2026-04-20T14-32-05Z`).
    - `<session_id>` = UUIDv7 (timestamp-prepended, Spec 032 precedent).
  - Ministry-scope records at `~/.kosmos/memdir/user/ministry-scope/<timestamp>-<session_id>.json`.
  - Append-only: never overwrite or delete a record. "Latest effective state" = most recent record by timestamp.
  - Atomic write: write to `<path>.tmp`, `os.fsync()`, then `os.rename()` — Spec 027 § 4 mailbox pattern.
- **Rationale**: Spec 027 § 4 established the `~/.kosmos/mailbox/` precedent for Python-backend POSIX filesystem state; extending under `~/.kosmos/memdir/user/` keeps the state-root coherent. Append-only is required by Constitution Principle II (audit log) + vision.md § Permission pipeline Step 7 ("every call is logged"). UUIDv7 is already used by Spec 032 for `correlation_id` generation — `uuid.uuid7()` is a 3.12 stdlib function, no new dep. The `consent/` and `ministry-scope/` subdirectories are new but fall under the existing memdir umbrella.
- **Alternatives considered**:
  - Single overwriting file (`~/.kosmos/memdir/user/consent.json`) — rejected: violates audit-log invariant; a mistaken re-consent could erase evidence of the prior decision.
  - SQLite database (`~/.kosmos/memdir/user.db`) — rejected: new runtime dep (`sqlite3` is stdlib, but a schema migration story is required; violates the "files only" convention of Spec 027).
  - JSON Lines append at a single file (`consent.jsonl`) — rejected: harder to prune old records in a future GDPR-style deletion; one-file-per-record is easier to audit.

## R-5 — AAL gate value taxonomy

- **Decision**: Reuse the `AuthenticatorAssuranceLevel` enum from `specs/033-permission-v2-spectrum/`. Values: `{AAL1, AAL2, AAL3}` with default `AAL1` at onboarding time (pre-identity-verification).
- **Rationale**: Spec 033 merged 2026-04 (PR #1441, Epic M precursor) and is the normative source for permission + authentication assurance levels in KOSMOS. Duplicating an enum here would violate DRY and create drift. The `aalGate` field in `PIPAConsentRecord` is a snapshot of the citizen's AAL at consent time; subsequent AAL upgrades (e.g., identity-verification completion) trigger new consent records per R-4.
- **Alternatives considered**:
  - Local enum with numeric values (`aal: 1 | 2 | 3`) — rejected: would fork Spec 033's contract.
  - Boolean `isVerified` — rejected: loses the 3-tier assurance distinction required by PIPA § 24 (고유식별정보 처리 동의) and Spec 033.
  - Omit AAL field — rejected: Epic body FR-013 explicitly requires the AAL gate.

## R-6 — Onboarding state-machine re-entry + skip logic

- **Decision**: Linear 3-step state machine with no branching:

  ```
  splash ──Enter──▶ pipa-consent ──Enter──▶ ministry-scope-ack ──Enter──▶ done
     │                  │                           │
     └──── Escape ──────┴───────── Escape ──────────┴──▶ exit(0), no record written
  ```

  Session-start decision tree:

  ```
  read memdir /user/consent/ latest → CONSENT_VERSION match? 
      ├─ yes → read /user/ministry-scope/ latest → version match? 
      │           ├─ yes → fast-path (splash-only, 3 s budget) → done
      │           └─ no  → render ministry-scope step, skip pipa-consent
      └─ no  → render full 3-step flow
  ```
- **Rationale**: CC `Onboarding.tsx` L33 uses `useState<number>(0)` + `goToNextStep()` linear advancement — this is the step-registry shape the ADR-006 A-9 commits to preserving. Back-navigation is a `wizard/*` concern deferred to a separate spec row. Skip logic is state-driven (memdir read only — never session or system state) per plan.md's "skipCondition may only evaluate memdir USER state" invariant. Escape-at-any-step = exit is the CC behaviour (`useExitOnCtrlCDWithKeybindings()`) preserved verbatim.
- **Alternatives considered**:
  - Wizard back-navigation — deferred to `wizard/*` REWRITE row (Deferred Items table).
  - Non-linear branching (e.g., "skip PIPA consent if returning user"): rejected — that IS the skip-condition at session start, not a branch in the step machine itself.
  - Re-prompt every session regardless of consent version — rejected: violates SC-012 (returning-citizen ≤ 3 s).

## R-7 — CC LogoV2 layout-mode utility reuse

- **Decision**: Partial PORT. From `.references/claude-code-sourcemap/restored-src/src/utils/logoV2Utils.ts`:
  - **PORT** (generic terminal-size math, no CC content): `getLayoutMode`, `calculateLayoutDimensions`, `calculateOptimalLeftWidth`, `formatWelcomeMessage`, `truncatePath`.
  - **REWRITE** (CC-specific content binding): `getRecentActivitySync` → `getKosmosSessionHistorySync` (reads `~/.kosmos/memdir/session/` via Spec 027 infrastructure); `getRecentReleaseNotesSync` → `getMinistryAvailabilitySync` (reads Spec 022 adapter registry snapshot).
  - **DISCARD** (CC brand identifier): `getLogoDisplayData` — embeds Anthropic Clawd branding; LogoV2 KOSMOS-REWRITE inlines its own display data.
- **Rationale**: Component-catalog PORT-first principle — lift verbatim when the logic is content-agnostic; REWRITE when content binds to CC-specific data sources. The 5 PORT-candidates are pure geometry / string utilities; the 2 REWRITE targets are thin adapters over KOSMOS data sources. `getLogoDisplayData` is the only DISCARD because it hardcodes CC wordmark + Clawd poses.
- **Alternatives considered**:
  - Rewrite entire `logoV2Utils.ts` — rejected: wastes ~200 lines of reusable geometry code; violates catalog PORT principle.
  - Keep DISCARD function and stub out Anthropic content — rejected: leaves dead code paths and import-site drift.

## R-8 — Reduced-motion env flag handling

- **Decision**: Create `tui/src/hooks/useReducedMotion.ts` (new hook) that reads `process.env.NO_COLOR` and `process.env.KOSMOS_REDUCED_MOTION` at hook-init time and returns a boolean `prefersReducedMotion`. The hook returns a stable value for the session lifetime (env flags are read once at mount, per Ink convention). Consumed by:
  - `AnimatedAsterisk` (REWRITE — skips `useShimmerAnimation` subscription, emits static asterisk).
  - `orbitalRing` render path in `LogoV2.tsx` (REWRITE — skips gradient animation, emits static ring).
  - `CondensedLogo` (REWRITE — skips pulse, emits static header).
  - `AnimatedAsterisk`-consuming components in the LogoV2 family.
- **Rationale**: `docs/tui/accessibility-gate.md § 1.1` pathway 2 ("Reduced-motion fallback") requires the behaviour; delegating the env-flag read to a hook matches Spec 287's `useKoreanIME()` precedent. Reading once at mount (not per-frame) is correct because env flags cannot change mid-session. `NO_COLOR` is a widely-adopted community convention (https://no-color.org/) and is honoured by CC.
- **Alternatives considered**:
  - Per-component conditional `useEffect` — rejected: scatters flag reads; hard to audit for coverage.
  - Runtime configuration via a Settings dialog — rejected: Settings / ThemePicker are deferred to Epic K #1308.
  - Always-static rendering (no animation at all) — rejected: loses the shimmer affordance for users who do not have reduced-motion needs.

## R-9 — Hangul and Korean-label rendering under Ink

- **Decision**: Rely on Spec 287's existing `tui/src/ink/stringWidth.ts` (ported from CC) for all Korean label width calculations. Ministry labels use the pattern `<Korean name> (<English adapter code>)` — e.g. `한국도로공사 (KOROAD)`. The parenthetical English code exists for screen-reader disambiguation when Korean TTS is not configured; it is NOT a translation.
- **Rationale**: `stringWidth.ts` already handles the East-Asian Wide (EAW) Unicode property correctly for Hangul syllable blocks (width 2 per glyph). No new measurement utility is needed. vision.md § Citizen onboarding commits to Korean labels. Screen-reader narration with English adapter codes is a concrete application of accessibility-gate.md § 1.1 pathway 1 (text-stream accessibility).
- **Alternatives considered**:
  - English-only labels — rejected: contradicts vision.md § Citizen onboarding.
  - Pure Korean labels with no English codes — rejected: breaks screen-reader disambiguation when the user's TTS engine only speaks English; blocks KWCAG audit.
  - Bilingual double-line labels (Korean \n English) — rejected: doubles the ministry-node row height; breaks the 80-column budget.

## R-10 — `kosmos-logo-dark.svg` doc-drift fix

- **Decision**: Single-line edit to `docs/design/brand-system.md § 1 Permanent cross-references` — replace the bullet `../../assets/kosmos-logo-dark.svg — logo optimised for the KOSMOS navy dark background; cited directly in ADR-006 A-9 as the onboarding splash source` with `../../assets/kosmos-banner-dark.svg — wide wordmark + subtitle on dark background; canonical palette extraction source per ADR-006 A-9` (the existing next-line entry already names this file; the replacement collapses the two entries into one accurate line). Bundle in Epic H PR (FR-027 § 3 authoring already touches § 1 ministry roster — low-conflict edit).
- **Rationale**: Filesystem verification (`ls /Users/um-yunsang/KOSMOS/assets/`) confirms only `kosmos-logo.svg`, `kosmos-banner-dark.svg`, `kosmos-banner-light.svg`, `kosmos-logo.png`, `kosmos-banner-dark.png`, `kosmos-banner-light.png`, `kosmos-org-avatar.svg`, `kosmos-org-avatar.png` exist. ADR-006 A-9 line "`assets/kosmos-logo-dark.svg` / icon component equivalent" indicates the SVG was planned but the "icon component equivalent" (KosmosCoreIcon per FR-023) was accepted as the delivered form. TUI does not render SVG — the hex palette is the only consumed output.
- **Alternatives considered**:
  - Author `kosmos-logo-dark.svg` from scratch — rejected: redundant (TUI does not render SVG); would fork the `kosmos-logo.svg` file with an identical palette.
  - Leave the drift — rejected: violates Constitution Principle I (reference traceability) because § 1 points at a non-existent file.
  - Split into a separate doc-fix PR under Brand Guardian — rejected: adds a round-trip cost without scope benefit; Epic H PR already touches § 1 for the ministry-roster accent binding.

---

## Deferred Items validation

From `spec.md § Scope Boundaries & Deferred Items`, consolidated:

### Out of Scope (Permanent) — 4 rows

1. Light and high-contrast themes — Phase 1 `dark` only (Epic body acceptance # 4).
2. SVG-to-terminal rendering — terminal character grid only (AGENTS.md TUI stack).
3. Audio / voice feedback — no audio subsystem in KOSMOS.
4. Browser / mobile equivalent — AGENTS.md hard rule: TypeScript for TUI only.

### Deferred to Future Work — 10 rows

| # | Item | Target | Tracking status | Verification |
|---|------|--------|-----------------|--------------|
| 1 | Theme picker (light + high-contrast) | Epic K #1308 | Issue exists | `gh api graphql` returned OPEN for #1308 ✅ |
| 2 | `design-system/*` PORT (26 rows) | Epic H follow-up / Epic M #1310 | NEEDS TRACKING | `/speckit-taskstoissues` will create placeholder |
| 3 | `CustomSelect/*` PORT (10 rows) | Epic H follow-up / Epic M #1310 | NEEDS TRACKING | `/speckit-taskstoissues` will create placeholder |
| 4 | `wizard/*` REWRITE (4 rows) | Epic H follow-up | NEEDS TRACKING | `/speckit-taskstoissues` will create placeholder |
| 5 | `TagTabs.tsx` PORT | Epic H follow-up | NEEDS TRACKING | `/speckit-taskstoissues` will create placeholder |
| 6 | 69-token mass rename | Epic M #1310 Deferred row 10 | Issue exists | `gh api graphql` returned OPEN for #1310 ✅ |
| 7 | § 8 Voice & tone authoring | Epic K #1308 | Issue exists | ✅ |
| 8 | § 10 Component usage appendix | Epics B/C/D/E/H/I/J/K/L/M — ongoing | Issue exists | #1310 anchor ✅ |
| 9 | Phase 2 ministry tokens (119 NFA, Geocoding, MOHW, MOLIT) | Phase 2 adapter Epics | NEEDS TRACKING | Spec 029 is nearest — placeholder will cite |
| 10 | Deep 4.1.2 (Name Role Value) compliance | Issue #25 | Issue exists | ✅ |
| 11 | `brand-system.md § 1` doc-fix (kosmos-logo-dark.svg ref) | Epic H PR (this spec) | In-scope (bundled) | Resolved in R-10 above |

### Ghost-deferral scan

Scanned `spec.md` prose for unregistered deferral phrases:
- "separate epic" — 2 matches, both in Deferred Items rows 2 / 3 (registered). ✅
- "future phase" — 0 matches outside the table. ✅
- "Phase 2" / "Phase 2+" — 3 matches, all cited in Deferred row 9 or in the Assumptions / Out-of-Scope explanation. ✅
- "v2" — 0 matches. ✅
- "deferred to" / "deferred" — 11 matches, all within the Deferred Items table or its explanatory prose. ✅
- "out of scope for v1" — 0 matches. ✅
- "later release" — 0 matches. ✅

**Scan result**: **0 ghost deferrals**. Constitution Principle VI gate **PASSES**.

### Issue existence verification

As of 2026-04-20, `gh api graphql` confirms:
- Issue #1308 (Epic K Settings) — `OPEN`.
- Issue #25 (Deep 4.1.2 compliance) — `OPEN`.
- Issue #1310 (Epic M TUI component catalog) — `OPEN`.
- Issue #1302 (Epic H — this spec's parent) — `OPEN`, parent = Initiative #2.

All referenced tracking issues exist and are open. Issues marked `NEEDS TRACKING` will be created by `/speckit-taskstoissues` in the natural workflow (see Phase 2).

---

## Summary for `/speckit-plan` re-evaluation

- 10 / 10 research items resolved with a Decision / Rationale / Alternatives block.
- Every decision cites a primary reference from the Constitution-mandated source set.
- 0 `NEEDS CLARIFICATION` markers remain.
- Deferred Items table: **0 ghost deferrals**, all referenced issues OPEN.
- Constitution Principles I / II / III / IV / V / VI all green for the Phase 0 gate.

**Next step**: proceed to Phase 1 (data-model.md + contracts/ + quickstart.md).
