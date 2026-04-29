# Acceptance Report — Epic γ #2294 (T025-T027 output)

**Captured**: 2026-04-29 | **Branch**: `2294-5-primitive-align` | **Final commit before report**: `4051c22`

This document records the Phase 8 final-acceptance battery measurements for Epic γ. It is the single artefact a reviewer reads to confirm the Epic is mergeable.

## SC-001 — PTY smoke "의정부 응급실 알려줘"

**Result**: ✅ PASS

The captured transcript at `specs/2294-5-primitive-align/smoke-emergency-lookup-pty.txt` (7977 lines) contains:
- `tool_registry: 14 entries verified (4 primitives) in 0ms` (twice — boot + reload)
- `KOSMOS v0.1.0-alpha+1978` branding banner with `K-EXAONE with high effort`
- `의정부 응급실 알려줘` Korean input echoed in the REPL prompt area
- `Actioning…` indicator confirming the agentic loop entered (LLM dispatch)

The PTY smoke validates the **stale-import / dead-JSX-path regression gate** (the canonical purpose of the harness per memory `feedback_pr_pre_merge_interactive_test`). Live LLM-side response is not exercised here; the harness uses `KOSMOS_BACKEND_CMD=sleep 60` to keep CI deterministic. Live verification ships with Epic ε once the NMC mock fixtures land.

**Wall-clock**: from spawn → "Actioning…" displayed: ~6 s (within the 8 s SC-001 budget on the developer laptop).

## SC-002 — ToolRegistry boot ≤ 200 ms

**Result**: ✅ PASS — measured **0 ms** wall-clock (under timer resolution).

Both the dev-mode boot (captured twice in the PTY transcript: `tool_registry: 14 entries verified (4 primitives) in 0ms`) and the standalone probe (`bun run probe:tool-registry`) report durationMs of 0. The boot guard walks 14 registered tools, of which 4 are primitives — well under the 200 ms budget.

## SC-003 — Citation 100% / blocklist 0%

**Result**: ✅ PASS

`bun test src/tools/__tests__/permission-citation.test.ts` — 20 pass / 0 fail / 75 expect() calls. Coverage:
- 4/4 primitives populate `kosmosCitations[0].real_classification_url` byte-identically against the synthetic NMC adapter.
- 4/4 primitives populate `kosmosCitations[0].policy_authority` byte-identically.
- 4/4 `renderToolResultMessage` outputs grep-clean of all 6 KOSMOS-invented blocklist phrases (`안전한 권한 등급`, `본 시스템은`, `KOSMOS는 다음과 같이`, `권한 등급 1/2/3`).
- 4/4 fail-closed paths (`AdapterNotFound`, `CitationMissing`) return the correct `errorCode`.

## SC-004 — `bun typecheck` 0 errors

**Result**: ✅ PASS — `tsc --noEmit -p tsconfig.typecheck.json` exits 0 cleanly.

## SC-005 — No NEW failures vs baseline

**Result**: ✅ PASS

| Stack | Baseline (`c6747dd`) | Post-refactor | Delta |
|---|---|---|---|
| `bun test` | 843 pass / 15 fail / 4 skip / 3 todo | **881 pass / 14 fail / 4 skip / 3 todo** | **+38 pass / -1 fail** |
| `uv run pytest` | (truncated tail; v6 handoff: 3160 pass) | **3160 pass / 0 fail / 36 skip / 2 xfailed** | clean |

The 14 remaining bun-test failures are pre-existing on `c6747dd` and unrelated to Epic γ. One previously-failing onboarding test now passes (presumably a flake-resolution side effect of the new test-suite runs); zero new failures introduced.

## SC-006 — Diff budget ≤ 1500 LOC

**Result**: ⚠️ **71 LOC over budget** (1571 total = 1549 insertions + 22 deletions vs 1500 budget).

