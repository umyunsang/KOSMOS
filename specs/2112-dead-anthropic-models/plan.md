# Implementation Plan: P1 Dead Anthropic Model Matrix Removal

**Branch**: `2112-dead-anthropic-models` | **Date**: 2026-04-28 | **Spec**: [spec.md](./spec.md)
**Epic**: [#2112](https://github.com/umyunsang/KOSMOS/issues/2112)
**Phase**: P1 (`docs/requirements/kosmos-migration-tree.md § Execution Phase`)
**Input**: Feature specification at `/specs/2112-dead-anthropic-models/spec.md`

## Summary

Delete the dead Anthropic model ID dispatch matrix from the KOSMOS TUI layer (~2,019 LOC across 3 files: `tui/src/utils/model/modelOptions.ts` 539 LOC, `tui/src/utils/model/model.ts` 598 LOC, `tui/src/services/mockRateLimits.ts` 882 LOC) and migrate every TUI-side model lookup to the canonical `LGAI-EXAONE/K-EXAONE-236B-A23B` single-branch path established at `tui/src/utils/model/model.ts:179,187` and `src/kosmos/llm/config.py:37`. Remove the paired `tui/src/services/rateLimitMocking.ts` (sole `[ANT-ONLY]` caller of `mockRateLimits.ts`). Preserve the Python `LLMClient` truth values (FR-012/013/014/015), the OAuth + subscription tier helpers (deferred to P2), and the `services/api/claude.ts` import graph (also deferred to P2 — handled in this Epic via thin K-EXAONE alias if and only if cross-perimeter callers exist). Single integrated PR per memory `feedback_integrated_pr_only`. Zero new runtime dependencies per AGENTS.md hard rule.

## Technical Context

**Language/Version**: TypeScript 5.6+ on Bun v1.2.x (TUI layer, target of this epic) · Python 3.12+ (backend, untouched by this epic)
**Primary Dependencies**: All existing — `ink`, `react`, `@inkjs/ui`, `string-width`, `bun:bundle` (TS); `pydantic >= 2.13`, `pydantic-settings >= 2.0`, `httpx >= 0.27`, `opentelemetry-sdk`, `pytest`, `pytest-asyncio` (Python). **Zero new runtime dependencies** (AGENTS.md hard rule + FR-009 + SC-005).
**Storage**: N/A — deletion-only spec; no schema, no on-disk state, no migration. Model identifier remains in `src/kosmos/llm/config.py:37` (Python source-of-truth) and `tui/src/utils/model/model.ts:179,187` (TS source-of-truth) — no new persistence introduced.
**Testing**: `bun test` (TS) and `uv run pytest` (Python). Baselines: ≥ 984 TS pass / ≥ 437 Python pass (Epic #2077 commit 692d1c3).
**Target Platform**: macOS / Linux terminal (KOSMOS TUI run via `bun run tui`).
**Project Type**: hybrid backend (Python) + CLI/TUI (TypeScript on Bun) — KOSMOS canonical layout.
**Performance Goals**: TUI smoke (FR-011): "Hi" → Korean reply paint within 30 s; "강남역 어디?" → `lookup` primitive call → reply paint within 60 s. Both at FriendliAI Tier 1 (60 RPM).
**Constraints**: zero new runtime deps · single integrated PR · preserve `src/kosmos/llm/{config.py,client.py}` truth values · preserve OAuth/subscription tier helpers (P2 boundary) · preserve `services/api/claude.ts` import graph (P2 boundary). LOC drop target ≥ 40 % across the three target files (SC-006).
**Scale/Scope**: ~2 019 LOC removed (3 files) + ≤ 9 caller-file edits (Phase 0 grep). Total diff size estimate: −1 800 / +200 lines.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| **I. Reference-Driven Development** | ✅ PASS | Phase 0 research cites: HF model card `LGAI-EXAONE/K-EXAONE-236B-A23B` (architecture truth), FriendliAI Serverless docs (provider truth), CC source-map at `_cc_reference/api.ts` (model-selection lineage), `docs/vision.md § Reference materials` (Reference matrix), `docs/requirements/kosmos-migration-tree.md § L1-A.A1/A3/A4` (single-fixed provider invariant). Per memory `feedback_cc_source_migration_pattern`, this is a *deletion-driven* epic — we are removing CC residue that has no KOSMOS analogue, not porting new CC code. The CC sourcemap mapping table in `research.md § R4` documents which CC lines are dead under KOSMOS's invariants. |
| **II. Fail-Closed Security (NON-NEGOTIABLE)** | ✅ PASS | No tool adapter changes. No permission gauntlet changes. The collapsed `firstPartyNameToCanonical` is fail-safe: non-K-EXAONE input returns `'k-exaone'` short-name (FR-005) rather than throwing or accepting an Anthropic identifier. No PII flows touched. |
| **III. Pydantic v2 Strict Typing (NON-NEGOTIABLE)** | ✅ PASS | No tool I/O schema changes. `LLMClientConfig` (`src/kosmos/llm/config.py`) is preserved by FR-012. No `Any` introduced. |
| **IV. Government API Compliance** | ✅ PASS | No adapter changes. No live `data.go.kr` calls. No new credential paths. `KOSMOS_FRIENDLI_TOKEN` env-var pattern unchanged. |
| **V. Policy Alignment** | ✅ PASS | No conversational-window or open-API changes. PIPA permission gauntlet untouched. |
| **VI. Deferred Work Accountability** | ✅ PASS | spec.md § Scope Boundaries lists 5 deferred items in the structured table, each with `Tracking Issue: NEEDS TRACKING` resolved by `/speckit-taskstoissues`. Free-text "separate epic" / "future phase" patterns scanned in `research.md § Phase 0 deferred validation`. |

**Result**: All six principles PASS. No complexity entries required.

## Project Structure

### Documentation (this feature)

```text
specs/2112-dead-anthropic-models/
├── plan.md                    # this file
├── spec.md                    # feature specification (already written)
├── research.md                # Phase 0 output — 5 deep-research sources + deferred validation
├── data-model.md              # Phase 1 output — entities + state transitions
├── quickstart.md              # Phase 1 output — verification recipe (audit + smoke)
├── contracts/
│   └── audit-contract.md      # the audit-grade SC-001..SC-006 verification contract
├── checklists/
│   └── requirements.md        # already written by /speckit-specify
└── tasks.md                   # Phase 2 output — created by /speckit-tasks (NOT this command)
```

### Source Code (repository root) — KOSMOS canonical layout

```text
KOSMOS/
├── src/kosmos/                          # Python backend (untouched by this epic)
│   └── llm/
│       ├── config.py:37                 # ← K-EXAONE source-of-truth (preserved, FR-012)
│       ├── client.py:161-164            # ← sampling defaults (preserved, FR-013)
│       ├── client.py:226-280,411-613    # ← rate-limit retry (preserved, FR-014)
│       ├── client.py:838-844,854-858    # ← enable_thinking toggle (preserved, FR-015)
│       └── _cc_reference/               # ← CC sourcemap mirror (research-use, untouched)
│
├── tui/src/                             # TypeScript TUI (THIS EPIC TARGETS)
│   ├── utils/model/
│   │   ├── model.ts                     # ← prune Anthropic dispatch (FR-001/004/005/006)
│   │   ├── modelOptions.ts              # ← prune Anthropic options (FR-001/006)
│   │   ├── aliases.ts                   # ← may need K-EXAONE alias adjustment
│   │   ├── modelAllowlist.ts            # ← may need K-EXAONE-only allowlist
│   │   ├── modelCapabilities.ts         # ← capability lookup → K-EXAONE single
│   │   ├── modelStrings.ts              # ← string lookups → K-EXAONE
│   │   ├── modelSupportOverrides.ts     # ← may simplify
│   │   ├── deprecation.ts               # ← claude-3-* deprecation table → empty
│   │   ├── configs.ts                   # ← model config matrix → K-EXAONE
│   │   ├── providers.ts                 # ← FirstParty Anthropic check → P2-deferred
│   │   ├── bedrock.ts                   # ← AWS Bedrock provider (out of scope here)
│   │   ├── agent.ts                     # ← uses Default*Model helpers
│   │   └── validateModel.ts             # ← validate K-EXAONE only
│   ├── services/
│   │   ├── mockRateLimits.ts            # ← DELETE (FR-002)
│   │   └── rateLimitMocking.ts          # ← DELETE (FR-003)
│   └── … (caller files updated per FR-006 caller-reach rule)
│
├── docs/
│   ├── vision.md                        # canonical reference (cited)
│   └── requirements/kosmos-migration-tree.md  # canonical reference (cited)
└── AGENTS.md                            # hard-rule source (cited)
```

**Structure Decision**: This is a *deletion-driven* epic in the KOSMOS TUI subtree only. No new module is created. No new directory is introduced. The Python backend (`src/kosmos/`) is **read-only** to this epic — preserving truth values per FR-012/013/014/015. The 13 files inside `tui/src/utils/model/` plus 2 files inside `tui/src/services/` are the change perimeter; ≤ 9 external caller files (Phase 0 grep) receive minimal updates.

## Complexity Tracking

**Empty** — Constitution Check returned all PASS. No deviations to justify.
