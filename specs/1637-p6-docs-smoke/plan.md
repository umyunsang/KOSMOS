# Implementation Plan: P6 · Docs/API specs + Integration smoke

**Branch**: `feat/1637-p6-docs-smoke` | **Date**: 2026-04-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/1637-p6-docs-smoke/spec.md`

## Summary

P6 is the migration's terminal Epic. It produces (a) a single canonical `docs/api/` catalog covering all 24 registry-bundled adapters with seven mandatory fields each, (b) deterministic JSON Schema Draft 2020-12 exports under `docs/api/schemas/` driven by a stdlib + Pydantic v2 build script, (c) absorption of the legacy `docs/tools/` directory and cleanup of nine stale `road_risk_score` (composite) references, (d) `bun test` recovery to 0 fail / 0 errors with the TUI L2 regression at `useVirtualScroll.ts:273` resolved, (e) a hand-driven `bun run tui` visual smoke checklist with ANSI evidence capture mirroring the Spec 1636 convention, and (f) the closing migration deliverables — `docs/vision.md` post-merge prose, `CLAUDE.md § Recent Changes` entry, and the KOSMOS v0.1-alpha CHANGELOG. The integrated PR uses `Closes #1637` and unlocks Initiative #1631 closure once merged.

The technical approach is documentation-first plus minimal code: a single new Python script (`scripts/build_schemas.py`, stdlib + Pydantic v2 only), one TUI hook fix (`tui/src/hooks/useVirtualScroll.ts:273`), and an exhaustive doc authoring pass that follows the seven-field template established here. No new runtime dependencies on either the Python or TS side.

## Technical Context

**Language/Version**: Python 3.12+ (existing baseline); TypeScript 5.6+ on Bun v1.2.x (existing Spec 287 TUI stack).
**Primary Dependencies**: existing only — `pydantic >= 2.13` (envelope discovery + JSON Schema export), `pydantic-settings >= 2.0`, `httpx >= 0.27` (referenced in adapter docs, not invoked at build time), `opentelemetry-sdk` + `opentelemetry-semantic-conventions` (referenced in span-attribute documentation, not invoked here), `ink` + `react` (TUI fix scope only), Bun stdlib. **Zero new runtime dependencies** (AGENTS.md hard rule satisfied; spec FR-022).
**Storage**: filesystem only — `docs/api/` (Markdown specs + nested directories), `docs/api/schemas/` (JSON files), `specs/1637-p6-docs-smoke/visual-evidence/` (ANSI captures). No database, no external store.
**Testing**: `bun test` (TUI side, target 0 fail / 0 errors over ≥ 830 tests), `uv run pytest` (backend side, regression-free), `python scripts/build_schemas.py` (idempotency self-check via re-run diff).
**Target Platform**: KOSMOS developer terminal (Bun + uv) and KOSMOS citizen terminal (Bun-built TUI). PDF inline-render path conditional on Kitty / iTerm2 graphics protocol.
**Project Type**: monorepo — Python backend (`src/kosmos/**`), TypeScript TUI (`tui/**`), shared docs (`docs/**`), shared scripts (`scripts/**`). Single repo, no microservices.
**Performance Goals**: `python scripts/build_schemas.py` runs in under 5 seconds on a clean checkout (24 adapters); `bun test` total wall time stays at or under the current 12-second baseline; `bun run tui` cold start under 2 seconds.
**Constraints**: source text English only (search hints bilingual ko/en allowed per FR-021); no `Any` in any new Python code; visual-evidence ANSI capture follows Spec 1636 convention; PR `Closes #1637` only (Task sub-issues closed after merge per docs/conventions.md).
**Scale/Scope**: 24 adapter Markdown specs · 24 JSON Schema exports · 9 doc cleanup locations · 1 new Python script (~150 LOC budget) · 1 TUI hook fix (~5 LOC delta) · 5 cross-cutting doc updates (vision, CLAUDE.md, CHANGELOG.md, plus existing references rewritten) · 1 smoke checklist with ~17 ANSI captures.

## Constitution Check

