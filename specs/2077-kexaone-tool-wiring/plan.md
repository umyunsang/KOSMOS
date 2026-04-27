# Implementation Plan: K-EXAONE Tool Wiring (CC Reference Migration)

**Branch**: `2077-kexaone-tool-wiring` | **Date**: 2026-04-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/2077-kexaone-tool-wiring/spec.md`
**Epic**: [#2077](https://github.com/umyunsang/KOSMOS/issues/2077)
**Handoff**: [handoff-prompt.md](./handoff-prompt.md) (line-cited diagnosis + 7-step migration recipe)

## Summary

K-EXAONE today hallucinates Claude Code training-data tools (`Read`, `Glob`, `Bash`, …) because the platform never tells it which tools actually exist. The TUI's `ChatRequestFrame` carries no `tools` field, the backend has no fallback registry inject, and `prompts/system_v1.md` carries no inline tool catalog. As a result, the LLM sees `tools=None` and falls back to its training memory.

The migration restores the Claude Code "tool inventory + agentic loop" pattern in three layers — (1) the TUI serializes its primitive catalogue into `ChatRequestFrame.tools`, (2) the backend appends an authoritative `## Available tools` section to the system prompt **and** falls back to `ToolRegistry.export_core_tools_openai()` whenever the frame omits tools, (3) the TUI projects every `tool_call` / `tool_result` / `permission_request` frame into the canonical Claude Code `stream_event{content_block_*}` shape so the existing native components (`AssistantToolUseMessage`, `PermissionGauntletModal`) finally light up. Every change is migrated from `src/kosmos/llm/_cc_reference/` (the local read-only copy of `.references/claude-code-sourcemap/restored-src/src/`) — no new abstractions, no new runtime dependencies.

## Technical Context

**Language/Version**: Python 3.12+ (backend) · TypeScript 5.6+ on Bun v1.2.x (TUI). No version bump.
**Primary Dependencies**: All existing — `pydantic >= 2.13`, `pydantic-settings >= 2.0`, `httpx >= 0.27`, `opentelemetry-sdk`, `opentelemetry-semantic-conventions`, `pytest`, `pytest-asyncio` (Python); `ink`, `react`, `zod ^3.23` (resolves to 3.25.76, ships `zod/v4` preview namespace), `@modelcontextprotocol/sdk` (TS). **Zero new runtime dependencies** — AGENTS.md hard rule. JSON Schema conversion uses `zod/v4`'s built-in `z.toJSONSchema()` which emits Draft 2020-12 natively (verified at plan-time, see `research.md § R-1`).
**Storage**: N/A. In-memory `ToolRegistry` (rebuilt on backend boot, Spec 1634), session JSONL transcripts at `~/.kosmos/memdir/user/sessions/` (Spec 027 unchanged), audit ledger entries appended to existing `~/.kosmos/memdir/user/consent/` (Spec 035 unchanged). No new on-disk schemas.
**Testing**: `uv run pytest tests/llm tests/ipc tests/tools` (Python); `bun test` for TUI; PTY harness at `/tmp/run_pty_tool_e2e.py` for citizen-perspective verification; VHS GIF recipe in `quickstart.md` for visual capture.
**Target Platform**: Local terminal (POSIX-only — macOS / Linux). Backend Python process spawned by TUI via stdio JSONL IPC (Spec 032).
**Project Type**: KOSMOS standard dual-layer (Python backend `src/kosmos/`, TypeScript TUI `tui/src/`).
**Performance Goals**: Per spec — SC-002 30 s end-to-end (citizen prompt → tool_use box → tool_result envelope → final answer paint), SC-003 1 s consent prompt appearance, SC-007 ≥ 95 % first-attempt success rate over a 20-attempt rehearsal.
**Constraints**: FriendliAI Tier 1 60 RPM upstream cap. Composite/macro tools forbidden (Migration Tree § L1-B.B6 — primitives chain instead). Korean-primary citizen copy with English fallback (Migration Tree § UI-A.A.3). PIPA §26 trustee semantics on every gated invocation (`project_pipa_role`).
**Scale/Scope**: ~25-35 sub-tasks (handoff §6 7 steps × 3-5 sub-tasks). Code surface: 9 CC reference cp + index README · 1 new Python module (`system_prompt_builder.py`) · 1 modified Python module (`stdio.py` — registry fallback + system-prompt inject + whitelist source-of-truth migration) · 1 new TS module (`toolSerialization.ts`) · 2 modified TS modules (`deps.ts` projection, `sessionStore.ts` pending-permission slot) · 4-5 new test files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I — Reference-Driven Development ✓

Every step maps to a concrete reference in `_cc_reference/`. Layer mapping:

