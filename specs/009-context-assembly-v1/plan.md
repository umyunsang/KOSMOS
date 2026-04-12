# Implementation Plan: Context Assembly v1 (Layer 5)

**Branch**: `feat/009-context-assembly-v1` | **Date**: 2026-04-13 | **Spec**: [spec.md](./spec.md)
**Input**: Epic #9 — Context Assembly v1 (Layer 5)

---

## Summary

Layer 5, Context Assembly, owns the complete layered prompt that the LLM receives on every turn. V1 introduces a `ContextBuilder` class that replaces the hardcoded `_DEFAULT_SYSTEM_PROMPT` constant in `QueryEngine`, assembles deterministic system messages, injects per-turn dynamic attachments, partitions tool schemas into cache-stable prefix and dynamic suffix, and enforces a token budget guard before each LLM call.

The core design invariant is **cache prefix stability**: core tool schemas and the system prompt must occupy a stable byte-identical prefix so that the FriendliAI prompt cache is not invalidated between citizen turns. Dynamic content — attachments, situational tools — is appended after the stable prefix. This directly applies the finding from arXiv 2601.06007 that cache-boundary discipline yields 41–80% encoding cost reduction in sessions with 30–50+ tool calls.

---

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: `pydantic >= 2.0` (frozen models, validators), `pydantic-settings >= 2.0` (config), `httpx >= 0.27` (async HTTP, existing), `pytest` + `pytest-asyncio` (tests)
**Storage**: N/A — in-memory session state only; `ContextBuilder` is stateless
**Testing**: `uv run pytest` — unit tests cover determinism, tool ordering, budget thresholds, reminder cadence, and engine integration. No live API calls (`@pytest.mark.live` absent).
**Target Platform**: Linux server (CI) + developer macOS
**Project Type**: Library module (`src/kosmos/context/`) consumed by `QueryEngine`
**Performance Goals**: `build_assembled_context()` must complete in under 10 ms on a session with 50 resolved tasks and 20 registered tools (pure in-memory computation, enforced by `pytest-benchmark`)
**Constraints**: Stateless between turns; `ContextBuilder` must not accumulate per-turn state. System prompt content must be byte-identical across calls for cache stability (NFR-003).
**Scale/Scope**: Single session scope; the context package is entirely in-memory with no I/O.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Notes |
|---|---|---|
| I — Reference-Driven Development | PASS | All design decisions mapped to sources in `docs/vision.md § Reference materials`. See Reference Source Mapping section below. |
| II — Fail-Closed Security | PASS | `ContextBuilder` never fetches APIs internally; `api_health` is injected dependency (FR-013). `ContextBuilder` is read-only with respect to citizen data. |
| III — Pydantic v2 Strict Typing | PASS | All context objects (`ContextLayer`, `ContextBudget`, `AssembledContext`) are frozen Pydantic v2 models. No `Any` in I/O. |
| IV — Government API Compliance | PASS | No live `data.go.kr` calls in context package. No hardcoded keys. |
| V — Policy Alignment | PASS | System prompt includes language policy (Korean unless citizen writes in another language), tool-use policy (no fabricating government data), and personal-data handling reminder (FR-009). |
| Dev Standards | PASS | `stdlib logging` only, `uv + pyproject.toml`, English source text, `estimate_tokens()` reused from existing `engine.tokens`. |

**Complexity Justification**: No constitution violations. The `src/kosmos/context/` sub-package is the fourth Python package under `src/kosmos/`, joining `engine/`, `llm/`, and `tools/`. This is not an extra project; it is a lateral peer package that respects layer separation per `AGENTS.md § Directory layout`.

---

## Phase 0 — Research

### Primary references consulted

