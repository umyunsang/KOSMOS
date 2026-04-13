# Data Model: Context Assembly v1 (Layer 5)

**Feature**: Epic #9 — Context Assembly v1
**Location**: `src/kosmos/context/models.py`
**Date**: 2026-04-13

---

## Overview

Five Pydantic v2 models form the complete data contract for the context assembly layer. All are frozen (`ConfigDict(frozen=True)`). One existing model (`QueryState`) receives an additive field.

```
SystemPromptConfig          ContextLayer          ContextBudget
       │                         │                      │
       ▼                         ▼                      ▼
 SystemPromptAssembler    AssembledContext  ──────────────
                           ├── system_layer: ContextLayer
                           ├── session_layer: ContextLayer | None
                           ├── attachment_layer: ContextLayer | None
                           ├── tool_definitions: list[dict]
                           ├── budget: ContextBudget
                           └── turn: int
```

---

## `SystemPromptConfig`

**Module**: `src/kosmos/context/models.py`
**Parent**: `pydantic.BaseModel`
**Config**: `frozen=True`

Carries the four mandatory policy sections that `SystemPromptAssembler` renders into a stable system message. All fields have platform-safe defaults, making construction optional for callers.

| Field | Type | Default | Constraint | Notes |
|---|---|---|---|---|
| `platform_identity` | `str` | `"KOSMOS"` | non-empty | Injected into the platform identity section |
| `language_policy` | `str` | `"Respond in Korean unless the citizen writes in another language."` | non-empty | FR-009 (b) |
| `tool_use_policy` | `str` | `"Use tools when live government data is needed. Do not fabricate government data."` | non-empty | FR-009 (c) |
| `personal_data_reminder` | `str` | `"Never expose personal identifiers beyond what the citizen provided."` | non-empty | FR-009 (d) |
| `reminder_cadence` | `int` | `5` | `>= 1` | Turns between reminder injections; FR-008 |

**Validation**:
- All `str` fields validated to be non-empty via `@field_validator`.
- `reminder_cadence` validated `>= 1`; cadence of 1 fires every turn (valid per spec edge case).

**Korean domain data note**: Fields such as `platform_identity`, `language_policy`, etc. may contain Korean text (domain data). This is the sole allowed exception to the English-only source text rule.

---

## `ContextLayer`

**Module**: `src/kosmos/context/models.py`
**Parent**: `pydantic.BaseModel`
**Config**: `frozen=True`

Represents one assembled context tier. The `content` field is the rendered text that will appear in the `ChatMessage` handed to the LLM.

| Field | Type | Constraint | Notes |
|---|---|---|---|
| `role` | `Literal["system", "user"]` | required | `"system"` for `system_prompt` layer; `"user"` for `session_context` and `turn_attachment` |
| `content` | `str` | non-empty | Validated by `@field_validator`; empty content would produce an invalid `ChatMessage` |
| `layer_name` | `Literal["system_prompt", "session_context", "turn_attachment"]` | required | Identifies which tier produced this layer |
| `estimated_tokens` | `int` | `>= 0` | Computed by `BudgetEstimator` using `estimate_tokens(content)` |

**Invariant**: `role == "system"` iff `layer_name == "system_prompt"`. Enforced by `@model_validator`.

---

## `ContextBudget`

**Module**: `src/kosmos/context/models.py`
**Parent**: `pydantic.BaseModel`
**Config**: `frozen=True`

Captures the token budget status of an assembled context. Computed by `BudgetEstimator` after all layers and tool definitions are assembled.

| Field | Type | Constraint | Notes |
|---|---|---|---|
| `hard_limit_tokens` | `int` | `> 0` | From `QueryEngineConfig.context_window` (default: 128,000) |
| `soft_limit_tokens` | `int` | `> 0`, `<= hard_limit_tokens` | Default: `int(hard_limit * 0.80)` |
| `estimated_tokens` | `int` | `>= 0` | Sum of all `ContextLayer.estimated_tokens` + tool definition token estimate |
| `is_near_limit` | `bool` | derived | `estimated_tokens >= soft_limit_tokens` |
| `is_over_limit` | `bool` | derived | `estimated_tokens >= hard_limit_tokens` |

**Construction note**: `is_near_limit` and `is_over_limit` are computed fields derived from the other fields. They MUST NOT be set independently — use the class method `ContextBudget.from_estimate(hard_limit, estimated)` which computes derived fields automatically.

**Threshold relationship**: `is_over_limit = True` implies `is_near_limit = True` (because `hard_limit >= soft_limit`). Any code that checks `is_over_limit` does not need to also check `is_near_limit` unless it needs to distinguish the two states.

---

## `AssembledContext`