| Step | Layer | Primary reference (`_cc_reference/...`) | Secondary reference |
|---|---|---|---|
| Step 2 (TUI tool serialization) | Tool System | `api.ts:toolToAPISchema()` (line 119-266) · `tools.ts:assembleToolPool()` (line 345-367) | Pydantic AI (registry rationale) |
| Step 3 (system prompt inject) | Context Assembly | `api.ts:appendSystemContext()` · `prompts.ts` dynamic composition | Anthropic prompt-caching docs |
| Step 4 (registry fallback) | Tool System | `tools.ts:assembleToolPool()` | Pydantic AI |
| Step 5 (tool_use stream_event projection) | Query Engine | `claude.ts:1995-2052` (content_block_start tool_use case) · `messages.ts:normalizeContentFromAPI()` | Claude Agent SDK (async generator) |
| Step 6 (tool_result content block) | Query Engine | `messages.ts:ensureToolResultPairing()` (line 1150-1250) | Claude Agent SDK |
| Step 7 (consent modal wire) | Permission Pipeline | `permissions.ts` (1486 lines) | OpenAI Agents SDK guardrail |
| Step 1 (CC ref cp) | (cross-layer) | All 9 files cp from `.references/claude-code-sourcemap/restored-src/` with research-use header | Constitution §I file-lift policy |

Each cp file carries a one-line header citing upstream path + version `2.1.88` + research-use notice (constitution §I). The KOSMOS-original code adapts the patterns; line-for-line copy is forbidden except inside `_cc_reference/`.

### Principle II — Fail-Closed Security (NON-NEGOTIABLE) ✓

The consent modal wire (Step 7) only adds *interactivity* — it never relaxes any gate.

- Gated primitives (`submit`, `subscribe`) remain gated. Today they auto-deny; after the change they ask the citizen but the default-on-timeout outcome is still **deny** (FR-017).
- The bypass-immune permission steps from Spec 033 (cross-citizen records, medical records without consent, write-without-identity) are **not** touched by this epic. Modal interactivity sits on top of the existing gate; it cannot remove a gate.
- `requires_auth = True`, `is_personal_data = True`, `is_concurrency_safe = False`, `cache_ttl_seconds = 0` defaults preserved across all adapter changes.

### Principle III — Pydantic v2 Strict Typing (NON-NEGOTIABLE) ✓

- `ChatRequestFrame.tools` already typed as `list[ToolDefinition]` (Pydantic v2, Spec 032 frame schema).
- New backend module `system_prompt_builder.py` consumes the existing `LLMToolDefinition` Pydantic model — no new schemas, no `Any`.
- TUI side uses `zod/v4` schemas (already in repo). `toolToFunctionSchema()` calls `z.toJSONSchema()` directly; the result is a strict JSON Schema 2020-12 object — no `unknown` cast paths bypass the schema.
- Existing `LookupPrimitive` / `SubmitPrimitive` / `VerifyPrimitive` / `SubscribePrimitive` Zod schemas remain canonical client-side validators; nothing is loosened.

### Principle IV — Government API Compliance ✓

This epic touches the LLM↔tool edge, not adapter call paths. No live `data.go.kr` invocations are added. Existing rate-limit + usage-tracker behavior on adapters is unaffected. `KOSMOS_*` env-var contract preserved (no new vars introduced beyond existing `KOSMOS_LLM_*` and `KOSMOS_PERMISSION_*`).

### Principle V — Policy Alignment ✓