| Decision Area | Source | Finding Applied |
|---|---|---|
| Context assembly architecture | `ChinaSiro/claude-code-sourcemap` (`context.ts`, `queryContext.ts`, `constants/prompts.ts`) | `ContextBuilder` is a stateless per-turn function, not an accumulator. The assembled context is a value object, not an owned resource. |
| 3-tier context structure | `openedclaude/claude-reviews-claude` (§ Context Assembly) | Three layers: system (stable), session (accumulated), attachment (dynamic). Maps directly to `ContextLayer.layer_name` enum values. |
| Cache boundary management | arXiv 2601.06007 "Don't Break the Cache" | Static core-tool schemas must form a stable prefix. Dynamic content appended after. 41–80% cost reduction in 30–50+ tool-call sessions. Cache partition ordering is an invariant, not a convention. |
| Prompt cache strategy | Anthropic official docs (prompt caching guide) | Prefix stability requires that the same bytes appear in the same position across requests. This means: (a) system prompt content must be deterministic for given config, (b) core tools must be sorted by `id`, (c) no session-variable content in the prefix. |
| Context management patterns | Claude Agent SDK (`anthropics/claude-agent-sdk-python`) | `api_health` passed as injected dependency — context assembly is a pure computation, not a I/O layer. |
| Token budget accounting | Existing `kosmos.engine.tokens.estimate_tokens()` | Reuse for consistency with `PreprocessingPipeline`; avoids dual estimation paths with divergent heuristics. |
| Tool schema export | Existing `ToolRegistry.export_core_tools_openai()` + `GovAPITool.to_openai_tool()` | `AssembledContext.tool_definitions` reuses the `dict[str, object]` format already consumed by `query.py`. |
| Reminder cadence | `docs/vision.md § Layer 5 — Reminder cadence` | Every N turns inject reminder of unfinished tasks + auth expiry. V1: `turn_count % cadence == 0 and turn_count > 0`. |
| Module isolation | `AGENTS.md § Directory layout` | New sub-package `src/kosmos/context/` keeps context assembly isolated from `engine/` and `llm/`. |

### Technical unknowns resolved

1. **`QueryState` field `resolved_tasks`**: Confirmed as `list[str]` (human-readable task descriptions). `ContextBuilder.build_turn_attachment()` iterates this list directly. No structured parsing required.
2. **`situational_tools` registry method**: Confirmed in `ToolRegistry.situational_tools()`. V1 needs to surface only situational tools that are in the session's active set. The `active_situational_tools: set[str]` field will be added to `QueryState`.
3. **`ChatMessage` role constraint**: `role='user'` requires `content` to be non-None (validated by `_validate_role_constraints`). Per-turn attachments must therefore never produce an empty string — `build_turn_attachment()` returns `None` for empty sessions, not an empty content message.
4. **`SystemPromptConfig` location**: New frozen Pydantic model in `context/models.py`. Not in `engine/config.py` to preserve layer separation.

---

## Architecture

### Module structure: `src/kosmos/context/`

```
src/kosmos/context/
├── __init__.py           # Public exports: ContextBuilder, SystemPromptConfig,
│                         #   AssembledContext, ContextLayer, ContextBudget
├── models.py             # Frozen Pydantic v2 models
├── builder.py            # ContextBuilder — main orchestrator
├── system_prompt.py      # SystemPromptAssembler — stable system message
├── attachments.py        # AttachmentCollector — per-turn dynamic context
└── budget.py             # BudgetEstimator — token counting and limit checks
```

### Class responsibilities

**`ContextBuilder`** (stateless orchestrator):
- Constructor accepts `SystemPromptConfig` and optional `reminder_cadence: int = 5`
- `build_system_message() -> ChatMessage`: delegates to `SystemPromptAssembler`; result is cached on first call for cache stability (the config is frozen, so caching is safe)
- `build_turn_attachment(state: QueryState, api_health: dict[str, bool] | None = None) -> ChatMessage | None`: delegates to `AttachmentCollector`
- `build_assembled_context(state: QueryState, registry: ToolRegistry, api_health: ...) -> AssembledContext`: orchestrates all layers, computes budget

**`SystemPromptAssembler`**:
- Accepts `SystemPromptConfig`; produces deterministic text for a given config
- Four mandatory sections (FR-009): platform identity, language policy, tool-use policy, personal-data handling reminder
- Uses `str.join()` on pre-computed section strings for determinism; no f-string formatting with session data