**Module**: `src/kosmos/context/models.py`
**Parent**: `pydantic.BaseModel`
**Config**: `frozen=True`

The final product of `ContextBuilder.build_assembled_context()`. Carries all three optional layers, the ordered tool definition list, and the budget snapshot for the current turn. Consumed by `QueryEngine.run()` which passes its layers and tool definitions to the LLM client.

| Field | Type | Presence | Notes |
|---|---|---|---|
| `system_layer` | `ContextLayer` | always | `layer_name="system_prompt"`, `role="system"` |
| `session_layer` | `ContextLayer \| None` | when `resolved_tasks` non-empty or `turn_count > 0` | `layer_name="session_context"`, `role="user"` |
| `attachment_layer` | `ContextLayer \| None` | when dynamic state is non-empty (see FR-002) | `layer_name="turn_attachment"`, `role="user"` |
| `tool_definitions` | `list[dict[str, object]]` | always (may be empty list) | Core tools first (sorted by `id`), then active situational tools (sorted by `id`) |
| `budget` | `ContextBudget` | always | Token budget status for this turn |
| `turn` | `int` | always | Snapshot of `QueryState.turn_count` at assembly time |

**Tool definition ordering invariant** (FR-004): Within `tool_definitions`, `tool.id` ordering is lexicographic ascending within each partition. This makes the list byte-identical across turns where no new core tools are registered, satisfying the prompt cache prefix stability requirement.

### Conversion to `ChatMessage` list

`QueryEngine` converts `AssembledContext` to the message list that the LLM client receives:

```
assembled.system_layer   → ChatMessage(role="system", content=system_layer.content)
assembled.session_layer  → ChatMessage(role="user", content=session_layer.content)   [if present]
assembled.attachment_layer → ChatMessage(role="user", content=attachment_layer.content) [if present]
[original conversation history messages follow]
```

The `tool_definitions` list is passed as the `tools=` parameter to `LLMClient.stream()` / `LLMClient.complete()`, not inserted into the message list.

---

## `QueryState` (additive change)

**Module**: `src/kosmos/engine/models.py`
**Type**: `dataclass` (mutable, existing)

One new field is added to the existing `QueryState` dataclass:

| Field | Type | Default | Notes |
|---|---|---|---|
| `active_situational_tools` | `set[str]` | `field(default_factory=set)` | IDs of situational tools explicitly activated during this session. Populated by `search_tools` in Wave 2+. Empty in V1. |

**Backward compatibility**: The `field(default_factory=set)` default ensures all existing `QueryState` construction sites that do not pass this argument continue to work without change. `QueryEngine.__init__()` does not pass this field, so it defaults to an empty set automatically.

---

## `SystemPromptConfig` — `ContextLayer` lifecycle

```
SystemPromptConfig
        │
        ▼
SystemPromptAssembler.assemble() → str (deterministic text)
        │
        ▼
ContextLayer(
    role="system",
    content=<assembled text>,
    layer_name="system_prompt",
    estimated_tokens=estimate_tokens(<assembled text>)
)
        │
        ▼
AssembledContext.system_layer
```

The `SystemPromptAssembler` caches its output in `ContextBuilder` after the first call (the config is frozen, so the output is immutable). Subsequent calls to `build_system_message()` return the cached `ChatMessage` directly, ensuring byte-identical content across every turn.

---

## Token estimation methodology

All token estimates in `ContextLayer.estimated_tokens` and the tool-definition estimate use `kosmos.engine.tokens.estimate_tokens()`:

```
Korean Hangul syllables (U+AC00–U+D7A3): ceil(count / 2) tokens
Other characters (ASCII, punctuation, numbers): ceil(count / 4) tokens
```

For tool definitions, `BudgetEstimator` serializes each definition to JSON (`json.dumps(defn)`) and estimates tokens on the resulting string. This is a conservative estimate; actual token cost may be lower when the prompt cache returns a cache hit and token costs are amortized.

---

## Edge case matrix

| State | `session_layer` | `attachment_layer` | `is_near_limit` | `is_over_limit` |
|---|---|---|---|---|
| Turn 0, no tasks, no health issues | `None` | `None` | computed | computed |
| Turn 1, one resolved task | Present | Present (task listed) | computed | computed |
| Turn 5, reminder cadence=5 | Present | Present + reminder | computed | computed |
| Turn 6, reminder cadence=5 | Present | Present (no reminder) | computed | computed |
| 100 resolved tasks, 20 tools | Present (large) | Present | likely True | possible |
| No core tools registered | Present | Present | computed | computed |
| All tools situational | — | — | — | WARNING logged |
| `api_health=None` | unaffected | health section omitted | computed | computed |
