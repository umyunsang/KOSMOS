# Feature Specification: Context Assembly v1 (Layer 5)

**Feature Branch**: `feat/009-context-assembly-v1`
**Created**: 2026-04-13
**Status**: Completed (Phase 1)
**Input**: Epic #9 — Context Assembly v1 (Layer 5)

---

## Overview & Context

Layer 5, Context Assembly, owns the layered prompt the LLM sees on every turn.
It sits between the Query Engine loop (Layer 1) and the LLM Client (Wave 1),
assembling a complete, budget-aware context object that the engine hands to the
client unchanged.

V1 covers three of the five memory tiers described in `docs/vision.md § Layer 5`:

| Tier | V1 scope | Later |
|------|----------|-------|
| System | Hardcoded platform policies | Phase 2: externalized YAML/CLML memory file |
| Region | — | Phase 2 |
| Citizen | — | Phase 2 |
| Session | Conversation state summary | Phase 2: compressed auto-summarization |
| Auto | — | Phase 2 |

In addition to tiers, V1 introduces per-turn dynamic attachments (auth level,
in-flight tool state, API health), tool schema injection with
core/situational partitioning, and a context budget guard.

### Cache correctness rationale

arXiv 2601.06007 ("Don't Break the Cache") empirically demonstrates that
placing dynamic content (tool results, per-turn attachments) *after* the stable
prefix saves 41–80% of prompt encoding cost in sessions with 30–50+ tool calls.
This finding directly maps to the KOSMOS tool registry partition already in
place (`is_core` / situational split in `ToolRegistry`). `ContextBuilder` must
enforce that partition ordering as an invariant, not a convention.

### Integration surface

The existing `QueryEngine.run()` constructs a hardcoded system prompt at
`_DEFAULT_SYSTEM_PROMPT` in `engine.py` and passes it as the first `ChatMessage`
when initializing `QueryState`. V1 replaces that hardcoded string with a call to
`ContextBuilder.build_system_message()`, and introduces a new per-turn call to
`ContextBuilder.build_turn_attachment()` that prepends a dynamic context block
to the snapshot before it reaches the LLM.

`PreprocessingPipeline` is unaffected. `ContextBuilder` runs *before* the
preprocessing threshold check, injecting the attachment; the pipeline then runs
on the full message list if the window limit is approached.

---

## User Stories

### User Story 1 — Stable System Prompt Assembly (Priority: P1)

A platform operator needs the LLM to receive consistent, policy-aligned
instructions on every turn so that citizen interactions stay within platform
guidelines regardless of which citizen or session is active.

**Why P1**: Without a correctly assembled system prompt, every LLM turn is
ungoverned. All downstream behaviour — tool selection, language, refusal
posture — depends on this layer.

**Independent Test**: Unit test constructs `ContextBuilder` with a
`SystemPromptConfig`, calls `build_system_message()`, and asserts that the
returned `ChatMessage` has `role='system'`, contains all required policy
sections, and does not change between calls on the same instance.

**Acceptance Scenarios**:

1. **Given** a `ContextBuilder` is initialized, **When** `build_system_message()` is called twice, **Then** both calls return an identical string (deterministic; cache-stable).
2. **Given** a platform policy that restricts tools to citizen services, **When** the system message is assembled, **Then** it contains the platform identity section, the language policy section, and the tool-use policy section.
3. **Given** the `QueryEngine` is initialized without an explicit `system_prompt`, **When** the first `ChatMessage` in history is inspected, **Then** it was produced by `ContextBuilder.build_system_message()`, not by the hardcoded `_DEFAULT_SYSTEM_PROMPT` constant.

---

### User Story 2 — Per-Turn Attachment Injection (Priority: P1)

A citizen making a multi-step civil-affairs request needs the LLM to be aware
of what has been resolved so far, which tools were called last turn, and whether
any APIs are currently under maintenance — without the citizen having to repeat
themselves.

**Why P1**: Without per-turn context, the model repeatedly rediscovers state
already established, wasting tool calls and degrading response quality in longer
sessions.

