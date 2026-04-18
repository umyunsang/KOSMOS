# Implementation Plan: Full TUI (Ink + React + Bun)

**Branch**: `287-tui-ink-react-bun` | **Date**: 2026-04-19 | **Spec**: [`specs/287-tui-ink-react-bun/spec.md`](./spec.md)
**Input**: Feature specification from `/specs/287-tui-ink-react-bun/spec.md`

## Summary

Port the Claude Code 2.1.88 Ink + React terminal UI onto the KOSMOS Python backend by keeping the upstream rendering spine (Ink reconciler, `useSyncExternalStore` store, virtualized list, permission-gauntlet modal, command dispatcher, theme engine) and replacing only the transport boundary. Claude Code's `services/api/` Anthropic REST client is swapped for a JSONL-over-stdio bridge that spawns `uv run kosmos-backend --ipc stdio` via `Bun.spawn`; Claude Code's `tools/*` developer-domain renderers are replaced by 14 Ink components that render the 5-primitive return variants (`lookup`, `resolve_location`, `submit`, `subscribe`, `verify`) defined by Spec 031 / #1052 and Spec 022 / #507.

Technical approach: TypeScript + Ink v7.0.0 + React 19.2 + Bun v1.2.x in a new `tui/` workspace. IPC frames are discriminated unions generated from the Python Pydantic v2 models via a code-gen step (`tui/scripts/gen-ipc-types.ts`) — no hand-duplicated schemas. Every file lifted from `.references/claude-code-sourcemap/restored-src/` carries a research-use attribution header (FR-011, SC-9). The Korean IME blocker (R1) is resolved ahead of any IME code by an ADR choosing between the `@jrichman/ink@6.6.9` fork (Gemini CLI's path) and a Node `readline` hybrid (FR-014, FR-057). The Python backend receives a thin new entrypoint `kosmos-backend --ipc stdio` that multiplexes the existing 5-primitive registry + Spec 027 coordinator mailbox over JSONL; no new Python runtime dependencies are added (AGENTS.md hard rule).

## Technical Context

**Language/Version**: TypeScript 5.6+ (TUI layer, `tui/`) with Bun v1.2.x as runtime + package manager; Python 3.12+ (existing backend, unchanged).
**Primary Dependencies** (TypeScript, all declared in `tui/package.json`):

- `ink@^7.0.0` (MIT) — terminal React reconciler
- `react@^19.2.0` + `react-dom` (MIT) — runtime pinned to Ink 7's peer range
- `@inkjs/ui@^2.0.0` (MIT) — TextInput / Spinner / Select components
- `string-width@^7` (MIT) — CJK width calculation
- `zod@^3.23` (MIT) — runtime validation of IPC frame shape (belt-and-braces atop generated types)
- `ink-testing-library@^4` (MIT) — fixture-driven component tests
- **Korean IME decision tracker**: `@jrichman/ink@6.6.9` (fork) **XOR** Node stdlib `readline` hybrid — chosen by ADR per FR-014.
- **Devtooling only**: `pydantic-to-typescript` Python CLI OR `datamodel-code-generator` invoked from `tui/scripts/gen-ipc-types.ts`; output is committed code, not a runtime dep.

**Primary Dependencies** (Python, unchanged): `pydantic >=2.13`, `pydantic-settings >=2.0`, `httpx >=0.27`, stdlib `asyncio` / `sys` / `json` for the new `--ipc stdio` adapter. **No new Python runtime deps** (AGENTS.md hard rule; Spec 031 SC-008).

**Storage**:

- TUI-side: N/A — zero local state per FR-131 / User Story 6; sessions round-trip through backend IPC.
- Backend-side: Existing Phase 1 JSONL session store (unchanged).

**Testing**:

- TypeScript: `bun test` + `ink-testing-library` (component unit), fixture JSON per discriminated-union arm (FR-034, FR-035).
- Python (new adapter only): `pytest` + `pytest-asyncio` for `kosmos-backend --ipc stdio` round-trip.
- Soak test: 10-minute fixture replay at 100+ ev/s via `bun test:soak` (FR-007, SC-2).
- Korean IME: headless stdin injection via `node --experimental-permission` harness on macOS + Linux (FR-015, FR-016, SC-4).

**Target Platform**:

- Primary: Linux + macOS terminals (kitty, alacritty, iTerm2, Konsole). Bun supports both.
- Windows: best-effort only (FR implicit via Edge Cases).
- Node/Bun: Bun v1.2.x runtime; Ink 7 requires Node 22 compatibility (satisfied by Bun's Node-compat layer).

**Project Type**: Desktop CLI application (TUI front-end + Python backend spawned as child process).

**Performance Goals**:

- Assistant chunk render latency ≤ 50 ms per chunk (FR-006).
- Sustained ≥ 100 IPC events/sec for ≥ 10 min with zero dropped frames on MacBook Air M1 (FR-007, FR-051, SC-2).
- Redraw ≤ 50 ms for 1,000-message fixture replay (User Story 7 Acceptance #1).
- Crash detection ≤ 5 s (FR-004, SC-5).

**Constraints**:

- `Bun.spawn` limited to stdin/stdout/stderr only (oven-sh/bun#4670, R4). Protocol MUST fit on three fds.
- Ink's `useInput` cannot buffer Hangul composition on macOS + Linux IMEs (R1, Claude Code issues #3045/#22732/#22853/#27857/#29745). Must be resolved by ADR before IME code.
- All source text English; only Korean domain data permitted (AGENTS.md hard rule). User-visible command copy is bilingual (`ko` + `en`) stored in `tui/i18n/` with English source text and Korean co-located translations.
- No file >1 MB committed without approval (AGENTS.md hard rule).
- Every file lifted from `restored-src/` carries attribution header (FR-011, SC-9).

**Scale/Scope**:

- Code lifted from `restored-src/`: ~1,884 files available; expected lift ≤ 120 files (reconciler, 14 renderer components, 20 permission-gauntlet components, command dispatcher, theme engine, virtualized list, coordinator status surface).
- KOSMOS-original TypeScript: ≤ 40 files (5-primitive renderers, IPC bridge, env config, entrypoint).
- Python additions: 1 entrypoint module (`src/kosmos/ipc/stdio.py`) + 1 CLI flag (`--ipc stdio`) on existing `kosmos-backend` command.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Reference-Driven Development — PASS

Every design decision in this plan maps to a concrete reference. Mapping captured in `research.md § Reference Ledger`. Primary references:

- TUI component lift → `.references/claude-code-sourcemap/restored-src/src/` (Claude Code 2.1.88, research-use)
- Ink reconciler + layout → `.references/claude-code-sourcemap/restored-src/src/ink/`
- Command dispatcher → `restored-src/src/commands/`
- Permission-gauntlet → `restored-src/src/components/` (`ToolPermission*.tsx`, `ApproveApiKey.tsx`, `CoordinatorAgentStatus.tsx`)
- Virtualized list + `overflowToBackbuffer` → Gemini CLI (`.references/gemini-cli/packages/cli/`, Apache-2.0)
- IPC contract → Spec 031 envelopes (`specs/031-five-primitive-harness/contracts/`) + Spec 027 coordinator mailbox (`specs/027-agent-swarm-core/data-model.md`)
- Korean IME resolution → Claude Code issues #3045/#22732/#22853/#27857/#29745 + `@jrichman/ink` fork (Gemini CLI's approach)
- Ink 7 upgrade constraints → Ink releases changelog (Node 22 + React 19.2 requirement)

### II. Fail-Closed Security — PASS

TUI does not introduce any new tool adapters; it is a presentation layer over existing primitives. The permission-gauntlet modal (User Story 4, FR-045) enforces the upstream `requires_auth=True` invariant — the TUI's role is to present, gather consent, and relay `permission_response` IPC frames. The TUI itself performs no permission relaxation. Crash-notice redaction of `KOSMOS_`-prefixed env vars (FR-004) matches the #468 secrets guard pattern.

### III. Pydantic v2 Strict Typing — PASS

All IPC frame types are generated FROM Pydantic v2 models (FR-003). No `Any` in generated TypeScript; the code-gen step emits TypeScript discriminated unions from the Python union types. The Python backend already conforms (Spec 031 constraint). Runtime validation on the TUI side uses `zod` schemas parallel to the generated types (belt-and-braces; purely TypeScript-side).

### IV. Government API Compliance — N/A for this layer

TUI does not call `data.go.kr` directly. All API calls flow through the backend's existing adapters (Specs 022 / 031). No live API calls from TypeScript. Renderer fixtures MUST be sourced from recorded responses in #507 (Spec 022) + #1052 (Spec 031) per FR-035.

### V. Policy Alignment — PASS

TUI implements AI Action Plan Principle 8 (single conversational window for cross-ministry citizen services) as the visible surface. Permission-gauntlet modal (FR-045) is the citizen-facing rendering of the PIPA-required 7-step permission pipeline. Bilingual command surface (FR-037) satisfies the Korean-first citizen audience requirement.

### VI. Deferred Work Accountability — PASS (with pending taskstoissues resolution)

Spec §"Scope Boundaries & Deferred Items" contains 13 deferred items, all with `NEEDS TRACKING` in the Tracking Issue column. Scan of spec body confirms zero deferral phrases outside the table. `/speckit-taskstoissues` will resolve the `NEEDS TRACKING` markers by creating placeholder issues and back-filling the spec. `/speckit-analyze` is expected to flag `NEEDS TRACKING` as actionable (not CRITICAL — it's the documented pre-taskstoissues state).

**Gate verdict**: PASS on all six principles. No complexity deviations required.

## Project Structure

### Documentation (this feature)

```text
specs/287-tui-ink-react-bun/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── README.md
│   ├── ipc-frames.schema.json        # Generated from Python Pydantic v2; re-emitted here for review
│   ├── user-input.schema.json
│   ├── assistant-chunk.schema.json
│   ├── tool-call.schema.json
│   ├── tool-result.schema.json       # Wraps 5-primitive envelope union
│   ├── coordinator-phase.schema.json
│   ├── worker-status.schema.json
│   ├── permission-request.schema.json
│   ├── permission-response.schema.json
│   ├── session-event.schema.json
│   └── error.schema.json
├── spec.md              # /speckit-specify output (committed upstream)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
# TypeScript TUI workspace (new)
tui/
├── package.json                        # Pinned Ink 7 + React 19.2 + Bun 1.2; IME fork pin behind ADR
├── tsconfig.json                       # strict mode; Bun + React 19 JSX
├── bun.lockb                           # Bun lockfile
├── NOTICE                              # Research-use attribution (FR-012)
├── docs/
│   ├── cjk-width-known-issues.md       # CJK width edge cases (ink#688, #759)
│   └── accessibility-checklist.md      # Manual a11y checklist (FR-056)
├── scripts/
│   ├── gen-ipc-types.ts                # Pydantic → TypeScript IPC frame code-gen (FR-003)
│   ├── diff-upstream.sh                # Compare lifted files to restored-src (FR-013)
│   └── soak.ts                         # 10-min 100 ev/s replay (FR-007)
├── src/
│   ├── main.tsx                        # Entrypoint — spawns kosmos-backend --ipc stdio
│   ├── ipc/
│   │   ├── bridge.ts                   # Bun.spawn wrapper; framing; FIFO queue (FR-001/005/009)
│   │   ├── frames.generated.ts         # Generated IPC frame types (do-not-edit)
│   │   ├── codec.ts                    # JSONL encode/decode; zod runtime validation
│   │   └── crash-detector.ts           # ≤5 s crash detection + KOSMOS_* redaction (FR-004)
│   ├── commands/                       # Lifted from restored-src/src/commands/ (FR-036)
│   │   ├── registry.ts
│   │   ├── save.ts / sessions.ts / resume.ts / new.ts  # /save /sessions /resume /new (FR-038)
│   │   └── dispatcher.ts
│   ├── i18n/
│   │   ├── en.ts                       # English user-visible strings (source)
│   │   └── ko.ts                       # Korean translations (FR-037)
│   ├── theme/                          # Lifted from restored-src/src/theme.ts etc (FR-039/040)
│   │   ├── tokens.ts                   # ThemeToken named set (FR-040)
│   │   ├── default.ts / dark.ts / light.ts
│   │   └── provider.tsx                # KOSMOS_TUI_THEME env var reader (FR-041)
│   ├── components/
│   │   ├── primitive/                  # KOSMOS-original renderers (Spec 031 envelopes)
│   │   │   ├── PointCard.tsx           # FR-017
│   │   │   ├── TimeseriesTable.tsx     # FR-018
│   │   │   ├── CollectionList.tsx      # FR-019
│   │   │   ├── DetailView.tsx          # FR-020
│   │   │   ├── ErrorBanner.tsx         # FR-021
│   │   │   ├── CoordPill.tsx           # FR-022
│   │   │   ├── AdmCodeBadge.tsx        # FR-023
│   │   │   ├── AddressBlock.tsx        # FR-024
│   │   │   ├── POIMarker.tsx           # FR-025
│   │   │   ├── SubmitReceipt.tsx       # FR-026
│   │   │   ├── SubmitErrorBanner.tsx   # FR-027
│   │   │   ├── EventStream.tsx         # FR-028
│   │   │   ├── StreamClosed.tsx        # FR-029
│   │   │   ├── AuthContextCard.tsx     # FR-030/031
│   │   │   ├── AuthWarningBanner.tsx   # FR-032
│   │   │   └── UnrecognizedPayload.tsx # FR-033
│   │   ├── coordinator/                # Lifted from restored-src/src/coordinator/ (FR-047)
│   │   │   ├── PhaseIndicator.tsx      # FR-043
│   │   │   ├── WorkerStatusRow.tsx     # FR-044
│   │   │   └── PermissionGauntletModal.tsx  # FR-045/046
│   │   ├── conversation/               # Lifted from restored-src/src/components/ (User Story 7)
│   │   │   ├── MessageList.tsx         # Uses VirtualizedList
│   │   │   ├── VirtualizedList.tsx     # Lifted (FR-048)
│   │   │   ├── StreamingMessage.tsx    # useSyncExternalStore (FR-050)
│   │   │   └── CrashNotice.tsx         # FR-004
│   │   └── input/
│   │       └── InputBar.tsx            # IME: fork-based OR readline-hybrid per ADR
│   ├── hooks/                          # Lifted from restored-src/src/hooks/
│   │   ├── useIPC.ts                   # useSyncExternalStore shim over IPC frames
│   │   ├── useKeybindings.ts
│   │   └── useKoreanIME.ts             # Strategy selector per ADR
│   ├── store/
│   │   └── session-store.ts            # useSyncExternalStore message/coordinator store
│   └── entrypoints/
│       └── tui.tsx                     # `bun run tui` entry
└── tests/
    ├── ipc/
    │   ├── bridge.test.ts              # Bun.spawn + 2 s startup + FIFO (User Story 1 scenarios)
    │   ├── crash.test.ts               # ≤5 s crash + redaction (FR-004)
    │   └── soak.test.ts                # 100 ev/s × 10 min (FR-007, SC-2)
    ├── components/primitive/*.test.tsx # One per renderer × all discriminator arms (FR-034)
    ├── components/coordinator/*.test.tsx
    ├── commands/dispatcher.test.ts
    ├── theme/provider.test.tsx
    ├── hooks/useKoreanIME.test.ts      # Hangul composition (FR-015, FR-016)
    └── fixtures/
        ├── lookup/                     # Pulled from #507 recorded responses (FR-035)
        ├── resolve_location/
        ├── submit/
        ├── subscribe/
        ├── verify/
        └── coordinator/                # Scripted #13/#14 scenarios (FR-043–FR-047)

# Python backend — new minimal adapter only (no new runtime deps)
src/kosmos/ipc/
├── __init__.py
├── stdio.py                            # async stdin/stdout JSONL multiplexer
└── frame_schema.py                     # Pydantic IPCFrame discriminated union (source of FR-003 code-gen)

src/kosmos/cli/
└── __main__.py                         # Add --ipc stdio flag routing to kosmos.ipc.stdio

tests/ipc/
├── test_stdio_roundtrip.py             # Python side round-trip + frame schema
└── test_frame_schema.py                # Pydantic frame validation

# ADRs (new)
docs/adr/
├── NNN-bun-ink-react-tui-stack.md       # SC-1 gate (FR-057)
├── NNN-claude-code-sourcemap-port.md    # Research-use + attribution (FR-011/012, SC-9)
└── NNN-korean-ime-strategy.md           # FR-014 / R1 resolution

# Attribution
tui/NOTICE                              # Research-use + Anthropic attribution (FR-012)

# Env registry (extend existing)
src/kosmos/config/env_registry.py       # Register KOSMOS_TUI_THEME, KOSMOS_TUI_LOG_LEVEL,
                                        # KOSMOS_TUI_SUBSCRIBE_TIMEOUT_S (FR-041, #468)
```

**Structure Decision**: Dual-language workspace. `tui/` is the **only** TypeScript directory — AGENTS.md hard rule permits TypeScript exclusively for the TUI layer. Python backend keeps its existing `src/kosmos/` layout; a single new `src/kosmos/ipc/` subpackage adds the stdio multiplexer without touching any existing module. TUI tests live inside `tui/tests/`; Python IPC tests live in the existing `tests/` root. No monorepo tooling (no Turborepo/Nx/pnpm workspaces) — `bun install` is invoked from `tui/` and `uv sync` from the repo root. Top-level `Makefile` / `package.json` at repo root remain untouched; a future ADR can add a top-level orchestrator if needed.

## Complexity Tracking

> No constitution violations requiring justification. All six principles passed.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)* | — | — |
