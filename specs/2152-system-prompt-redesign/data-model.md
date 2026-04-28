# Phase 1 — Data Model

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

All types are Pydantic v2 frozen models (constitution Principle III; `Any` forbidden in I/O schemas). Types live in `src/kosmos/llm/prompt_assembler.py` unless noted.

---

## 1. `PromptSection`

The atomic unit of the static prefix. The four shipped instances correspond to the four XML-tagged sections in `prompts/system_v1.md`.

| Field | Type | Notes |
|---|---|---|
| `tag` | `Literal["role", "core_rules", "tool_usage", "output_style"]` | One of the four R1 tag names. Closed Literal — extension requires a deliberate Pydantic field-type change reviewed in a future Epic. |
| `body` | `str` | The Korean-language prose between the opening and closing XML tag. Validated non-empty (`min_length=1`). |

**Validation**: `tag` and `body` are both required. Frozen model — instances are immutable once constructed. No state transitions.

**Source-of-truth**: `prompts/system_v1.md` is the canonical text; the model is constructed from it at PromptLoader boot. The model exists for type-safety and test assertions, not as a parallel store.

---

## 2. `PromptAssemblyContext`

Read-only context passed to every dynamic-suffix decorator. Mirrors Pydantic AI's `RunContext[T]` pattern.

| Field | Type | Notes |
|---|---|---|
| `session_id` | `str` | Stable across all turns of a TUI session. UUID4. |
| `session_started_at` | `datetime` | ISO-8601 UTC. |
| `tool_inventory` | `tuple[str, ...]` | Sorted tuple of tool IDs registered at chat-request time. Used to determine cache-prefix invariance. |
| `dynamic_inputs` | `dict[str, str]` | Free-form key-value bag for memdir consent / ministry-scope / future injectors. Values are pre-stringified — decorators do not coerce. Pydantic v2 Strict mode rejects non-string values. |

**Validation**: `tool_inventory` MUST be a tuple (not a list) so it cannot be mutated after construction. `dynamic_inputs` keys MUST match the regex `^[a-z][a-z0-9_]*$` (snake_case identifiers). `session_id` MUST be a UUID4 string.

**Frozen**: yes. Constructed by `_handle_chat_request` immediately before the assembler runs.

---

## 3. `SystemPromptManifest`

The fully-assembled output of `PromptAssembler.build(ctx)`. The bytes that get sent to the LLM.

| Field | Type | Notes |
|---|---|---|
| `static_prefix` | `str` | The four-XML-section body of `prompts/system_v1.md`, concatenated with `## Available tools` (R6 enriched), terminated with the literal boundary marker `\nSYSTEM_PROMPT_DYNAMIC_BOUNDARY\n`. |
| `dynamic_suffix` | `str` | Concatenation of every registered decorator's return value (skipping `None` returns). Empty string when no decorator is registered or all return `None`. |
| `prefix_hash` | `str` | SHA-256 of `static_prefix.encode("utf-8")` rendered as 64 lowercase hex chars. Emitted as the OTEL `kosmos.prompt.hash` attribute. |

**Validation**: `static_prefix` MUST end with `\nSYSTEM_PROMPT_DYNAMIC_BOUNDARY\n`. `prefix_hash` MUST equal `sha256(static_prefix)` — enforced by a `@model_validator(mode="after")` that re-derives the hash and raises if it diverges.

**Frozen**: yes. Constructed by `PromptAssembler.build(ctx)`.

**Cache-prefix invariant**: For two `SystemPromptManifest` values built from the same registered tool inventory and the same `prompts/system_v1.md`, `prefix_hash` MUST be byte-identical regardless of `dynamic_inputs`. This is the FR-006 / FR-007 / SC-3 contract.

---

## 4. `ToolTriggerExamples` (extension to existing `GovAPITool` schema)

Additive Pydantic field on the existing tool-adapter schema. Lives in `src/kosmos/tools/_base.py` (existing module, additive change).

| Field | Type | Notes |
|---|---|---|
| `trigger_examples` | `list[str]` | Two to five short Korean utterances the tool covers. Default `[]`. Validated `len ≤ 5` (cap output token cost). |

**Backward compatibility**: Default `[]` ensures every adapter that has not yet opted in continues to register without modification. The R6 emission code skips the trigger-phrase line when the list is empty.

---

## 5. `CitizenRequestEnvelope`

A pure formatting helper (not a Pydantic model — it returns `str` directly). Lives in `src/kosmos/ipc/citizen_request.py` (new file, single function).

```python
def wrap_citizen_request(text: str) -> str: ...
```

Returns `f"<citizen_request>\n{text}\n</citizen_request>"` for any non-empty input. Empty input returns the empty string unchanged so the no-op path stays byte-stable. The function is not async, has no I/O, and contains no logging — pure transform.

**Why not a Pydantic model**: Wrapping is a one-line string operation; a Pydantic envelope would add type-system friction without buying any invariant the type system needs to enforce. Tests assert the wrap presence at the call-site through static `grep`, not by matching a model schema.

---

## 6. Decorator surface (function signatures, not data)

```python
DynamicSectionFn = Callable[[PromptAssemblyContext], str | None]

class PromptAssembler:
    def register(self, name: str, fn: DynamicSectionFn) -> None: ...
    def build(self, ctx: PromptAssemblyContext) -> SystemPromptManifest: ...
```

Decorator helper:

```python
def system_prompt(assembler: PromptAssembler, name: str) -> Callable[[DynamicSectionFn], DynamicSectionFn]:
    def decorator(fn: DynamicSectionFn) -> DynamicSectionFn:
        assembler.register(name, fn)
        return fn
    return decorator
```

**Type discipline**: `DynamicSectionFn` is a `Callable[..., str | None]` — fully typed, no `Any`. The `name` arg gives every registered injector a stable identity for memoization (the section cache key, mirroring CC `systemPromptSection`).

**Future extensions**: a `DANGEROUS_uncached_system_prompt(...)` decorator can be added when the first cache-breaking injector legitimately requires per-turn recomputation (CC pattern). Out of scope for this Epic.

---

## 7. Relationships

```text
prompts/system_v1.md ──parsed by──▶ PromptLoader
                                          │
                                          ▼
                          PromptSection × 4 (role/core_rules/tool_usage/output_style)
                                          │
                                          ▼
PromptAssembler(static_prefix, registry) ──build(ctx)──▶ SystemPromptManifest
                                                              │
                                                              ├── static_prefix (cacheable)
                                                              ├── prefix_hash (kosmos.prompt.hash)
                                                              └── dynamic_suffix (per-turn)

ChatRequestFrame.messages[].content (citizen) ──wrap_citizen_request──▶ <citizen_request>...</citizen_request>
                                                                              │
                                                                              ▼
                                                          fed to LLM as a "user" role message

GovAPITool.trigger_examples ──build_system_prompt_with_tools──▶ ## Available tools §<tool>:
                                                                          - description
                                                                          - **Trigger**: <phrase>
                                                                          - parameters JSON
```

---

## 8. State transitions

None. All shipped types are frozen. The only mutable surface is `PromptAssembler` itself, which accumulates registered decorators at module-load time and never mutates per-turn. Registration is conceptually a one-shot event triggered by Python module imports; the current Epic does not introduce any runtime registration path.