- Korea AI Action Plan **Principle 8** (single conversational window): the change *enables* it — today the agent cannot route across ministries because it cannot reach KOSMOS tools at all.
- **Principle 9** (Open API + OpenMCP): KOSMOS tool definitions are emitted in OpenAI-compatible function-call shape (already used by `_dispatch_primitive` and FriendliAI's API), preserving MCP interop trajectory.
- **Public AI Impact Assessment (과제 54)**: explainability — Step 5+6 give citizens a transparent audit trail of every tool the agent used.
- **PIPA §26 trustee semantics** (`project_pipa_role`): the consent modal records the explicit citizen grant required for every personal-data flow.

### Principle VI — Deferred Work Accountability ⚠️ → ✓ (resolved in Phase 0)

`spec.md § Scope Boundaries & Deferred Items` declares:

- 2 entries reference open epics (#1979, #1980) — verified open at plan-time (`research.md § R-7`).
- 5 entries marked `NEEDS TRACKING` — placeholders to be resolved by `/speckit-taskstoissues`.

Phase 0 scans `spec.md` for unregistered "separate epic" / "future phase" / "v2" patterns and confirms every match has a row in the deferred-items table.

**Gate result**: PASS (no constitution violation) — the `Complexity Tracking` section is empty.

## Project Structure

### Documentation (this feature)

```text
specs/2077-kexaone-tool-wiring/
├── plan.md                # this file
├── spec.md                # /speckit-specify output (citizen-facing user stories + FRs + SCs)
├── handoff-prompt.md      # line-cited diagnosis + 7-step recipe (cold-start session input)
├── research.md            # Phase 0 — references + Zod toJSONSchema decision + deferred-item validation
├── data-model.md          # Phase 1 — entity model (ToolDefinition envelope, ToolUse content block, ToolResult content block, PendingPermission slot)
├── quickstart.md          # Phase 1 — PTY E2E + VHS GIF citizen-perspective verification recipe
├── contracts/             # Phase 1 — interface contracts
│   ├── chat-request-frame.md           # ChatRequestFrame.tools field shape (TUI → backend)
│   ├── system-prompt-builder.md        # build_system_prompt_with_tools() Python contract
│   ├── tool-serialization.md           # toolToFunctionSchema() TS contract (Zod → JSON Schema 2020-12)
│   ├── stream-event-projection.md      # tool_call / tool_result frame → CC stream_event projection
│   └── pending-permission-slot.md      # sessionStore.setPendingPermission() + waitForDecision() Promise contract
├── checklists/
│   └── requirements.md    # /speckit-specify validation results
└── tasks.md               # (created by /speckit-tasks — NOT this command)
```

### Source Code (repository root)

```text
src/kosmos/llm/
├── _cc_reference/                       # CC 2.1.88 read-only copies (Constitution §I file-lift)
│   ├── claude.ts                        # cp'd in fdfd3e9 (3419 lines — streaming + agentic loop)
│   ├── client.ts                        # cp'd in fdfd3e9 (389 lines)
│   ├── errors.ts                        # cp'd in fdfd3e9 (1207 lines)
│   ├── emptyUsage.ts                    # cp'd in fdfd3e9 (22 lines)
│   ├── api.ts                           # NEW (cp 718 lines — toolToAPISchema, appendSystemContext)
│   ├── tools.ts                         # NEW (cp 389 lines — assembleToolPool, getAllBaseTools)
│   ├── prompts.ts                       # NEW (cp 914 lines — dynamic system prompt composition)
│   ├── query.ts                         # NEW (cp 1729 lines — multi-turn closure)
│   ├── toolOrchestration.ts             # NEW (cp 188 lines — runTools async generator)
│   ├── toolExecution.ts                 # NEW (cp 1745 lines — runToolUse, ToolResultBlockParam serialization)
│   ├── messages.ts                      # NEW (cp 5512 lines — normalizeContentFromAPI, ensureToolResultPairing)
│   ├── permissions.ts                   # NEW (cp 1486 lines — permission gauntlet)
│   ├── toolResultStorage.ts             # NEW (cp 1040 lines — token budgeting, processToolResultBlock)
│   └── README.md                        # NEW — index + KOSMOS migration mapping
└── system_prompt_builder.py             # NEW — build_system_prompt_with_tools() (Step 3)

src/kosmos/ipc/
└── stdio.py                             # M — Step 3 system-prompt inject + Step 4 registry fallback + whitelist source-of-truth migration

src/kosmos/tools/
└── registry.py                          # M (only if export_core_tools_openai needs MVP-7 enrichment) — Step 4

tui/src/query/
├── deps.ts                              # M — frame.tools spread (Step 2) + tool_call/tool_result/permission_request CC stream_event projection (Steps 5-7)
└── toolSerialization.ts                 # NEW — toolToFunctionSchema() + getToolDefinitionsForFrame() (Step 2)

tui/src/store/
└── sessionStore.ts                      # M — pending-permission slot + waitForPermissionDecision() Promise (Step 7)

tests/llm/
└── test_system_prompt_builder.py        # NEW — Step 3 unit + system-prompt inject contract

tests/ipc/
└── test_stdio.py                        # M — Step 3+4 fallback + system-prompt inject scenarios

tui/tests/tools/
└── serialization.test.ts                # NEW — toolToFunctionSchema invariants (Step 2)

tui/tests/ipc/
└── handlers.test.ts                     # M — deps.ts new branches (Steps 5-7)

tui/tests/store/
└── sessionStore.test.ts                 # M (or NEW) — pending-permission slot lifecycle (Step 7)
```

**Structure Decision**: KOSMOS standard dual-layer (Python backend + TypeScript TUI). The migration cleanly partitions across the two layers — backend changes affect inventory generation and dispatch only, TUI changes affect ChatRequestFrame composition and stream-event projection only. Both ends communicate exclusively over the existing Spec 032 stdio JSONL envelope; no new IPC frame arms are introduced (assumed in spec).

## Complexity Tracking

> **Empty — no constitution violations to justify.** Every step maps to an existing reference layer and an existing dependency. The `_cc_reference/` cp is explicitly sanctioned by Constitution §I; the modifications adapt the patterns rather than duplicate them.
