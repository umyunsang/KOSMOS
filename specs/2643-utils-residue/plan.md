# Implementation Plan: Epic G — Utils 잔존 정리 (S9)

**Branch**: `feat/2643-s9-utils-residue` | **Date**: 2026-05-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/2643-utils-residue/spec.md`

## Summary

Epic G processes the 4 remaining S9 (Utils) audit items decided in `specs/cc-migration-audit/decisions.md § S9 Utils`:

1. **`utils/sessionTitle.ts` PORT** — byte-identical from CC + swap-1 wire to existing UMMAYA `queryHaiku` (resolves a P1 broken import in `cli/print.ts:156`).
2. **`utils/mcp/dateTimeParser.ts` PORT** — byte-identical from CC + swap-1 wire + Korean fixture regression tests + `elicitationValidation.ts` inline-stub removal (restores 한국어 자연어 시각 입력 surface for citizen UX).
3. **`permissions.ts` Path B 모듈 분리** — extract the inline `yoloClassifier` stub absorbed into `permissions.ts:103-145` into a sibling `yoloClassifier.ts` module, preserving CC's import shape (Path B precedent: Spec 2295 PR #2364 commit c6747dd).
4. **`secureStorage/` DROP ADR** — author `docs/adr/ADR-009-secureStorage-drop.md` to forensically pin the `.env`-only credential policy with a measurable future-trigger condition; cross-reference from `decisions.md` and `scope-S9-utils.md`.

Technical approach: pure byte-copy (with annotated swap-1 deviations) + import-shape refactor + ADR authoring. Zero new runtime dependencies. Zero Python source changes. All TypeScript edits scoped to `tui/src/utils/`.

## Technical Context

**Language/Version**: TypeScript 5.6+ on Bun v1.2.x (TUI layer, existing Spec 287 stack — no version bump). Python 3.12+ backend referenced via `services/api/claude.ts` boundary only (no Python edits).
**Primary Dependencies**: All existing — `zod ^3.23` (`zod/v4` namespace, used by sessionTitle's title schema), `@anthropic-ai/sdk` type aliases via `src/sdk-compat.js` (Spec 2521 shim), `ink` + `react` (no UI changes), `bun:test` + `ink-testing-library` (Korean fixture tests). **Zero new runtime dependencies** — AGENTS.md hard rule + spec assumption invariant + SC-005.
**Storage**: N/A. `generateSessionTitle` and `parseNaturalLanguageDateTime` are stateless function calls. Analytics events go through existing `services/analytics/index.ts:logEvent` (in-memory + OTLP collector via Spec 028).
**Testing**: `bun test` (unit + ink snapshot — `tui/src/utils/mcp/__tests__/dateTimeParser.test.ts` + permissions regression suite + sessionTitle unit). `pytest` baseline preserved (no Python changes). Layer 5 tmux capture-pane scenario for end-to-end SDK title-generation visual proof.
**Target Platform**: macOS (primary dev), Linux (CI). Headless `--print` SDK mode + interactive TUI both covered.
**Project Type**: TUI (Ink + React + Bun) within existing UMMAYA monorepo; this Epic touches only the `tui/` subtree plus `docs/adr/` and audit cross-references.
**Performance Goals**: `generateSessionTitle` p95 ≤ 6 s on FriendliAI Tier 1 (60 RPM), per Spec 2521 K-EXAONE smoke baselines. `parseNaturalLanguageDateTime` p95 ≤ 4 s (no JSON-schema overhead, single-shot ISO conversion).
**Constraints**: byte-identical CC fidelity (FR-016: total `permissions.ts` diff ≤ 8 lines vs CC). Zero Python deps. No live K-EXAONE in CI (AGENTS.md hard rule extension).
**Scale/Scope**: 4 source files added/modified (`sessionTitle.ts` create, `dateTimeParser.ts` create, `elicitationValidation.ts` edit, `permissions.ts` edit, `yoloClassifier.ts` create), 1 ADR file added, 2 audit-doc cross-reference updates, 1 unit test file added (`dateTimeParser.test.ts`), 1 unit test file added (`sessionTitle.test.ts`). Total ~10 file changes — within single-Sonnet teammate dispatch budget per AGENTS.md § Agent Teams (≤ 10 file changes per teammate), but split across 4 user stories for clean parallel dispatch.

## Constitution Check

*Constitution v1.1.1 (`.specify/memory/constitution.md`)*

| Principle | Check | Status |
|---|---|---|
| **I. Reference-Driven Development** | All 4 items map to `.references/claude-code-sourcemap/restored-src/src/utils/` (sessionTitle.ts byte-copy, dateTimeParser.ts byte-copy, yoloClassifier reconstruction in CC import shape, secureStorage/ DROP justified by `.env`-only scope). Layer mapping: Query Engine → Claude Code reconstructed (Haiku title generator); MCP elicitation → Claude Code reconstructed (NL date parsing); Permission Pipeline → OpenAI Agents SDK guardrail pipeline + Claude Code permission model (`yoloClassifier` belongs to the auto-mode classifier sub-surface). | **PASS** |
| **II. Fail-Closed Security (NON-NEGOTIABLE)** | `yoloClassifier` stub maintains `unavailable=true` (auto-mode = no-op). No UMMAYA-invented permission classifications introduced. `permissions.ts` callsite logic unchanged (FR-015). | **PASS** |
| **III. Pydantic v2 Strict Typing (NON-NEGOTIABLE)** | N/A — TypeScript-only Epic. No tool I/O schema changes. `YoloClassifierResult` type matches CC shape (TypeScript strict typing per existing tsconfig). | **PASS** (N/A) |
| **IV. Government API Compliance** | No live `data.go.kr` calls. K-EXAONE calls in tests use `queryHaiku` mock (FR-011). No new credentials surface — secureStorage DROP ADR explicitly preserves `.env`-only policy. | **PASS** |
| **V. Policy Alignment** | Korean citizen-facing surface restored (US2 한국어 시각 입력). PIPA / 7-step gauntlet untouched. | **PASS** |
| **VI. Deferred Work Accountability** | Spec's "Scope Boundaries & Deferred Items" table has 5 deferred rows, 1 with active tracking (#2637) and 4 with `NEEDS TRACKING` (resolved by `/speckit-taskstoissues`). No free-text "future epic"/"v2" mentions outside the table. | **PASS** |

**Gate Result**: All 6 principles PASS. No violations require Complexity Tracking entries. Re-check after Phase 1 design will revalidate (no schema changes ⇒ no re-evaluation needed).

## Project Structure

### Documentation (this feature)

```text
specs/2643-utils-residue/
├── plan.md              # This file
├── spec.md              # /speckit.specify output (complete)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (TS interface contracts)
│   ├── sessionTitle.contract.md
│   ├── dateTimeParser.contract.md
│   └── yoloClassifier.contract.md
├── checklists/
│   └── requirements.md  # /speckit.specify quality checklist (PASS)
├── scripts/             # Smoke / measurement scripts (created by /speckit-implement)
└── tasks.md             # /speckit-tasks output (NOT created here)
```

### Source Code (repository root — TUI subset only)

```text
tui/src/utils/
├── sessionTitle.ts                       # NEW (byte-copy CC + swap-1 wire)
├── __tests__/
│   └── sessionTitle.test.ts              # NEW (mocked queryHaiku)
├── mcp/
│   ├── dateTimeParser.ts                 # NEW (byte-copy CC + swap-1 wire)
│   ├── elicitationValidation.ts          # EDIT (lines 10-19 inline stub → import)
│   └── __tests__/
│       └── dateTimeParser.test.ts        # NEW (Korean fixture regression)
└── permissions/
    ├── permissions.ts                    # EDIT (lines 102-145 inline stub → import)
    └── yoloClassifier.ts                 # NEW (Path B module — CC shape stub)