**`AttachmentCollector`**:
- Accepts `QueryState`, `api_health`, `reminder_cadence`
- Produces structured text covering: resolved tasks, in-flight tool state, API health warnings, auth expiry warning, optional reminder block
- Returns `None` for empty session (turn 0, no resolved tasks, no api_health warnings)

**`BudgetEstimator`**:
- Stateless functions: `estimate_layer_tokens(layer: ContextLayer) -> int`, `estimate_tool_defs_tokens(defs: list[dict]) -> int`
- Produces `ContextBudget` from estimated totals and hard limit from `QueryEngineConfig.context_window`
- Soft limit: `int(hard_limit * 0.80)` (configurable, default 80%)

### Integration with `QueryEngine`

Two additive changes to `engine/engine.py`:

1. **Constructor**: Replace `system_prompt: str | None` parameter with `context_builder: ContextBuilder | None`. When `None`, default `ContextBuilder(SystemPromptConfig())` is constructed. Remove `_DEFAULT_SYSTEM_PROMPT` constant. Initialize `QueryState.messages` with `[context_builder.build_system_message()]`.

2. **`run()` method**: After the turn budget checks and before appending the user message, call `context_builder.build_turn_attachment(self._state, api_health=None)`. If non-`None`, prepend the attachment `ChatMessage` to `self._state.messages` before appending the user message.

One additive change to `engine/models.py`:

- Add `active_situational_tools: set[str] = field(default_factory=set)` to `QueryState`. This holds the IDs of situational tools explicitly activated during the session (e.g., via `search_tools`).

---

## Data Model (see also `data-model.md`)

### Frozen Pydantic v2 models (`context/models.py`)

```python
class SystemPromptConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    platform_identity: str = "KOSMOS"
    language_policy: str = (
        "Respond in Korean unless the citizen writes in another language."
    )
    tool_use_policy: str = (
        "Use tools when live government data is needed. "
        "Do not fabricate government data."
    )
    personal_data_reminder: str = (
        "Never expose personal identifiers beyond what the citizen provided."
    )
    reminder_cadence: int = 5


class ContextLayer(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Literal["system", "user"]
    content: str                       # non-empty; validated by field_validator
    layer_name: Literal[
        "system_prompt", "session_context", "turn_attachment"
    ]
    estimated_tokens: int              # >= 0


class ContextBudget(BaseModel):
    model_config = ConfigDict(frozen=True)

    hard_limit_tokens: int
    soft_limit_tokens: int             # default int(hard_limit * 0.80)
    estimated_tokens: int
    is_near_limit: bool                # estimated >= soft_limit
    is_over_limit: bool                # estimated >= hard_limit


class AssembledContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    system_layer: ContextLayer
    session_layer: ContextLayer | None
    attachment_layer: ContextLayer | None
    tool_definitions: list[dict[str, object]]  # core first, situational second
    budget: ContextBudget
    turn: int
```

### `QueryState` additive change

```python
active_situational_tools: set[str] = field(default_factory=set)
```

This field is the session-scoped set of situational tool IDs that have been explicitly activated (typically via `search_tools`). `ContextBuilder` uses this set to filter `ToolRegistry.situational_tools()` when building `AssembledContext.tool_definitions`.

---

## File Structure

### Documentation

```
specs/009-context-assembly-v1/
├── spec.md           # Approved specification (input)
├── plan.md           # This file
├── data-model.md     # Pydantic model diagrams and field reference
├── research.md       # Technical unknowns and resolution log
└── tasks.md          # Generated by /speckit-tasks (not yet created)
```

### Source code

```
src/kosmos/context/
├── __init__.py
├── models.py
├── builder.py
├── system_prompt.py
├── attachments.py
└── budget.py

src/kosmos/engine/
├── engine.py         # Modified: system_prompt → context_builder parameter
└── models.py         # Modified: active_situational_tools added to QueryState

tests/context/
├── __init__.py
├── test_models.py
├── test_builder.py
├── test_system_prompt.py
├── test_attachments.py
├── test_budget.py
└── test_engine_integration.py
```

---

## Implementation Phases

### Phase 1 — Models + ContextBuilder Skeleton

**Goal**: Lay down the complete data model layer and a bare `ContextBuilder` that assembles a valid `AssembledContext` with no attachment and no situational tools.

