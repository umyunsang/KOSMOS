# Implementation Plan: P1+P2 · Dead code + Anthropic → FriendliAI migration

**Branch**: `1633-dead-code-friendli-migration` | **Date**: 2026-04-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `./spec.md`
**Epic**: [#1633](https://github.com/umyunsang/KOSMOS/issues/1633)
**Phase 0 research**: [research.md](./research.md)
**Data model**: [data-model.md](./data-model.md)
**Contracts**: [contracts/llm-client.md](./contracts/llm-client.md)
**Quickstart**: [quickstart.md](./quickstart.md)

## Summary

Rewire TUI's LLM path from Anthropic to FriendliAI EXAONE by (a) deleting Anthropic-specific assets (OAuth + Keychain + analytics + CC version migrations + teleport + policy limits + MCP Anthropic integration), (b) replacing `@anthropic-ai/sdk` consumption points with a new `tui/src/ipc/llmClient.ts` that round-trips LLM turns over Spec 032 stdio IPC to the existing Python `LLMClient`, and (c) wiring Spec 026 PromptLoader into the system-prompt path. The agentic loop in `query.ts`/`QueryEngine.ts` is preserved 1:1 (rewrite boundary, Constitution Principle I). Model ID fixes to `LGAI-EXAONE/EXAONE-236B-A23B` (Python config default also updated).

## Technical Context

**Language/Version**: TypeScript 5.6+ (TUI layer, Bun v1.2.x runtime, existing from Spec 287); Python 3.12+ (backend, existing). No version bump.
**Primary Dependencies**: TS — existing Bun stdlib + Ink + React; no new JS deps. Python — existing `httpx >= 0.27`, `pydantic >= 2.13`, `pydantic-settings >= 2.0`, `opentelemetry-sdk`, `opentelemetry-semantic-conventions`. **Zero new runtime dependencies** (AGENTS.md hard rule).
**Storage**: N/A at feature layer. Session JSONL stays in `~/.kosmos/memdir/user/sessions/` (Spec 027); OTEL spans flow via Spec 028 OTLP collector to local Langfuse. No schema changes.
**Testing**: `bun test` (TUI, existing), `uv run pytest` (Python, existing). Epic P0 floor ≥ 540 TS tests preserved. New test targets: SC-based grep invariants (add to CI), `LLMClient` unit tests (mocked bridge), end-to-end resume smoke (Spec 032-backed).
**Target Platform**: Developer / contributor terminals (Linux + macOS). TUI runs under Bun; Python backend under uv-managed virtualenv.
**Project Type**: Bi-lingual monorepo — TS TUI (`tui/`) + Python backend (`src/kosmos/`). No new project directories.
**Performance Goals**: First-streaming-token latency ≤ 5 s (SC-001). Stream throughput bounded by FriendliAI Serverless + stdio bridge (no additional budget).
**Constraints**: Hard — (a) no direct HTTPS from TS runtime; (b) no `@anthropic-ai/sdk` runtime imports; (c) fail-closed on missing `FRIENDLI_API_KEY`; (d) `main.tsx` ≤ 2,500 lines; (e) zero external egress other than FriendliAI (Spec 021 A7).
**Scale/Scope**: ~50 TS files deleted, ~5 TS files added/rewired, 1 Python line changed (`config.py:37`), ~137 Anthropic SDK import edits, `main.tsx` reduction ~4,693 → ≤ 2,500 lines.

## Constitution Check

*GATE — must pass before Phase 1, re-checked post-design.*

| Principle | Requirement | Status | Evidence |
|---|---|---|---|
| **I. Reference-Driven Development** | Every design decision traces to a concrete reference in `docs/vision.md § Reference materials` or restored-src. | ✅ PASS | Research Decision 4/5/8 cite Spec 032 frames.generated.ts + Spec 021 + Spec 026. `QueryEngine.ts` / `query.ts` rewire honors the rewrite-boundary rule ("`services/api/*` only goes to Python over stdio JSONL"). |
| **II. Fail-Closed Security** | Most-restrictive defaults at system boundaries. | ✅ PASS | Fail-closed boot without `FRIENDLI_API_KEY` (contract § 5). No Anthropic credentials looked up anywhere. SC-009 validates no external egress beyond FriendliAI. |
| **III. Pydantic v2 Strict Typing** | All tool I/O via Pydantic v2 models; no `Any`. | ✅ PASS (N/A mostly) | This Epic does not add tool adapters. The IPC frame schema is already Pydantic v2 (Spec 032); TS type shim mirrors but does not produce `Any`. |
| **IV. Government API Compliance** | No live `data.go.kr` from CI; per-key quota; fixtures; no hardcoded keys. | ✅ PASS | Epic touches LLM path only; no ministry adapters modified. `FRIENDLI_API_KEY` stays env-var only. |
| **V. Policy Alignment** | Korea AI Action Plan P8/P9; PIPA gauntlet. | ✅ PASS | Permission pipeline untouched. FriendliAI rewire enables the single-conversational-window (P8) product direction. |
| **VI. Deferred Work Accountability** | Every scope exclusion tracked with a GitHub issue or `NEEDS TRACKING`. | ✅ PASS | Research § "Deferred Items validation" enumerates 8 rows, all with tracking markers. PLAN-PHASE-0 markers (`filesApi.ts`, `promptCacheBreakDetection.ts`) resolved in this plan. |

**Initial gate**: PASS. **Post-design gate** (re-evaluated after Phase 1): PASS (no violations introduced by design artifacts).

## Project Structure

### Documentation (this feature)

```text
specs/1633-dead-code-friendli-migration/
├── plan.md                        # This file (/speckit-plan output)
├── spec.md                        # Feature specification (/speckit-specify output)
├── research.md                    # Phase 0 research (9 + 4 decisions resolved)
├── data-model.md                  # Spec 032 frame reuse for LLM turns
├── quickstart.md                  # Reproducible end-to-end validation
├── checklists/
│   └── requirements.md            # Spec quality checklist (all pass)
└── contracts/
    └── llm-client.md              # TS LLMClient interface + IPC LLM turn protocol
```

### Source Code (repository root — files this Epic touches)

```text
src/kosmos/llm/
└── config.py                      # [EDIT 1 line] default model ID

tui/src/                           # TS TUI — most of this Epic's surface
├── main.tsx                       # [EDIT] strip ant-guards, simplify boot → ≤ 2500 lines
├── query.ts                       # [EDIT] remove @anthropic-ai/sdk type imports
├── QueryEngine.ts                 # [EDIT] remove @anthropic-ai/sdk type imports
├── ipc/                           # [EXTEND] new LLM client on existing bridge
│   ├── bridge.ts                  # (existing, Spec 032)
│   ├── envelope.ts                # (existing, Spec 032)
│   ├── codec.ts                   # (existing, Spec 032)
│   ├── frames.generated.ts        # (existing, Spec 032; no change)
│   ├── tx-registry.ts             # (existing, Spec 032)
│   ├── llmClient.ts               # [NEW] LLMClient class (contract § 1)
│   └── llmTypes.ts                # [NEW] Kosmos* type surface (contract § 2)
├── migrations/                    # [DELETE] 11 CC version migrations
├── services/
│   ├── analytics/                 # [DELETE] 7 files (growthbook, datadog, firstParty, sink, metadata, index, sinkKillswitch)
│   ├── api/                       # [MIXED] keep withRetry/errors/errorUtils/promptCacheBreakDetection (rewired); delete bootstrap/usage/overageCreditGrant/referral/adminRequests/grove/filesApi/claude/client; rewire via llmClient
│   ├── claudeAiLimits.ts          # [DELETE]
│   ├── claudeAiLimitsHook.ts      # [DELETE] (Finding C)
│   ├── internalLogging.ts         # [DELETE]
│   ├── mcp/claudeai.ts            # [DELETE]
│   ├── oauth/                     # [DELETE] 5 files
│   ├── policyLimits/              # [DELETE] directory
│   └── remoteManagedSettings/
│       └── securityCheck.tsx      # [DELETE]
├── utils/
│   ├── auth.ts                    # [DELETE]
│   ├── betas.ts                   # [DELETE]
│   ├── modelCost.ts               # [DELETE]
│   ├── secureStorage/             # [DELETE] 6 files
│   ├── telemetry/                 # [DELETE] 5 files
│   ├── teleport.tsx               # [DELETE]
│   ├── teleport/gitBundle.ts      # [DELETE]
│   ├── background/remote/         # [DELETE] 2 files
│   └── model/
│       ├── antModels.ts           # [DELETE]
│       └── model.ts               # [EDIT] getDefaultMainLoopModel returns "LGAI-EXAONE/EXAONE-236B-A23B"
├── constants/
│   └── betas.ts                   # [DELETE] (Finding C)
├── commands/
│   ├── login/                     # [DELETE]
│   └── logout/                    # [DELETE]
├── components/
│   └── TeleportResumeWrapper.tsx  # [DELETE]
├── hooks/
│   └── useTeleportResume.tsx      # [DELETE]
├── remote/                        # [DELETE] 4 files
├── types/types/generated/
│   └── events_mono/               # [DELETE] generated event types
└── entrypoints/
    └── init.ts                    # [EDIT] replace initializeTelemetryAfterTrust with KOSMOS OTEL init
```

**Structure Decision**: Monorepo (TUI + Python backend) layout from Epic P0 is preserved. This Epic is subtractive on TUI (~50 deletions) plus two new TS files in `tui/src/ipc/`. One Python line change (`config.py:37`). No new top-level directories.

## Phase 0 (complete)

See [research.md](./research.md). All 9 PLAN-PHASE-0 items resolved; 4 late-discovery findings documented and folded back into the plan.

## Phase 1 (complete)

Artifacts generated:
- **[data-model.md](./data-model.md)** — Frame reuse strategy (no schema changes); TS type translation layer outline.
- **[contracts/llm-client.md](./contracts/llm-client.md)** — `LLMClient` class contract + `llmTypes.ts` types + IPC happy/tool-use/error/rate-limit sequences + OTEL attribute table + fail-closed boot contract + P3 compatibility shim.
- **[quickstart.md](./quickstart.md)** — Setup, Scenario 1 (citizen UX), Scenario 2 (fail-closed), Scenario 3 (contributor invariants), Scenario 4 (Spec 032 resume), CI harness.
- Agent context update: pending — will run `.specify/scripts/bash/update-agent-context.sh claude` in the finalization step below.

## Phase 2 — Task generation strategy (preview)

> **Executed by `/speckit-tasks`, not this command.** Listed here so reviewers understand the downstream shape.

Task categories (expected):

1. **Delete** category (~40 tasks, one per deletion target file or directory). Parallel-safe.
2. **Rewire** category (~10 tasks): `model.ts:206` return value, `config.py:37` default, `init.ts` OTEL swap, `query.ts` + `QueryEngine.ts` type-import removal.
3. **New file** category (~4 tasks): `llmClient.ts`, `llmTypes.ts`, compatibility shims for `filesApi` callers (P3 bridge).
4. **Test** category (~8 tasks): `LLMClient` unit tests, contract tests, SC invariant CI tasks, resume regression test.
5. **Slash cleanup** (~3 tasks): delete `/login`+`/logout`, update help, update onboarding.

Expected total: **60-70 tasks**, well under the Sub-Issues 90-budget (AGENTS.md `Sub-Issue 100-cap` rule).

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

**None.** All gates passed in the Constitution Check table above; no justifications required.

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Epic #1632 tools depending on deleted files | Medium | Build break | Compatibility shim (contracts § 6) keeps P3 tool files compiling until Epic #1634 |
| FriendliAI EXAONE-236B-A23B model ID renamed / deprecated | Low | SC-010 fails | Plan treats model ID as a **single constant** in one Python config line; rename requires one-line edit + release-manifest bump (Spec 026). FriendliAI partnership status (Day-0 support) suggests stable naming. |
| Spec 032 backpressure didn't anticipate FriendliAI 429 volume | Medium | Throttling UX | Existing `BackpressureSignal(kind=llm_rate_limit)` already designed for this; Python-side retry from Spec 019 is battle-tested |
| TS tests referencing `@anthropic-ai/sdk` types | High | Mass test failures | Type shim in `llmTypes.ts` provides structural equivalents; tests compile without edit as long as imports are updated |
| `main.tsx` ≤ 2,500 line target unreachable | Low | SC-003 miss | Current file is 4,693 lines; removing ant-guards (58+ sites) + login/logout boot + telemetry init + CC version migrations easily yields > 2,000 line reduction per `grep -c` estimates |
| Disabling Anthropic OAuth leaves orphan imports | Medium | Compile error | Hard-dependency check: `grep '@anthropic-ai/sdk' tui/src` must be 0 before PR merge (Epic #1633 Acceptance Criteria) |

## Acceptance gate before `/speckit-tasks`

- [x] `research.md` complete — 9 + 4 decisions resolved
- [x] `data-model.md` complete — frame-reuse strategy locked
- [x] `contracts/llm-client.md` complete — TS + IPC contract documented
- [x] `quickstart.md` complete — reproducible validation path
- [x] Constitution Check gates all PASS (pre-design + post-design)
- [x] No unresolved `NEEDS CLARIFICATION` markers
- [x] Deferred Items validated (Constitution Principle VI)

**Result**: Proceed to `/speckit-tasks`.

## References

- `spec.md` — what we're building
- `research.md` — why these decisions
- `data-model.md` — how LLM turns pack into Spec 032 frames
- `contracts/llm-client.md` — the TS surface + IPC protocol
- `quickstart.md` — how to verify
- `docs/vision.md § 28-44` · `§ L1-A`
- `docs/requirements/kosmos-migration-tree.md § L1-A · § Execution Phase`
- `docs/requirements/epic-p1-p2-llm.md`
- `.specify/memory/constitution.md` v1.1.1
- Spec 019 · 021 · 026 · 028 · 032 · 035
- FriendliAI public docs (2026-04-24 snapshot) — model catalog, chat-completions usage fields
