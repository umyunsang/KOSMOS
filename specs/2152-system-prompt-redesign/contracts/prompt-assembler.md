# Contract — `kosmos.llm.prompt_assembler`

**Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md) · **Research**: [../research.md](../research.md) (R2 + R4)

Defines the public Python surface introduced by Epic #2152 for citizen-domain system-prompt assembly. The module is consumed by `src/kosmos/ipc/stdio.py:_handle_chat_request` exactly once per chat request, immediately after the active tool inventory is computed.

---

## Public surface

### `PromptAssembler`

```python
from kosmos.llm.prompt_assembler import (
    PromptAssembler,
    PromptAssemblyContext,
    SystemPromptManifest,
    DynamicSectionFn,
    system_prompt,
)
```

#### Constructor

```python
PromptAssembler(static_prefix_source: PromptLoader)
```

- `static_prefix_source` — the existing Spec 026 `PromptLoader`. The assembler calls `static_prefix_source.load("system_v1")` exactly once at instantiation time and caches the result; subsequent `build()` calls reuse the cached static prefix.
- The constructor MUST NOT perform any network or registry I/O.
- The constructor MUST validate that the loaded prompt text contains all four required XML tag pairs (`<role>...</role>`, `<core_rules>...</core_rules>`, `<tool_usage>...</tool_usage>`, `<output_style>...</output_style>`). On absence: raise `PromptAssemblyError` (new exception subclassing `ValueError`).

#### `register(name: str, fn: DynamicSectionFn) -> None`

- `name` — snake_case identifier; matches `^[a-z][a-z0-9_]*$`. Must be unique within the assembler. On duplicate: raise `PromptAssemblyError`.
- `fn` — `Callable[[PromptAssemblyContext], str | None]`. Pure function preferred; the assembler does not enforce purity but assumes it for cache-prefix invariance.
- Decorator order is preserved: registration order = emission order in the dynamic suffix.

#### `build(ctx: PromptAssemblyContext) -> SystemPromptManifest`

- Constructs a `SystemPromptManifest` (see [data-model.md §3](../data-model.md)).
- Returns immediately if no decorators are registered (`dynamic_suffix` is empty string).
- The returned `static_prefix` MUST end with `\nSYSTEM_PROMPT_DYNAMIC_BOUNDARY\n`.
- The returned `prefix_hash` MUST equal `hashlib.sha256(static_prefix.encode("utf-8")).hexdigest()`.
- The function MUST NOT raise for any combination of registered decorators returning `None`. `None` is the documented opt-out (CC parity — see `restored-src/.../prompts.ts` `.filter(s => s !== null)`).

### `system_prompt` decorator

```python
@system_prompt(assembler, name="ministry_scope")
def ministry_scope_section(ctx: PromptAssemblyContext) -> str | None:
    scope = ctx.dynamic_inputs.get("ministry_scope")
    if not scope:
        return None
    return f"<ministry_scope>{scope}</ministry_scope>"
```

- Sugar over `assembler.register(name, fn)` so injector authors get a familiar Pydantic-AI-style declaration site.
- The decorator returns the original function unmodified so it remains directly callable for unit tests.

---

## Invariants (enforced by tests)

| ID | Invariant | Test location |
|---|---|---|
| I-A1 | Same `prompts/system_v1.md` + same registered tool inventory ⇒ identical `static_prefix` byte stream regardless of `dynamic_inputs` (FR-006). | `tests/llm/test_prompt_assembler.py::test_static_prefix_byte_stable_across_dynamic_inputs` |
| I-A2 | `prefix_hash == sha256(static_prefix)` for every `build()` return (FR-007). | `tests/llm/test_prompt_assembler.py::test_prefix_hash_matches_static_prefix` |
| I-A3 | Static prefix terminates with the literal `\nSYSTEM_PROMPT_DYNAMIC_BOUNDARY\n` (R4). | `tests/llm/test_prompt_assembler.py::test_boundary_marker_present` |
| I-A4 | All four XML tag pairs present in `prompts/system_v1.md` and reflected in the static prefix (R1, SC-2). | `tests/llm/test_prompt_assembler.py::test_xml_tag_presence` |
| I-A5 | A registered injector that returns `None` is omitted from the dynamic suffix without producing a stray newline. | `tests/llm/test_prompt_assembler.py::test_none_return_is_omitted` |
| I-A6 | Two `build(ctx)` calls in the same process with identical `ctx` produce byte-identical `SystemPromptManifest.static_prefix` and `prefix_hash` (cache-prefix idempotence, supports SC-3). | `tests/llm/test_prompt_assembler.py::test_build_idempotent_for_same_context` |
| I-A7 | `register` is idempotent on the same `(name, fn)` pair — second registration with identical name and function is a no-op; mismatched function under the same name raises. | `tests/llm/test_prompt_assembler.py::test_register_dup_name` |

---

## Error envelope

| Exception | When | Caller obligation |
|---|---|---|
| `PromptAssemblyError` (new) | Required XML tag missing in `prompts/system_v1.md`; duplicate decorator name with mismatched function; static prefix does not end with the boundary marker | `_handle_chat_request` MUST log at WARNING and emit an `error` IPC frame with the existing schema. The chat request itself is rejected. |

The exception is fail-closed: if assembly fails the chat request does not proceed. This is consistent with constitution Principle II (Fail-Closed Security) and with Spec 026's existing fail-closed-at-boot prompt-registry contract.

---

## Out of scope for this contract

- Memoization of decorator returns (CC `getSystemPromptSectionCache`). Sugar to add when a future injector legitimately benefits from session-scoped caching. Keep the surface minimal in this Epic.
- `DANGEROUS_uncached_system_prompt` decorator (CC parity). Not added until the first uncached use case lands.
- Override hierarchy (CC `restored-src/.../utils/systemPrompt.ts:30-123`). KOSMOS does not yet expose `--system-prompt` / coordinator / agent overrides.