**Files**:
- `src/kosmos/context/models.py` — `SystemPromptConfig`, `ContextLayer`, `ContextBudget`, `AssembledContext`
- `src/kosmos/context/__init__.py` — export all public types
- `src/kosmos/context/builder.py` — `ContextBuilder` with all three public methods stubbed; `build_system_message()` returns a minimal static system message
- `tests/context/test_models.py` — validate frozen constraint, field validators, `ContextBudget` threshold logic

**Completion gate**: `uv run pytest tests/context/test_models.py` passes; `AssembledContext` can be constructed with only `system_layer` populated.

### Phase 2 — SystemPromptAssembler + Tool Schema Injection

**Goal**: Implement the four mandatory system prompt sections and the core/situational tool partitioning with deterministic ordering.

**Files**:
- `src/kosmos/context/system_prompt.py` — `SystemPromptAssembler`; produces deterministic text from `SystemPromptConfig`; logs `WARNING` when no core tools are registered
- `src/kosmos/context/builder.py` — wire `build_system_message()` to `SystemPromptAssembler`; wire `build_assembled_context()` tool_definitions to core-then-situational ordering
- `tests/context/test_system_prompt.py` — determinism test (1,000 consecutive calls, same config), section presence assertions
- `tests/context/test_builder.py` — tool ordering test: 3 core + 2 situational, verify `[core_a, core_b, core_c, sit_a, sit_b]` regardless of registration order; no-situational-tools edge case; all-situational-tools warning

**Completion gate**: SC-001, SC-002, and the cache-partitioning acceptance scenarios (US3) pass.

### Phase 3 — AttachmentCollector + Per-Turn Dynamic Context

**Goal**: Implement the full per-turn attachment: resolved tasks, in-flight tool state, API health, auth expiry, reminder cadence.

**Files**:
- `src/kosmos/context/attachments.py` — `AttachmentCollector`; each section is a private method that returns `str | None`; the collector joins non-None sections with `\n\n`; returns `None` when result is empty
- `src/kosmos/context/builder.py` — wire `build_turn_attachment()` to `AttachmentCollector`
- `tests/context/test_attachments.py` — US2 acceptance scenarios: empty session returns None; two resolved tasks listed; degraded API warning; auth expiry warning; reminder cadence at turn 10 with cadence=5; no reminder at turn 11

**Completion gate**: US1, US2, US5 acceptance scenarios pass.

### Phase 4 — Budget Management + Engine Integration + Performance

**Goal**: Complete the token budget guard, integrate `ContextBuilder` into `QueryEngine`, and enforce the 10 ms performance requirement.

**Files**:
- `src/kosmos/context/budget.py` — `BudgetEstimator`; sums `estimate_tokens()` over all layers and tool definitions; produces `ContextBudget`
- `src/kosmos/context/builder.py` — wire `build_assembled_context()` budget computation to `BudgetEstimator`
- `src/kosmos/engine/engine.py` — replace `system_prompt` parameter with `context_builder`; insert `build_turn_attachment()` call in `run()`; handle `is_over_limit` → yield `StopReason.api_budget_exceeded`
- `src/kosmos/engine/models.py` — add `active_situational_tools` to `QueryState`
- `tests/context/test_budget.py` — US4 acceptance scenarios: over-limit fires, near-limit logs WARNING, within-limit both False
- `tests/context/test_engine_integration.py` — SC-004: engine initialized without system_prompt produces history whose first message matches `build_system_message()` output; budget exceeded scenario
- `tests/context/test_builder.py` — performance: `pytest-benchmark` assertion that `build_assembled_context()` < 10 ms on 50 tasks + 20 tools

**Completion gate**: All seven success criteria (SC-001 through SC-007) pass; `uv run pytest tests/context/` is 100% green; `uv run pytest tests/engine/` remains 100% green (no regression).

---

## Reference Source Mapping

Every design decision traces to a concrete source in `docs/vision.md § Reference materials` per constitution § I.

