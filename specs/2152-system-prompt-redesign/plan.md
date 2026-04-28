# Implementation Plan: KOSMOS System Prompt Redesign

**Branch**: `feat/2152-system-prompt-redesign` | **Date**: 2026-04-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/Users/um-yunsang/KOSMOS/specs/2152-system-prompt-redesign/spec.md`

## Summary

Migrate the Claude Code 2.1.88 system-prompt architecture (section-based static prefix + dynamic suffix + boundary marker + per-tool trigger guidance) from `.references/claude-code-sourcemap/restored-src/src/constants/prompts.ts` (lines 175–590, the `getSystemPrompt` 7-static / 12-dynamic composition) to the KOSMOS citizen-domain harness. The redesign rewrites `prompts/system_v1.md` as four XML-tagged sections (R1), augments the existing `build_system_prompt_with_tools` to emit per-tool trigger phrases (R6), excises the developer-context injectors (`getSystemContext` / `appendSystemContext` / `prependUserContext` / `getUserContext`) from the citizen TUI chat-request emit path (R5), wraps citizen utterances in a `<citizen_request>` envelope at the chat-request boundary (R3), inserts a `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` marker between the cacheable static prefix and the per-turn dynamic suffix while wiring `kosmos.prompt.hash` to hash only the static prefix (R4), and introduces a `kosmos.llm.prompt_assembler` module with a Pydantic-AI-style decorator surface for future per-turn injectors (R2). The work ships as a single integrated PR with zero new runtime dependencies.

## Technical Context

**Language/Version**: Python 3.12+ (backend, existing baseline) · TypeScript 5.6+ on Bun v1.2.x (TUI, existing Spec 287 stack). No version bump.
**Primary Dependencies**: All existing — `pydantic >= 2.13` (frozen models for `PromptSection` / `PromptAssemblyContext` / `SystemPromptManifest`), `pydantic-settings >= 2.0` (env catalog), `opentelemetry-sdk` + `opentelemetry-semantic-conventions` (Spec 021 spans, `kosmos.prompt.hash` attribute), `pytest` + `pytest-asyncio` (existing test stack), stdlib `hashlib` (SHA-256 prefix hash) / `pathlib` (PromptLoader I/O) / `re` (XML-tag presence assertions in tests). TS side: existing `ink`, `react`, `@inkjs/ui`, `string-width`, Bun stdlib. **Zero new runtime dependencies** (AGENTS.md hard rule + spec FR-012 + SC-6).
**Storage**: N/A at runtime. `prompts/system_v1.md` and `prompts/manifest.yaml` continue to live in the repository as the canonical source-of-truth (Spec 026 SHA-256 manifest invariant). The PromptLoader still loads them into an immutable in-memory cache at process boot. Dynamic-suffix injectors that pull from memdir USER tier (`~/.kosmos/memdir/user/consent/`, `~/.kosmos/memdir/user/ministry-scope/`) reuse the existing Spec 027 / Spec 035 paths.
**Testing**: `uv run pytest` (Python unit + integration) · `bun test` (TS parity + snapshot) · `expect`/`asciinema` text-log E2E TUI smoke (memory `feedback_vhs_tui_smoke` — text logs are primary, gif/png are auxiliary).
**Target Platform**: macOS / Linux terminal (TUI on Bun, backend on uv-managed Python 3.12+ over stdio JSONL IPC).
**Project Type**: Harness — split between Python backend (`src/kosmos/`) and Ink/React TUI (`tui/`) talking through stdio IPC frames (Spec 032).
**Performance Goals**: `kosmos.prompt.hash` byte-stable across two consecutive turns of the same session (cache prefix invariant, SC-3) · ≥ 3 of 5 citizen smoke scenarios trigger a tool call before the assistant's final answer (SC-1) · `bun test` ≥ 984 pass and `uv run pytest` ≥ 3458 pass (SC-5 parity with `main`).
**Constraints**: Zero new runtime dependencies (FR-012, SC-6, AGENTS.md hard rule) · English source text only with the approved Korean exception inside `<role>` and `<core_rules>` prose (constitution Development Standards) · Pydantic v2 only with `Any` forbidden in I/O schemas (constitution Principle III) · all `KOSMOS_`-prefixed env vars (AGENTS.md) · stdlib `logging` only with no `print()` outside CLI surfaces (AGENTS.md) · Spec 026 prompt-registry SHA-256 contract preserved (FR-013).
**Scale/Scope**: Single-user TUI session per process · ~12 registered citizen-data tools today (Spec 1637 catalog: `lookup`, `resolve_location`, KOROAD ×2, KMA ×6, HIRA ×1, NMC ×1, NFA119 ×1, MOHW ×1) · roughly 25–35 implementation tasks (≤ 90 sub-issue budget per memory `feedback_subissue_100_cap`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Constitution Principle | Status | Justification (each gate links a design decision back to a reference) |
|---|---|---|
| **I — Reference-Driven Development** | PASS | R1 cites `.references/claude-code-sourcemap/restored-src/src/constants/prompts.ts:175-590` (CC `getSystemPrompt` 7 static + 12 dynamic). R2 cites Pydantic AI `@agent.system_prompt` decorator (`docs/research/system-prompt-harness-comparison.md §4.2`). R3 cites Anthropic prompt-engineering guide §8.2 (XML tags). R4 cites `prompts.ts:572-575` (`SYSTEM_PROMPT_DYNAMIC_BOUNDARY`). R5 cites `restored-src/src/context.ts` `getSystemContext` definition. R6 cites Anthropic guide §"Tool use triggering" (Opus 4.7 uses tools less than 4.6 → describe why and how clearly). Constitution Principle I "Mandatory reference mapping" — Context Assembly row (Claude Code reconstructed primary, Anthropic docs secondary) — is satisfied verbatim. |
| **II — Fail-Closed Security** | PASS | This Epic does NOT touch any tool adapter, permission gauntlet, or auth path. The new prompt-assembler module reads only static prompt text and existing memdir USER tier paths (already permission-bound by Spec 027 / Spec 035). No new `requires_auth=False`, no new `is_personal_data=False`, no permission bypass. The `<citizen_request>` wrap (R3) is a defensive prompt-injection guard — strengthens, not weakens, fail-closed posture. |
| **III — Pydantic v2 Strict Typing** | PASS | All new types (`PromptSection`, `PromptAssemblyContext`, `SystemPromptManifest`, `ToolTriggerPhrase`) are Pydantic v2 frozen models with explicit fields. No `Any` in any I/O schema. The `prompt_assembler` decorator surface uses generic `Callable[[PromptAssemblyContext], str \| None]` — fully typed. |
| **IV — Government API Compliance** | PASS (NOT APPLICABLE) | This Epic does not add or modify any government-API adapter. No live `data.go.kr` calls in CI; no quota changes; no key handling. Per-tool trigger phrases (R6) reference adapter names (`kma_forecast_fetch`, `hira_hospital_search`, etc.) but do not invoke them. |
| **V — Policy Alignment** | PASS | The new `<role>` prose explicitly frames the assistant as a Korean public-service intermediary that consolidates cross-ministry citizen services into a single conversational window — direct alignment with Korea AI Action Plan Principle 8 (single conversational window). The R5 dev-context excision honours Principle 5 (consent-based access — citizens never receive developer surveillance metadata they did not consent to). PIPA: no new personal-data flows; existing 7-step gauntlet untouched. |
| **VI — Deferred Work Accountability** | PASS | spec.md "Scope Boundaries & Deferred Items" section is present and populated. Out of Scope (Permanent) lists 4 items with brief reasons. Deferred to Future Work table lists 4 items each with `Reason for Deferral`, `Target Epic/Phase`, and `Tracking Issue` set to `NEEDS TRACKING` (will be resolved by `/speckit-taskstoissues`). spec.md prose contains no unregistered "future epic" / "v2" / "Phase 2+" / "deferred to" patterns outside the table — verified by Phase 0 deferred-item validation in research.md. |

**Result**: All six gates PASS at Phase 0 entry. No Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/2152-system-prompt-redesign/
├── plan.md              # This file
├── spec.md              # Feature specification (already authored by /speckit-specify)
├── research.md          # Phase 0 output — R1–R6 reference mapping + deferred-item validation
├── data-model.md        # Phase 1 output — PromptSection / PromptAssemblyContext / etc.
├── quickstart.md        # Phase 1 output — how to use prompt_assembler + verification commands
├── contracts/           # Phase 1 output
│   ├── prompt-assembler.md         # Decorator surface + assembly contract
│   ├── system-prompt-builder.md    # build_system_prompt_with_tools R6 extension
│   └── chat-request-envelope.md    # R3 citizen_request wrap at the IPC boundary
├── checklists/
│   └── requirements.md  # Spec quality checklist (already authored)
└── tasks.md             # Created by /speckit-tasks (NOT this command)
```