*GATE: must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| I. Reference-Driven Development | PASS | Phase 0 Research § R3 maps adapter-spec-template to `docs/tools/koroad.md` (existing) + `specs/1636-plugin-dx-5tier/contracts/manifest.schema.json` precedent. § R6 maps visual-evidence capture to Spec 1636 convention. Cross-spec inheritance lists 1632/1633/1634/1635/1636. `docs/vision.md § Reference materials` mapping table consulted: Tool System row → "Pydantic AI (schema-driven registry)" → JSON Schema export approach grounded; TUI row → "Ink + Gemini CLI" → useVirtualScroll fix scope confined to existing port. |
| II. Fail-Closed Security (NON-NEGOTIABLE) | PASS | Documentation-only change to existing fail-closed defaults. Adapter specs **describe** the per-adapter `requires_auth=True` / `is_personal_data=True` settings; no defaults are loosened. The single TUI fix (useVirtualScroll Set error) does not touch permission code. |
| III. Pydantic v2 Strict Typing (NON-NEGOTIABLE) | PASS | `scripts/build_schemas.py` consumes existing Pydantic v2 envelopes via `model_json_schema()`. No new schemas introduced. No `Any` anywhere. JSON Schema dialect explicitly Draft 2020-12 (set on output via `$schema` URI). |
| IV. Government API Compliance | PASS | No live `data.go.kr` calls in plan or implementation. Adapter docs reference recorded fixtures only. `@pytest.mark.live` tests remain skipped per existing convention. No hardcoded keys; no key handling at this layer. |
| V. Policy Alignment | PASS | Adapter spec seven-field template explicitly carries permission-tier rationale citing Spec 033 (PIPA permission gauntlet). KOSMOS v0.1-alpha CHANGELOG references AI Action Plan Principles 8/9/5 alignment as the migration outcome. |
| VI. Deferred Work Accountability | PASS | Spec contains 5 deferred items, all marked `NEEDS TRACKING`; `/speckit-taskstoissues` will resolve to issue numbers. Spec.md already scanned for unregistered deferral patterns; "future epic", "v2", "post-v0.1-alpha" references all map to deferred-table rows. |

**Result**: all gates PASS. No Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/1637-p6-docs-smoke/
├── plan.md                      # This file (/speckit.plan output)
├── spec.md                      # /speckit.specify output (already authored)
├── research.md                  # Phase 0 output (this command)
├── data-model.md                # Phase 1 output (this command)
├── quickstart.md                # Phase 1 output (this command)
├── contracts/
│   ├── adapter-spec-template.md
│   ├── smoke-checklist-template.md
│   └── build-schemas-cli.md
├── checklists/
│   └── requirements.md          # Already authored
├── visual-evidence/             # Created during /speckit-implement
│   └── (ANSI captures, .ansi.txt + .txt pairs)
└── tasks.md                     # /speckit-tasks output (NOT created here)
```

### Source Code (repository root)

```text
docs/
├── api/                         # NEW canonical adapter catalog
│   ├── README.md                # Source × primitive matrix; 24-row index
│   ├── koroad/
│   │   ├── accident_search.md
│   │   └── accident_hazard_search.md
│   ├── kma/
│   │   ├── current_observation.md
│   │   ├── short_term_forecast.md
│   │   ├── ultra_short_term_forecast.md
│   │   ├── weather_alert_status.md
│   │   ├── pre_warning.md
│   │   └── forecast_fetch.md
│   ├── hira/
│   │   └── hospital_search.md
│   ├── nmc/
│   │   └── emergency_search.md  # Layer-3 gated; freshness sub-tool inline
│   ├── nfa119/
│   │   └── emergency_info_service.md
│   ├── mohw/
│   │   └── welfare_eligibility_search.md
│   ├── verify/
│   │   ├── digital_onepass.md
│   │   ├── mobile_id.md
│   │   ├── gongdong_injeungseo.md
│   │   ├── geumyung_injeungseo.md
│   │   ├── ganpyeon_injeung.md
│   │   └── mydata.md
│   ├── submit/
│   │   ├── traffic_fine_pay.md
│   │   └── welfare_application.md
│   ├── subscribe/
│   │   ├── cbs_disaster.md
│   │   ├── rss_public_notices.md
│   │   └── rest_pull_tick.md
│   ├── resolve_location/
│   │   └── index.md
│   └── schemas/                 # Generated by scripts/build_schemas.py
│       └── <tool_id>.json       # 24 files, Draft 2020-12
├── tools/                       # DELETED — merged into docs/api/
├── vision.md                    # § L1-A/B/C post-merge prose update
├── phase1-acceptance.md         # composite cleanup
├── research/
│   └── tool-system-migration-plan.md  # composite cleanup
├── design/
│   └── mvp-tools.md             # composite cleanup
└── requirements/
    ├── epic-p3-tool-system.md   # tool_ids list 14, not 15
    └── epic-p6-docs-smoke.md    # composite reference removed (this Epic itself)

scripts/
└── build_schemas.py             # NEW Pydantic→JSON Schema Draft 2020-12 builder

src/kosmos/                      # Read-only at this Epic — schema source of truth
└── tools/
    └── register_all.py          # walked by build_schemas.py for registry traversal

tui/
└── src/
    └── hooks/
        └── useVirtualScroll.ts  # Line 273 Set constructor type error fix

CLAUDE.md                        # § Active Technologies + § Recent Changes update
CHANGELOG.md                     # NEW v0.1-alpha entry
```

**Structure Decision**: KOSMOS is a single monorepo with a Python backend (`src/kosmos/`), TypeScript TUI (`tui/`), shared docs (`docs/`), and shared scripts (`scripts/`). This Epic touches docs (extensively), one Python script, one TS hook, and three top-level Markdown files (CLAUDE.md, CHANGELOG.md, vision.md). No new directories at the repo root; `docs/api/` is the only new directory under `docs/`. The structure follows the precedent set by Spec 1636 (which placed `docs/plugins/` as a sibling under `docs/`).

## Complexity Tracking

> Empty by intent. Constitution Check passed all gates without violation.