| Decision | Source | Evidence |
|---|---|---|
| 3-tier V1 context (system, session, attachment) | `openedclaude/claude-reviews-claude` § Context Assembly; `docs/vision.md § Layer 5 — Memory tiers` | Three tiers map to the three `ContextLayer.layer_name` values |
| Core tools in prefix, situational tools in suffix | arXiv 2601.06007 ("Don't Break the Cache"), §3.2 cache-boundary experiments; `docs/vision.md § Layer 2 — Prompt cache partitioning` | 41–80% cost reduction by placing dynamic content after stable prefix |
| `ContextBuilder` stateless, called per turn | `ChinaSiro/claude-code-sourcemap` `context.ts` — context assembly is a pure functional per-turn pass | Stateless = no instance variables that accumulate per-turn state (NFR-002) |
| Frozen Pydantic v2 models for all context objects | Constitution § III; `pydantic/pydantic-ai` schema-driven pattern | `ConfigDict(frozen=True)` on all three new models (FR-011) |
| `estimate_tokens()` reuse | Existing `kosmos.engine.tokens.estimate_tokens()` — consistency with `PreprocessingPipeline` | Avoids dual estimation paths (FR-007) |
| Reminder cadence every N turns | `docs/vision.md § Layer 5 — Reminder cadence` | `turn_count % cadence == 0 and turn_count > 0` (FR-008) |
| `api_health` as injected dependency | Constitution § IV; Claude Agent SDK dependency injection pattern | Context assembly must not call live APIs (FR-013) |
| `src/kosmos/context/` new sub-package | `AGENTS.md § Directory layout` — layer separation | Isolated from `engine/` and `llm/` (NFR-005) |
| System prompt sections (FR-009) | `docs/vision.md § Layer 5` platform policies; Anthropic official docs on system prompt structure | Platform identity + language policy + tool-use policy + personal-data reminder |
| `active_situational_tools` on `QueryState` | `docs/vision.md § Layer 2 — Lazy tool discovery` — situational tools added mid-session via `search_tools` | FR-005: only explicitly activated situational tools appear in `tool_definitions` |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Cache partition violated by accidental insertion of dynamic content in prefix | Low | High | `build_assembled_context()` assembles `tool_definitions` in a single deterministic pass: `core_tools()` (sorted by id) then `active_situational_tools` (sorted by id). Covered by SC-002. |
| `ChatMessage(role='user', content=None)` raised when empty session | Medium | Medium | `build_turn_attachment()` returns `None`; `QueryEngine.run()` guards with `if attachment is not None`. Edge case covered by US2 scenario 3. |
| `build_assembled_context()` exceeds 10 ms on large sessions | Low | Medium | Pure in-memory string concatenation + `estimate_tokens()` heuristic; no I/O, no copies of large objects. Benchmark in Phase 4 catches regression early. |
| `active_situational_tools` on `QueryState` never populated in V1 (no `search_tools` integration yet) | High | Low | In V1, `active_situational_tools` will be empty for all sessions. This is correct: situational tools appear only after `search_tools` is implemented. Test coverage explicitly covers the empty-set case. |
| Budget guard fires before `PreprocessingPipeline` can compress | Low | Medium | Ordering is correct: budget guard runs inside `build_assembled_context()` called from `QueryEngine.run()` before preprocessing; if `is_over_limit` is True the engine yields `api_budget_exceeded` without calling the LLM. The preprocessing pipeline is still the primary defence; budget guard is last resort. |

---

## Project Structure (final)

### Documentation

```
specs/009-context-assembly-v1/
├── spec.md
├── plan.md           # This file
├── data-model.md
├── research.md
└── tasks.md          # /speckit-tasks output (not yet created)
```

### Source code layout

```
src/kosmos/context/
├── __init__.py
├── models.py
├── builder.py
├── system_prompt.py
├── attachments.py
└── budget.py

src/kosmos/engine/
├── engine.py         # Additive: context_builder parameter, turn attachment call
└── models.py         # Additive: active_situational_tools on QueryState

tests/context/
├── __init__.py
├── test_models.py
├── test_builder.py
├── test_system_prompt.py
├── test_attachments.py
├── test_budget.py
└── test_engine_integration.py
```