### Source Code (repository root)

```text
prompts/
├── system_v1.md                                  # R1 — rewrite as XML-tagged 4 sections
└── manifest.yaml                                 # R1 — update SHA-256 for system_v1.md

src/kosmos/llm/
├── system_prompt_builder.py                      # R6 — strengthen build_system_prompt_with_tools
│                                                 #     to emit per-tool trigger phrase line
├── prompt_assembler.py                           # R2 — NEW module — Pydantic-AI-style decorator
│                                                 #     surface for dynamic suffix injectors;
│                                                 #     emits SYSTEM_PROMPT_DYNAMIC_BOUNDARY (R4)
└── _cc_reference/
    └── prompts.ts                                # CC reference mirror (read-only)

src/kosmos/ipc/
└── stdio.py                                      # R3 — wrap user msg in <citizen_request>
                                                  # R4 — emit BOUNDARY marker between
                                                  #      static prefix and dynamic suffix in
                                                  #      _handle_chat_request system assembly

src/kosmos/observability/
└── prompt_hash.py                                # R4 — hash ONLY the static prefix into
                                                  #      kosmos.prompt.hash (extend if exists,
                                                  #      else fold into prompt_assembler)

tui/src/
├── ipc/llmClient.ts                              # passthrough (already correct from PR #2151);
│                                                 # add static-prefix-only hash assertion in tests
├── utils/api.ts                                  # R5 — drop appendSystemContext /
│                                                 #      prependUserContext from chat-request path
├── utils/queryContext.ts                         # R5 — remove getSystemContext / getUserContext
│                                                 #      Promise.all from chat-request callers
├── query.ts                                      # R5 — remove appendSystemContext call
├── screens/REPL.tsx                              # R5 — remove getSystemContext / getUserContext
│                                                 #      from chat-request emit path warm-paths
├── main.tsx                                      # R5 — remove void getSystemContext() prefetch
└── tools/AgentTool/runAgent.ts                   # UNTOUCHED — agent tool legitimately consumes
                                                  # developer context inside its own module;
                                                  # this Epic does not affect it.

tests/llm/
├── test_prompt_assembler.py                      # NEW — decorator registration / boundary
│                                                 # marker / static-prefix byte-stability /
│                                                 # dynamic-suffix recompute / cache invariant
├── test_system_prompt_builder.py                 # EXTEND — per-tool trigger phrase emission
│                                                 # (R6) + empty-tools no-op invariant (FR-015)
└── test_prompt_loader.py                         # EXTEND — manifest SHA-256 round-trip after
                                                  # system_v1.md rewrite

tests/ipc/
└── test_stdio_chat_request.py                    # EXTEND — <citizen_request> wrap presence
                                                  # (R3) + SYSTEM_PROMPT_DYNAMIC_BOUNDARY presence
                                                  # in assembled prompt (R4)

tui/src/__tests__/
├── chatRequestEmit.test.ts                       # NEW — assert no developer context attached
│                                                 # to chat_request frame (R5 / SC-4)
└── promptCacheStability.test.ts                  # NEW — assert kosmos.prompt.hash byte-stable
                                                  # across 2 turns (R4 / SC-3)

specs/2152-system-prompt-redesign/
├── smoke.txt                                     # E2E text log (5 scenarios)
└── smoke-scenario-{1..5}-*.txt                   # Per-scenario asciinema logs
```

**Structure Decision**: KOSMOS is a single-repo polyglot harness with two long-lived top-level source trees: `src/kosmos/` (Python backend) and `tui/src/` (Ink/React TUI on Bun). This Epic touches both — the prompt-assembler and IPC envelope wiring live in Python; the developer-context excision lives in TUI. No new top-level directories; no `apps/` or `packages/` split needed. The existing layout already enforces the "harness, not reimplementation" rule (memory `feedback_harness_not_reimplementation`) — `_cc_reference/` mirrors stay read-only and unchanged.

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.