**Independent Test**: Unit test constructs a `QueryState` with two resolved
tasks and one in-flight tool ID, calls `build_turn_attachment()`, and asserts
the returned `ChatMessage` text contains the resolved task descriptions and the
pending tool name.

**Acceptance Scenarios**:

1. **Given** a session with two resolved tasks, **When** `build_turn_attachment()` is called, **Then** the attachment lists both resolved tasks in the injected context block.
2. **Given** an API health monitor reporting one service as degraded, **When** `build_turn_attachment()` is called, **Then** the attachment includes a warning that the affected tool is currently unavailable.
3. **Given** an empty session (turn 0), **When** `build_turn_attachment()` is called, **Then** it returns `None` (no attachment needed; avoids empty-content messages that break `ChatMessage` validation).
4. **Given** a session where the citizen's auth token expires in fewer than 60 seconds, **When** `build_turn_attachment()` is called, **Then** the attachment includes an auth-expiry warning. *(V1 note: `QueryState` does not yet carry `auth_expiry_at`; this scenario is verified using a test fixture that manually injects the field. Full integration deferred to Phase 2 when citizen authentication lands.)*

---

### User Story 3 — Tool Schema Injection with Cache Partitioning (Priority: P1)

The LLM needs tool schemas in every prompt. For cost efficiency, core tool
schemas (stable across sessions) must appear in the prefix partition so they
stay cache-hit, and situational tool schemas (dynamic, added mid-session via
`search_tools`) must appear in the suffix partition.

**Why P1**: Violating this ordering invalidates the cache prefix on every turn,
multiplying encoding costs. This is the primary cost driver identified by arXiv
2601.06007.

**Independent Test**: Unit test registers 3 core tools and 2 situational tools,
calls `build_assembled_context()`, and asserts that the returned
`AssembledContext.tool_definitions` list places all core tools before all
situational tools, sorted by `id` within each partition.

**Acceptance Scenarios**:

1. **Given** a registry with core tools A, B, and situational tool C, **When** `AssembledContext` is built, **Then** the `tool_definitions` list is ordered [A, B, C] regardless of registration order.
2. **Given** a situational tool D is added mid-session (discovered via `search_tools`), **When** the next turn's `AssembledContext` is built, **Then** D appears after all core tools but is not present in the stable prefix. *(V1 note: `search_tools` is not yet wired; this scenario is verified using a test fixture that manually populates `QueryState.active_situational_tools` to simulate mid-session tool discovery.)*
3. **Given** no situational tools are active, **When** `AssembledContext` is built, **Then** only core tools appear in `tool_definitions` and the suffix partition is empty.

---

### User Story 4 — Context Budget Guard (Priority: P2)

For a long session approaching the 128K token window, the engine must not hand
the LLM a prompt that exceeds the model's context window, even before the
`PreprocessingPipeline` has had a chance to compress history.

**Why P2**: The preprocessing pipeline runs after context assembly. If the
assembled context already exceeds the window, the pipeline receives input it
cannot save. The budget guard is the last line of defence before the LLM call.

**Independent Test**: Unit test constructs an `AssembledContext` whose estimated
token count exceeds `context_budget.hard_limit_tokens`, then calls
`context_budget.is_over_limit()` and asserts it returns `True`. Separately,
asserts that `QueryEngine` raises (or yields a stop event) when the guard fires.

**Acceptance Scenarios**:

1. **Given** a session with a history that brings total estimated tokens above the hard limit, **When** `ContextBuilder.build_assembled_context()` is called, **Then** `AssembledContext.budget.is_over_limit` is `True` and the engine yields `StopReason.api_budget_exceeded`.
2. **Given** a soft warning threshold (default: 80% of hard limit), **When** the assembled context crosses the threshold but not the hard limit, **Then** `AssembledContext.budget.is_near_limit` is `True` and a warning is logged at `WARNING` level.
3. **Given** a context well within the soft threshold, **When** `build_assembled_context()` is called, **Then** both `is_over_limit` and `is_near_limit` are `False`.

---

### User Story 5 — Reminder Cadence (Priority: P3)