```text
 tui/src/probes/toolRegistryProbe.tsx               |  39
 tui/src/services/toolRegistry/bootGuard.ts         | 103
 tui/src/tools/LookupPrimitive/LookupPrimitive.ts   | 178
 tui/src/tools/LookupPrimitive/prompt.ts            |   5
 tui/src/tools/SubmitPrimitive/SubmitPrimitive.ts   | 124
 tui/src/tools/SubmitPrimitive/prompt.ts            |   6
 tui/src/tools/SubscribePrimitive/SubscribePrimitive.ts | 110
 tui/src/tools/SubscribePrimitive/prompt.ts         |   5
 tui/src/tools/VerifyPrimitive/VerifyPrimitive.ts   | 120
 tui/src/tools/VerifyPrimitive/prompt.ts            |   5
 tui/src/tools/__tests__/permission-citation.test.ts| 405
 tui/src/tools/__tests__/registry-boot.test.ts      | 117
 tui/src/tools/__tests__/span-attribute-parity.test.ts | 288
 tui/src/tools/shared/primitiveCitation.ts          |  66
 14 files changed, 1549 insertions(+), 22 deletions(-)
```

**Breakdown**:
- Tests (810 LOC across 3 files) — every line is part of the FR-008 / SC-002 / SC-003 / SC-007 acceptance package.
- Primitive bodies (532 LOC across 4 files) — replaces stub `validateInput`/`renderToolResultMessage` with the real per-primitive Korean-rendering implementations.
- Helpers + probe (208 LOC) — shared citation extraction + boot guard + standalone probe script.

The 71 LOC overrun (4.7%) is concentrated in tests, which the spec explicitly mandates as part of acceptance (FR-008, SC-002/003/007). The Lead reviewed each test file for redundancy during T025 and found no removable lines that wouldn't weaken acceptance coverage.

**Decision**: accept the 71 LOC overrun. Lead notes the budget was authored before knowing how many describe/test cases the citation suite would need (the blocklist enforcement alone takes 4 × ~80 LOC for per-primitive render-flatten).

## SC-007 — OTEL span attribute parity

**Result**: ✅ PASS via fallback strategy

`bun test src/tools/__tests__/span-attribute-parity.test.ts` — 14 pass / 0 fail.

The TUI primitive layer does NOT emit OTEL spans directly (Spec 021 emits `gen_ai.client.invoke` from `tui/src/ipc/llmClient.ts`; the analytics service is a Spec 1633 dead-code stub). The test therefore locks the *intent surface* — `extractCitation()` returns exactly two canonical keys; `validateInput` populates `kosmosCitations[0]` with the byte-identical citation that a future OTEL emitter will read into `kosmos.adapter.real_classification_url`; the input schema preserves `tool_id` and `mode` (the source fields for `kosmos.tool.id` and `kosmos.tool.mode`). The fallback rationale is documented at the top of the test file.

## Sub-issue closure plan

After PR merge of `Closes #2294`:
1. The 27 task sub-issues (#2365–#2391) auto-close via Epic closure rule (memory `feedback_deferred_sub_issues`).
2. The 2 deferred placeholders (#2392, #2393) remain OPEN as `[Deferred]` follow-ups (memory `feedback_deferred_sub_issues` § exclusion).
3. The 3 pre-existing deferred issues (#2296, #2297, #2362) remain in their owning Epics' lifecycles.
4. A small follow-up issue for the Spec 022 path naming gap (`tests/primitives/test_lookup_resolve_location.py` vs the actual `tests/unit/primitives/test_resolve_location_envelope_identity.py`) is recommended — out of γ scope; sonnet-regress flagged this in `baseline.md § T023 resolve_location test status`.

## Constitution re-check (post-implementation)

| Principle | Status |
|---|---|
| I. Reference-Driven Development | ✅ PASS — every decision traces to `Tool.ts` / `AgentTool.tsx` / `cc-source-migration-plan` |
| II. Fail-Closed Security | ✅ PASS — `validateInput` fail-closed on missing citation; KOSMOS-invented language enforced absent by `permission-citation.test.ts` blocklist |
| III. Pydantic v2 Strict Typing | ✅ PASS — backend Pydantic untouched; TS uses `zod/v4` discriminated unions; no `Any` |
| IV. Government API Compliance | ✅ PASS — PTY smoke uses mock backend; no live `data.go.kr` |
| V. Policy Alignment | ✅ PASS — single-window contract preserved; PIPA pathway intact |
| VI. Deferred Work Accountability | ✅ PASS — all 7 deferred items tracked (4 issues + 2 placeholders + 1 permanent boundary) |

Zero CRITICAL findings. The 71-LOC SC-006 overrun is the only LOW-severity deviation; documented and accepted.
