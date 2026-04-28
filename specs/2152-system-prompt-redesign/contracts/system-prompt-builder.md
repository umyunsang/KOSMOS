# Contract — `kosmos.llm.system_prompt_builder.build_system_prompt_with_tools` (R6 extension)

**Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md) · **Research**: [../research.md](../research.md) (R6)

Extends the existing function at `src/kosmos/llm/system_prompt_builder.py:30-80` to emit one extra line per tool — the trigger phrase — alongside the structured description block. Backward-compatible additive change.

---

## Existing signature (preserved)

```python
def build_system_prompt_with_tools(
    base: str,
    tools: list[LLMToolDefinition],
) -> str: ...
```

Behavior unchanged for `tools == []`: returns `base` byte-for-byte (FR-015 invariant — required so existing tests that exercise the no-tools path keep passing without modification).

---

## R6 emission format

For every non-empty `tools` list, the function emits the existing `## Available tools` section header, then one block per tool. The per-tool block is augmented as follows:

**Before R6 (today)**:
```text
### kma_forecast_fetch

Fetch a Korean weather forecast for a region.

**Parameters**:

```json
{ ... }
```
```

**After R6**:
```text
### kma_forecast_fetch

Fetch a Korean weather forecast for a region.

**Trigger**: 사용자가 한국 지역의 날씨, 기온, 비, 눈, 태풍을 물을 때 호출 — 예: "오늘 서울 날씨 알려줘", "내일 부산 비 와?", "주말 제주 날씨".

**Parameters**:

```json
{ ... }
```
```

The trigger line is inserted between the description and the `**Parameters**:` header. Format:

```text
**Trigger**: <human-readable Korean sentence ending with a period> — 예: "<utterance 1>", "<utterance 2>"[, "<utterance 3>"].
```

---

## Sourcing the trigger phrase

The phrase is built deterministically from the tool's existing schema fields:

1. **Description sentence** — derived from `tool.search_hint` (existing field, Spec 022 hard rule). The Korean half of the bilingual hint is the human-readable description.
2. **Example utterances** — derived from the new `trigger_examples: list[str]` Pydantic field on `GovAPITool` (see [data-model.md §4](../data-model.md)). Default `[]` keeps backward compatibility.

When `trigger_examples` is empty, the function still emits the `**Trigger**:` line using only the `search_hint`-derived sentence (no `— 예:` clause). This is intentional: every tool gets at least a one-line trigger phrase, even if no contributor has yet authored explicit example utterances.

---

## Invariants (enforced by tests)

| ID | Invariant | Test location |
|---|---|---|
| I-B1 | `build_system_prompt_with_tools(base, [])` returns exactly `base` byte-for-byte (FR-015, no-tools no-op invariant). | `tests/llm/test_system_prompt_builder.py::test_no_tools_byte_identical` |
| I-B2 | Every emitted per-tool block contains exactly one line starting with `**Trigger**: ` immediately above `**Parameters**:`. | `tests/llm/test_system_prompt_builder.py::test_trigger_line_present_per_tool` |
| I-B3 | When `trigger_examples == []`, the trigger line contains no `— 예:` clause (and no trailing whitespace). | `tests/llm/test_system_prompt_builder.py::test_trigger_line_no_examples` |
| I-B4 | When `trigger_examples` is non-empty, every example string appears verbatim wrapped in double quotes within the trigger line. | `tests/llm/test_system_prompt_builder.py::test_trigger_line_with_examples_quotes` |
| I-B5 | Output is deterministic: two calls with identical inputs produce byte-identical strings (cache-prefix prerequisite for R4). | `tests/llm/test_system_prompt_builder.py::test_deterministic_output` |
| I-B6 | Augmentation only appends; `base` text is unchanged in output prefix bytes. | `tests/llm/test_system_prompt_builder.py::test_base_unchanged_prefix` |

---

## Out of scope for this contract

- Localising the `**Trigger**:` literal to multiple languages. Korean-primary only this Epic; multi-language is in the Deferred table.
- Generating trigger phrases via LLM at registry build time. Rejected in research.md §6 — non-determinism conflicts with cache-prefix invariance.