✅ Implemented in Phase 1 — `src/kosmos/context/attachments.py` (`AttachmentCollector._reminder_section`, lines 135–154), `src/kosmos/context/models.py` (`SystemPromptConfig.reminder_cadence`, lines 31–56). Tests: `tests/context/test_attachments.py` (`TestAttachmentReminderCadenceStress`, `test_reminder_fires_at_cadence`, `test_reminder_skips_turn_0`, `test_reminder_skips_non_cadence`), `tests/context/test_models.py` (`test_reminder_cadence_zero_raises`, `test_reminder_cadence_negative_raises`).

In a long session, the LLM tends to forget earlier unfinished tasks and
authentication context. Every N turns the system injects a structured reminder
that re-orients the model without requiring the citizen to repeat themselves.

**Why P3**: The first two user stories cover correctness; this covers quality
degradation in very long sessions. It is not a hard correctness requirement for
V1 but significantly improves multi-turn citizen experience.

**Independent Test**: Unit test constructs a `QueryState` with `turn_count=10`,
configures `reminder_cadence=5`, and asserts that `build_turn_attachment()`
includes the reminder section. Repeats with `turn_count=11` and asserts the
reminder section is absent.

**Acceptance Scenarios**:

1. **Given** a session at turn 10 and `reminder_cadence=5`, **When** `build_turn_attachment()` is called, **Then** the attachment includes a reminder block listing unfinished tasks and the time remaining before auth expiry.
2. **Given** a session at turn 11 and `reminder_cadence=5`, **When** `build_turn_attachment()` is called, **Then** no reminder block is present (turn 11 is not a cadence boundary).

---

## Functional Requirements

- **FR-001**: `ContextBuilder` MUST expose `build_system_message()` returning a frozen `ChatMessage(role='system')` whose content is deterministic for a given `SystemPromptConfig`.
- **FR-002**: `ContextBuilder` MUST expose `build_turn_attachment(state, api_health)` returning a `ContextLayer(role='user', layer_name='turn_attachment')` or `None`. The caller (`QueryEngine`) converts the returned `ContextLayer` to a `ChatMessage(role='user')` before inserting it into the message history. The content MUST NOT be empty (enforced by `ContextLayer` validation).
- **FR-003**: `ContextBuilder` MUST expose `build_assembled_context(state, registry, api_health)` returning an `AssembledContext` that combines the system message, optional turn attachment, and tool definitions.
- **FR-004**: `AssembledContext.tool_definitions` MUST list core tools before situational tools; within each partition tools MUST be sorted by `id` (deterministic for cache stability).
- **FR-005**: `AssembledContext.tool_definitions` MUST NOT include situational tools that were not explicitly added to the session's active situational tool set.
- **FR-006**: `ContextBuilder` MUST compute the estimated token count of the assembled context and populate `AssembledContext.budget` with `ContextBudget.estimated_tokens`, `is_near_limit`, and `is_over_limit`.
- **FR-007**: Token estimation MUST use `engine.tokens.estimate_tokens()` for consistency with `PreprocessingPipeline`; actual token counts from the LLM response are not available at assembly time.
- **FR-008**: `ContextBuilder` MUST inject a reminder block when `state.turn_count % config.reminder_cadence == 0` and `state.turn_count > 0`; the reminder MUST list `state.resolved_tasks` and any pending in-flight state.
- **FR-009**: The system prompt layer MUST include at minimum: (a) platform identity, (b) language policy (Korean response unless citizen writes in another language), (c) tool-use policy (use tools when live data is needed; do not fabricate government data), (d) personal-data handling reminder.
- **FR-010**: `ContextBuilder` MUST be callable before `QueryEngine._state` is populated with user messages; it MUST NOT read from `state.messages` directly — per-turn attachment data comes from the structured fields on `QueryState`.
- **FR-011**: All three new Pydantic models (`ContextLayer`, `ContextBudget`, `AssembledContext`) MUST be frozen (`ConfigDict(frozen=True)`).
- **FR-012**: `ContextBuilder` integration into `QueryEngine` MUST be additive: the `system_prompt` constructor parameter is replaced by `ContextBuilder`, and the engine's `run()` calls `build_turn_attachment()` before creating the immutable snapshot. Existing call sites not using `system_prompt` must not require changes.
- **FR-013**: `ContextBuilder` MUST NOT call live `data.go.kr` APIs. API health status is passed in as a parameter (injected dependency).