tui/src/cli/
└── print.ts                              # UNCHANGED (line 156 import resolves naturally after FR-001)

docs/adr/
└── ADR-009-secureStorage-drop.md         # NEW (5-section ADR)

specs/cc-migration-audit/
├── decisions.md                          # EDIT (S9 row 2 cross-reference ADR-009)
└── scope-S9-utils.md                     # EDIT (P0-2~6 + D2 cross-reference ADR-009)
```

**Structure Decision**: UMMAYA monorepo with TUI subdirectory (`tui/`) hosting all TypeScript edits. ADR file under existing `docs/adr/` directory (slot ADR-009, next available after ADR-008). Audit cross-references inline in existing files. No new top-level directory creation. Total surface: 6 file creates + 4 file edits = 10 file changes.

## Phase 0 — Research

See [research.md](./research.md). Phase 0 covers:

- R-1: CC `sessionTitle.ts` byte-copy strategy + UMMAYA `queryHaiku` API surface verification
- R-2: CC `dateTimeParser.ts` byte-copy strategy + Korean fixture mock pattern
- R-3: Path B precedent re-read (Spec 2295 PR #2364 commit c6747dd) and applicability to `yoloClassifier`
- R-4: ADR-009 template authority (existing ADR-001 ~ ADR-008 inspection)
- R-5: UMMAYA `queryHaiku` surface verification
- R-6: Deferred items validation (Constitution Principle VI gate)

## Phase 1 — Design Artifacts

See [data-model.md](./data-model.md) and [contracts/](./contracts/) and [quickstart.md](./quickstart.md). Phase 1 covers:

- Function-shape contracts for the 3 new TS modules
- Test fixture matrix (Korean inputs × expected mock outputs × pass/fail expectations)
- Verification chain (Layer 1a / 1b / 2 / 3 / 4 / 5 per AGENTS.md § TUI verification)
- ADR-009 acceptance checklist

## Complexity Tracking

> No constitution violations. This section is intentionally empty per template guidance.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | (none) | (none) |
