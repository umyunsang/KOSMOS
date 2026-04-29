# Implementation Plan: 5-Primitive Align with Claude Code Tool.ts Interface

**Branch**: `2294-5-primitive-align` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/2294-5-primitive-align/spec.md`
**Worktree**: `/Users/um-yunsang/KOSMOS-w-2294`
**Epic**: #2294 (Initiative #2290 Layer 1) — Phase P3 Tool-system wiring re-iteration

## Summary

Refactor the four KOSMOS primitives (`LookupPrimitive`, `SubmitPrimitive`, `VerifyPrimitive`, `SubscribePrimitive`) so that each one implements the **complete** `Tool<In, Out>` contract from CC's `Tool.ts` (already byte-identical-ported into `tui/src/Tool.ts`), close two missing members (`validateInput`, `renderToolResultMessage`) plus the explicit `isMcp` flag, and add a single ToolRegistry boot guard that fails closed if any registered tool — primitive or adapter — is missing a required member or lacks a non-empty `real_classification_url` from `AdapterRealDomainPolicy` (Epic δ commit `c6747dd`). All permission UI continues to flow through CC's `FallbackPermissionRequest` (already ported); the only addition is that adapter `real_classification_url` + `policy_authority` strings are passed through verbatim as the prompt body. The Python backend `PrimitiveInput`/`PrimitiveOutput` IPC envelope (Spec 032) is **not** modified — this is a TS-side refactor anchored on stability of the cross-layer contract.

## Technical Context

**Language/Version**: TypeScript 5.6+ on Bun v1.2.x runtime (TUI layer; existing Spec 287 + 1635 stack — no version bump). Python 3.12+ backend referenced as a stable contract surface only (no Python edits).
**Primary Dependencies**: All existing — `zod` (input/output schemas; `zod/v4` namespace from `tui/package.json`), `ink` + `react` + `@inkjs/ui` (CC permission components, byte-identical ported), `@modelcontextprotocol/sdk` (the `isMcp` flag's reference type source). **Zero new runtime dependencies** (AGENTS.md hard rule + spec FR-014).
**Storage**: N/A. ToolRegistry is in-memory, rebuilt at process boot from `tui/src/tools/*Primitive` registrations + Python adapter manifests imported over IPC. No on-disk schema changes.
**Testing**: `bun test` (existing TUI test stack) + `uv run pytest` (existing backend stack). Three new TUI test files added by this Epic — `registry-boot.test.ts`, `permission-citation.test.ts`, `span-attribute-parity.test.ts`. PTY smoke captured via `expect`/`script` per `feedback_pr_pre_merge_interactive_test`.
**Target Platform**: Bun v1.2.x runtime on macOS / Linux (existing KOSMOS support matrix; no platform change).
**Project Type**: TUI — single-app (Ink + React + Bun) layered over a Python backend reached via Spec 032 stdio IPC.
**Performance Goals**: ToolRegistry boot ≤ 200 ms wall-clock for 22 entries (4 primitives + 18 adapters) per spec SC-002; PTY smoke "의정부 응급실 알려줘" round-trip ≤ 8 s wall-clock per spec SC-001.
**Constraints**: Diff size ≤ 1500 net LOC across the 4 primitive files + registry boot guard + 3 new tests (spec SC-006). All source text in English; Korean reserved for `description()` + user-facing UI (spec FR-015). No live `data.go.kr` calls in CI tests (Constitution § IV).
**Scale/Scope**: 4 primitive files + 1 registry boot guard module + 3 test files + 1 PTY smoke transcript directory. Existing 18 adapters consume the new contract via their already-registered metadata; no per-adapter edits.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Justification |
|---|---|---|
| **I. Reference-Driven Development** | ✅ PASS | Every refactor target maps to `.references/claude-code-sourcemap/restored-src/src/Tool.ts` (line 362 `Tool<>`, 436 `isMcp?`, 489 `validateInput?`, 566 `renderToolResultMessage?`, 721 `ToolDef<>`, 783 `buildTool`). Reference pattern for all 9 members lives in `.references/claude-code-sourcemap/restored-src/src/tools/AgentTool/AgentTool.tsx`. Layer-1 mapping in `docs/vision.md § Reference materials` cites Claude Code reconstructed (tool loop) + Pydantic AI (schema-driven) + OpenAI Agents SDK (guardrail pipeline) — `validateInput` work draws from the OpenAI Agents SDK guardrail pattern; `renderToolResultMessage` follows the CC reconstruction. |
| **II. Fail-Closed Security** | ✅ PASS | KOSMOS invents zero permission language. The new `validateInput` resolves the adapter and surfaces its citation; the existing CC `FallbackPermissionRequest` renders the citation byte-for-byte. Boot guard fails closed when `real_classification_url` is empty (spec FR-009). The 5-mode spectrum, `pipa_class`, `auth_level`, etc. removed in Spec 1979 are **not** reintroduced. |
| **III. Pydantic v2 Strict Typing** | ✅ PASS — by reference | Backend `PrimitiveInput`/`PrimitiveOutput` Pydantic v2 schema is unchanged (spec FR-011). TS-side schemas use `zod/v4` discriminated unions; `Any` is forbidden (existing pattern in `LookupPrimitive.ts`). |
| **IV. Government API Compliance** | ✅ PASS | No live `data.go.kr` traffic in CI; PTY smoke uses Mock fixtures for the NMC adapter. No new credentials or env vars introduced. |
| **V. Policy Alignment** | ✅ PASS | Refactor preserves the AI Action Plan Principle 8/9 single-window contract (lookup primitive routes the citizen request through one TUI surface). PIPA pathway unchanged — every personal-data flow continues to traverse the existing 7-step gauntlet. |
| **VI. Deferred Work Accountability** | ✅ PASS | Spec's "Scope Boundaries & Deferred Items" table lists 7 items; 4 are linked to existing issues (#2296 ε, #2297 ζ, #2362 δ-deferred), 2 are tagged `NEEDS TRACKING` for `/speckit-taskstoissues` resolution, 1 is a permanent boundary. No prose escapes — verified in Phase 0 research. |

**No constitution violations. No complexity-tracking entries required.**

## Project Structure

### Documentation (this feature)

```text
specs/2294-5-primitive-align/
├── plan.md              # this file
├── spec.md              # written by /speckit-specify
├── research.md          # Phase 0 — decisions + reference mapping + deferred-item validation
├── data-model.md        # Phase 1 — Tool / Primitive / AdapterRealDomainPolicy / ToolRegistry shapes
├── quickstart.md        # Phase 1 — citizen + reviewer walkthrough
├── contracts/
│   ├── primitive-shape.md          # 9-member contract per primitive
│   └── registry-boot-guard.md      # boot guard pre/post-conditions
├── checklists/
│   └── requirements.md  # written by /speckit-specify
├── scripts/             # PTY smoke harnesses (Phase 7 of /speckit-implement)
│   └── smoke-emergency-lookup.expect
├── smoke-emergency-lookup-pty.txt  # captured PTY transcript (mandatory before PR)
└── tasks.md             # written by /speckit-tasks (NOT this command)
```

### Source Code (repository root)

This is a single-app TUI layered over a stable Python backend. Only the TUI side is touched.

```text
tui/src/
├── Tool.ts                            # ALREADY byte-identical CC port (792 LOC) — UNCHANGED
├── tools/
│   ├── LookupPrimitive/
│   │   ├── LookupPrimitive.ts         # MODIFIED — add validateInput + renderToolResultMessage + isMcp
│   │   └── prompt.ts                  # MODIFIED — Korean description tightening
│   ├── SubmitPrimitive/
│   │   ├── SubmitPrimitive.ts         # MODIFIED — same 3 members + Korean description
│   │   └── prompt.ts                  # MODIFIED
│   ├── VerifyPrimitive/
│   │   ├── VerifyPrimitive.ts         # MODIFIED — same 3 members + Korean description
│   │   └── prompt.ts                  # MODIFIED
│   ├── SubscribePrimitive/
│   │   ├── SubscribePrimitive.ts      # MODIFIED — same 3 members + Korean description
│   │   └── prompt.ts                  # MODIFIED
│   ├── shared/
│   │   └── primitiveCitation.ts       # NEW — citation extractor used by validateInput + renderToolResultMessage
│   └── __tests__/
│       ├── registry-boot.test.ts      # NEW — Story 2 boot-time shape + citation guard
│       ├── permission-citation.test.ts# NEW — Story 3 byte-identical citation snapshot
│       └── span-attribute-parity.test.ts # NEW — SC-007 OTEL span attribute snapshot
├── services/
│   └── toolRegistry/
│       └── bootGuard.ts               # NEW — invoked by registry boot path; fails closed
└── components/permissions/
    └── FallbackPermissionRequest.tsx  # ALREADY CC-identical — UNCHANGED
```

The Python backend (`src/kosmos/primitives/{lookup,submit,verify,subscribe}.py`) is the IPC routing destination. **Not modified by this Epic** — that is the entire point of preserving `PrimitiveInput`/`PrimitiveOutput` (FR-011).

**Structure Decision**: Single-app TUI; all 4 primitive directories live under `tui/src/tools/<Name>Primitive/`. Three new test files live under `tui/src/tools/__tests__/`. The boot guard is the only **non-test** file added outside the primitive directories — it lives under `tui/src/services/toolRegistry/bootGuard.ts` to keep the registry construction site (current location of `ToolRegistry`) and the guard logic separable for testing.

## Complexity Tracking

> Empty — no Constitution violations require justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_ | _(N/A)_ | _(N/A)_ |