---

## Pydantic v2 Models

### `ContextLayer`

```
ContextLayer (frozen):
    role: Literal["system", "user"]
    content: str               # non-empty; validated
    layer_name: str            # "system_prompt" | "session_context" | "turn_attachment"
    estimated_tokens: int      # >= 0
```

### `ContextBudget`

```
ContextBudget (frozen):
    hard_limit_tokens: int         # from QueryEngineConfig.context_window
    soft_limit_tokens: int         # default: int(hard_limit * 0.80)
    estimated_tokens: int          # sum of all ContextLayer.estimated_tokens
    is_near_limit: bool            # estimated >= soft_limit
    is_over_limit: bool            # estimated >= hard_limit
```

### `AssembledContext`

```
AssembledContext (frozen):
    system_layer: ContextLayer             # always present
    session_layer: ContextLayer | None     # present when resolved_tasks or turn > 0
    attachment_layer: ContextLayer | None  # present when dynamic state is non-empty
    tool_definitions: list[dict[str, object]]  # core first, then situational
    budget: ContextBudget
    turn: int                              # snapshot of state.turn_count
```

The `tool_definitions` field reuses the existing `GovAPITool.to_openai_tool()` dict
format already consumed by `QueryEngine.query()` via
`ToolRegistry.export_core_tools_openai()`.

---

## Non-Functional Requirements

- **NFR-001**: `build_assembled_context()` MUST complete in under 10 ms on a session with up to 50 resolved tasks and 20 registered tools (pure in-memory computation).
- **NFR-002**: `ContextBuilder` MUST be stateless between turns; all session state is passed in at call time. No instance variables that accumulate per-turn state.
- **NFR-003**: The system message content MUST be identical across calls with the same `SystemPromptConfig` so the FriendliAI/EXAONE prompt cache is not invalidated between turns.
- **NFR-004**: All logging MUST use `logging.getLogger(__name__)` at appropriate levels; no `print()` statements.
- **NFR-005**: The module MUST be located at `src/kosmos/context/` (new sub-package), keeping it isolated from `engine/` and `llm/` to respect layer separation.

---

## Success Criteria

- **SC-001**: `build_system_message()` returns identical content on 1,000 consecutive calls with the same config (determinism / cache-stability test).
- **SC-002**: `AssembledContext.tool_definitions` correctly places core tools before situational tools in 100% of unit test scenarios covering mixed registration order.
- **SC-003**: `ContextBudget.is_over_limit` correctly fires when estimated tokens exceed `context_window` in all threshold boundary tests.
- **SC-004**: `QueryEngine` integration test: constructing the engine without `system_prompt` and running one turn produces a `ChatMessage` history whose first message content matches `ContextBuilder.build_system_message()` output.
- **SC-005**: A session of 50 turns with one reminder injection per 5 turns produces the expected number of reminder blocks (10) in attachment history.
- **SC-006**: `build_assembled_context()` executes in under 10 ms on a benchmark with 50 resolved tasks and 20 tools (enforced by a `pytest-benchmark` assertion).
- **SC-007**: All unit tests pass with no live API calls (CI safe; `@pytest.mark.live` marker absent from all context assembly tests).

---

## Edge Cases

