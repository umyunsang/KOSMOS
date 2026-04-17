---
# Session compaction template — consumed by src/kosmos/context/session_compact.py
# T031 loader: call PromptLoader.load("compact_v1"), parse frontmatter with yaml.safe_load,
# then map these keys into the builder constants that replace the inline Final[str] values.
summary_header: "[Session Summary — older turns compacted]"
section_labels:
  user_requests: "User requests in this session:"
  tool_calls: "Tool calls executed:"
  tool_results: "Key tool results:"
  assistant_responses: "Assistant responses:"
empty_state: "(No significant content found in compacted turns.)"
truncation_marker: "[Summary truncated]"
line_prefix: "  - "
formatters:
  tool_call: "tool_call:{name}({args_excerpt})"
  tool_result: "tool_result[{call_id}]: {excerpt}"
  assistant: "assistant: {excerpt}"
  user: "user: {excerpt}"
---

# Session compaction template v1

This template carries the literal strings the rule-based compactor in
`src/kosmos/context/session_compact.py` emits. The refactor (T031) loads this
file via `PromptLoader.load("compact_v1")` and parses the frontmatter.

## Key mapping for T031

| frontmatter key | replaces inline constant / literal |
|---|---|
| `summary_header` | `_SUMMARY_HEADER: Final[str]` |
| `section_labels.user_requests` | `"User requests in this session:"` in `_build_summary_text` |
| `section_labels.tool_calls` | `"Tool calls executed:"` in `_build_summary_text` |
| `section_labels.tool_results` | `"Key tool results:"` in `_build_summary_text` |
| `section_labels.assistant_responses` | `"Assistant responses:"` in `_build_summary_text` |
| `empty_state` | `"(No significant content found in compacted turns.)"` |
| `truncation_marker` | `"[Summary truncated]"` appended after `char_budget` truncation |
| `line_prefix` | `f"  - {line}"` f-string prefix in `_build_summary_text` |
| `formatters.tool_call` | `f"tool_call:{tc.function.name}({args_excerpt})"` in `_extract_tool_calls` |
| `formatters.tool_result` | `f"tool_result[{call_id}]: {excerpt}"` in `_extract_tool_results` |
| `formatters.assistant` | `f"assistant: {excerpt}"` in `_extract_assistant_decisions` |
| `formatters.user` | `f"user: {excerpt}"` in `_extract_user_intents` |

## Non-externalised constants (implementation-only, not in template)

The following constants remain in code because they control algorithmic
behaviour, not text output, and are not visible in the golden fixture:

- `_MAX_RESULT_EXCERPT_CHARS = 200` — truncation limit for tool results
- `_MAX_ASSISTANT_EXCERPT_CHARS = 300` — truncation limit for assistant excerpts
- `_SUMMARY_ROLE = "system"` — message role, not text content
- `200` (user excerpt limit in `_extract_user_intents`) — same rationale
- `80` (args excerpt limit in `_extract_tool_calls`) — same rationale
- `40` (min content length skip threshold) — same rationale
