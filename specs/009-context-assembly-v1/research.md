# Research: Context Assembly v1 (Layer 5)

**Feature**: Epic #9 — Context Assembly v1
**Date**: 2026-04-13
**Status**: Resolved — no open unknowns blocking implementation

---

## Purpose

This document records the technical unknowns that existed at plan creation and how each was resolved by reading the existing codebase and reference sources. It is an audit trail, not an action list.

---

## Unknown 1 — `QueryState.resolved_tasks` structure

**Question**: Is `resolved_tasks` a list of structured objects or plain strings? The spec says "human-readable descriptions of tasks resolved during the session."

**Resolution**: Confirmed in `src/kosmos/engine/models.py` line 55:
```python
resolved_tasks: list[str] = field(default_factory=list)
```
Plain strings. `AttachmentCollector` iterates this list and formats each entry as a bullet point. No structured parsing, no schema migration required.

---

## Unknown 2 — Situational tool activation mechanism in V1

**Question**: `ToolRegistry.situational_tools()` returns all non-core tools. `AssembledContext.tool_definitions` must include only situational tools that were explicitly activated this session (FR-005). How does the session record which situational tools are active?

**Resolution**: Added `active_situational_tools: set[str]` to `QueryState`. This is a new field with `field(default_factory=set)`, backward-compatible with all existing `QueryState` construction sites. In V1 the field is always empty (no `search_tools` integration yet). This is correct behavior: the empty-situational-tools case is an explicit edge case covered by US3 scenario 3.

The `ContextBuilder.build_assembled_context()` implementation will call:
```python
situational = sorted(
    [t for t in registry.situational_tools() if t.id in state.active_situational_tools],
    key=lambda t: t.id,
)
```

---

## Unknown 3 — `ChatMessage` validation when `build_turn_attachment()` returns empty content

**Question**: Can `ChatMessage(role="user", content="")` be constructed? If `AttachmentCollector` accidentally returns an empty string, does `ContextBuilder` produce an invalid message?

**Resolution**: Inspected `src/kosmos/llm/models.py`. The `@model_validator` enforces:
```python
if self.role in ("system", "user") and self.content is None:
    raise ValueError(...)
```
Empty string (`""`) is NOT caught by this validator — it only rejects `None`. However, the spec (FR-002) explicitly states the message must not be empty. The `ContextLayer` validator will enforce `content` is non-empty via `@field_validator`. If `AttachmentCollector` produces all-None sections, `build_turn_attachment()` returns `None` (not a `ContextLayer`), and `QueryEngine` skips it.

---

## Unknown 4 — `SystemPromptAssembler` caching strategy

**Question**: FR-001 requires `build_system_message()` to return identical content on repeated calls. Should the assembled content be cached in `ContextBuilder` or recomputed each time?

**Resolution**: Cache on first call. `SystemPromptConfig` is frozen (immutable), so the output of `SystemPromptAssembler.assemble()` is deterministic and can be safely cached. The `ContextBuilder` stores the result as `self._cached_system_message: ChatMessage | None = None` and returns it on subsequent calls. This guarantees both determinism and performance.

Alternative considered: recompute on each call. Rejected because: (a) it defeats the purpose of the determinism requirement; (b) even though the output would be identical, recomputation introduces an unnecessary code path that could diverge under a future bug.

---

## Unknown 5 — Integration ordering: budget guard vs. preprocessing pipeline

**Question**: The spec says the budget guard fires when `build_assembled_context()` produces an over-limit context, and the preprocessing pipeline runs later inside `query.py`. Does this create a situation where the pipeline never gets a chance to compress?

**Resolution**: The budget guard and the preprocessing pipeline operate at different scopes.

The preprocessing pipeline in `query.py` runs on `ctx.state.messages` (the raw conversation history), triggered by the token threshold check. This happens inside the `while iteration < max_iterations` loop, before the LLM call snapshot is taken.

The context budget guard in `build_assembled_context()` estimates the full assembled context (system + session + attachment + tool defs + history). The budget guard fires when the assembled total exceeds the hard limit even before preprocessing.

The correct interpretation: in V1, `build_assembled_context()` is called in `QueryEngine.run()` before the `query()` generator is entered. If `is_over_limit` is True, the engine yields `api_budget_exceeded` and returns without ever entering `query()`. The preprocessing pipeline therefore never sees the oversized context.

This is intentional (spec FR-006, US4 scenario 1): the budget guard is the last-resort protection. Compression is the pipeline's job. If compression has already run (in a previous iteration within the same turn), and the context is still over limit, the engine must stop.

However: for V1, `build_assembled_context()` is called once per turn in `QueryEngine.run()`, before any iteration of `query.py`. The preprocessing pipeline runs inside `query.py` at the start of each iteration. This means there is a one-turn lag: the budget guard fires on a context that has not yet been preprocessed.

Mitigation strategy confirmed: this is accepted behavior per the spec. Long sessions will be protected by the preprocessing pipeline in the common case; the budget guard only fires for pathological sessions where even post-compression context exceeds the hard limit.

---

## Unknown 6 — `export_core_tools_openai()` vs. direct `to_openai_tool()` call

**Question**: Should `ContextBuilder` call `registry.export_core_tools_openai()` directly, or reconstruct tool definitions from `registry.core_tools()`?

**Resolution**: Call `registry.export_core_tools_openai()` for core tools. This method already enforces sorted-by-id ordering and returns the same format consumed by `query.py`. For situational tools, `ContextBuilder` calls `[t.to_openai_tool() for t in sorted(active_situational, key=lambda t: t.id)]` to build the suffix. The two lists are then concatenated:

```python
tool_definitions = registry.export_core_tools_openai() + [
    t.to_openai_tool()
    for t in sorted(situational_active, key=lambda t: t.id)
]
```

This reuses the existing sorted export for the stable prefix and applies the same sort discipline to the dynamic suffix.

---

## Unknown 7 — `reminder_cadence` field location: `SystemPromptConfig` or `ContextBuilder` constructor?

**Question**: Should `reminder_cadence` be on `SystemPromptConfig` (grouped with other policy config) or on `ContextBuilder.__init__()` (operational behavior, not policy content)?

**Resolution**: Place `reminder_cadence` on `SystemPromptConfig`. Rationale:

1. `SystemPromptConfig` is the single configuration object for `ContextBuilder`. Adding a separate constructor parameter creates a split configuration that callers must coordinate.
2. The reminder cadence is a platform policy decision, not an implementation detail. It belongs alongside the other policy fields.
3. The spec's `FR-008` says "when `state.turn_count % config.reminder_cadence == 0`", implying `config` refers to a single config object, not a mix of constructor args and config fields.

`ContextBuilder.__init__()` signature:
```python
def __init__(self, config: SystemPromptConfig | None = None) -> None:
```
When `config` is `None`, `SystemPromptConfig()` defaults are used, including the default `reminder_cadence=5`.

---

## No open unknowns

All technical questions have been resolved. Implementation can proceed with Phase 1.