- **Empty session (turn 0, no resolved tasks)**: `build_turn_attachment()` returns `None`. `QueryEngine` must handle `None` gracefully without adding an empty `ChatMessage` to the snapshot.
- **All tools are core (no situational tools registered)**: `AssembledContext.tool_definitions` contains only core tools; situational suffix is empty. No error.
- **All tools are situational (no core tools registered)**: Core prefix is empty; situational tools appear in `tool_definitions` sorted by `id`. Warning logged at `WARNING` level because this breaks cache-prefix assumptions.
- **`api_health` parameter is `None`**: `build_turn_attachment()` omits the API health section silently. Health monitoring is optional in V1.
- **`state.resolved_tasks` is a very long list (100+ items)**: `session_layer` content is assembled but token estimation may push `budget.is_near_limit` to `True`. The engine logs a warning but proceeds; compression is `PreprocessingPipeline`'s responsibility.
- **Reminder cadence configured to 1**: Reminder fires on every turn. This is valid; the test must verify it does not cause `ChatMessage` role conflicts or duplicate system instructions.
- **`SystemPromptConfig` fields contain Korean text (domain data)**: Allowed per project language rule (Korean domain data is the sole exception to the English-only source text rule).

---

## Out of Scope (V1)

The following are explicitly deferred to Phase 2 or later:

- **Region tier**: Region-specific rule files (Busan ordinances, etc.) requiring conditional activation logic.
- **Citizen tier**: Per-citizen profile injection (age, residence, family composition) and age-gated tool filtering (`age >= 65` conditional).
- **Auto tier**: Prior civil-affairs history (auto-memorized patterns across sessions).
- **Memory file format**: YAML / CLML memory files with conditional activation blocks.
- **Compressed session summaries**: Automatic summarization of older turns to reduce session layer token cost.
- **Prompt caching headers**: Explicit cache-control markers to the FriendliAI API (evaluated after observing actual cache-hit rates in Phase 2).
- **Coordinator context injection**: Attachment of Agent Swarm (Layer 4) coordination state — deferred until Layer 4 is implemented.

---

## Dependencies

| Dependency | Status | Notes |
|---|---|---|
| Epic #4 — LLM Client | Complete | `LLMClient`, `ChatMessage`, `TokenUsage` |
| Epic #5 — Query Engine Core | Complete | `QueryEngine`, `QueryState`, `QueryEngineConfig`, `PreprocessingPipeline`, `estimate_tokens` |
| Epic #6 — Tool System | Complete | `ToolRegistry`, `GovAPITool`, `is_core` field, `export_core_tools_openai()` |
| Epic #8 — Permission Pipeline v1 | In progress | Auth level field on `QueryState` used in per-turn attachment; V1 reads a stub if not yet available |

### Integration contract with QueryEngine

`QueryEngine.__init__` currently accepts an optional `system_prompt: str | None`
parameter and falls back to `_DEFAULT_SYSTEM_PROMPT`. V1 replaces this with an
optional `context_builder: ContextBuilder | None` parameter; when `None` a
default `ContextBuilder` with standard `SystemPromptConfig` is used. The
hardcoded `_DEFAULT_SYSTEM_PROMPT` constant is removed.

`QueryEngine.run()` currently appends the user message and immediately creates
the immutable snapshot. V1 inserts a call to
`context_builder.build_turn_attachment(state, api_health=None)` before the
snapshot is taken, prepending the attachment as a `user`-role context message
if the result is non-`None`.

No other call sites in the existing codebase are affected.

---

## Reference Mapping

Per constitution § I, every design decision must trace to a source in
`docs/vision.md § Reference materials`.

| Decision | Source |
|---|---|
| 3-tier V1 context (system, session, attachment) | `docs/vision.md § Layer 5 — Memory tiers` |
| Core tools in prefix, situational tools in suffix | arXiv 2601.06007 ("Don't Break the Cache") + `docs/vision.md § Layer 2 — Prompt cache partitioning` |
| `ContextBuilder` stateless, called per turn | Claude Code reconstructed (`ChinaSiro/claude-code-sourcemap`) — context assembly is pure per-turn function |
| Frozen Pydantic v2 models for all context objects | Constitution § III; Pydantic AI schema-driven pattern |
| `estimate_tokens()` reuse for budget accounting | Existing `kosmos.engine.tokens` module — consistency with `PreprocessingPipeline` |
| Reminder cadence every N turns | `docs/vision.md § Layer 5 — Reminder cadence` |
| `api_health` as injected dependency (not fetched internally) | Constitution § IV — never call live APIs from within a non-adapter module |
| `src/kosmos/context/` new sub-package | `AGENTS.md § Directory layout` — layer separation |
