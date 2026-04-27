# Contract — `system_prompt_builder.build_system_prompt_with_tools()`

> Epic [#2077](https://github.com/umyunsang/KOSMOS/issues/2077) · 2026-04-27
> A new Python helper that bridges `frame.tools` to the LLM's system prompt. Mirrors CC's `appendSystemContext()` pattern (`_cc_reference/api.ts`).

## Module

`src/kosmos/llm/system_prompt_builder.py` (NEW).

## Public API

```python
from kosmos.llm.client import LLMToolDefinition

def build_system_prompt_with_tools(
    base: str,
    tools: list[LLMToolDefinition],
) -> str:
    ...
```

## Inputs

| Parameter | Type | Description | Constraints |
|---|---|---|---|
| `base` | `str` | The unmodified system prompt body (e.g., contents of `prompts/system_v1.md` after placeholder interpolation). | Non-empty. |
| `tools` | `list[LLMToolDefinition]` | The active inventory passed to the LLM on this turn. | May be empty. |

## Output

| Case | Output |
|---|---|
| `tools` is empty | `base` unchanged (byte-identical). |
| `tools` is non-empty | `base + "\n\n## Available tools\n\n" + per_tool_blocks` where each per-tool block is the format defined below. |

## Per-tool block format

```
### {function.name}

{function.description}

**Parameters**:

```json
{json.dumps(function.parameters, indent=2, sort_keys=True, ensure_ascii=False)}
```


```

(Trailing blank line between blocks. The opening triple-backtick fence is `json` so the LLM treats it as a code block.)

## Determinism (REQUIRED)

The function MUST be byte-stable for byte-identical inputs:

- No `datetime.now()` / `time.time()` interpolation.
- No environment variable lookups.
- `json.dumps` MUST use `sort_keys=True` so JSON object key order is deterministic.
- Tool order in the output MUST match the input list order (caller is responsible for sorting if desired — `getToolDefinitionsForFrame()` on the TUI side sorts alphabetically by `function.name`).

This determinism is required by the Spec 026 prompt-hash invariant — though the augmentation is excluded from the `kosmos.prompt.hash` span attribute (which hashes only `base`), the augmented text is reused inside the prompt cache for the LLM provider, and reuse depends on byte stability.

## Caller pattern

Single caller: `src/kosmos/ipc/stdio.py:_handle_chat_request`.

```python
from kosmos.llm.system_prompt_builder import build_system_prompt_with_tools

# existing line: gather base from frame.system or _ensure_system_prompt()
base_system = frame.system or await _ensure_system_prompt()
augmented_system = build_system_prompt_with_tools(base_system, llm_tools)

llm_messages.insert(0, LLMChatMessage(role="system", content=augmented_system))
```

## Edge cases

- `base` is empty string → return `"" + "\n\n## Available tools\n\n" + per_tool_blocks` (caller responsibility to ensure base non-empty; helper does not raise).
- `tools` contains a definition whose `function.parameters` is `None` → render as `{}` (treat as no-parameter tool).
- `function.description` contains backticks → no escaping (LLM tolerates code in descriptions).
- `function.parameters` contains nested objects with mixed types → `json.dumps` handles natively.
- Korean text in `function.description` → `ensure_ascii=False` keeps the Korean characters readable in the prompt.

## Test coverage (`tests/llm/test_system_prompt_builder.py`)

| Test | Asserts |
|---|---|
| `test_empty_tools_returns_base_unchanged` | Output identical to `base` byte-for-byte. |
| `test_single_tool_appends_section` | Output ends with `### lookup\n...\n\`\`\`\n` block. |
| `test_byte_stable_for_same_input` | Two calls with identical inputs return identical strings. |
| `test_korean_description_preserved` | Korean characters in `description` round-trip. |
| `test_sort_keys_invariant` | Two calls with same tool but different parameter dict insertion order produce same output. |
| `test_multiple_tools_alphabetic_input_preserved` | Output preserves caller's order (no sorting inside helper). |
| `test_no_timestamp_or_env_leakage` | grep output for `2026` / `KOSMOS_` env vars — none present unless caller-provided. |

## OTEL attributes

- `kosmos.system_prompt.augmented_chars` (int) — len(augmented) - len(base). Useful for debugging prompt budget.
- `kosmos.system_prompt.tool_count` (int) — number of tools rendered into the section.
