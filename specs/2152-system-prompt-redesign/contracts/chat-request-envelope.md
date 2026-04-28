# Contract — Chat-Request Citizen Envelope (R3) + Boundary Wiring (R4) at the IPC Boundary

**Spec**: [../spec.md](../spec.md) · **Plan**: [../plan.md](../plan.md) · **Research**: [../research.md](../research.md) (R3 + R4 + R5)

Defines the behaviour of `src/kosmos/ipc/stdio.py:_handle_chat_request` (lines 1129–1230 today, adjusted by this Epic) for assembling the LLM message stack from a `ChatRequestFrame`. The IPC schema itself is unchanged (no `frames.generated.ts` modification, no Pydantic model bump).

---

## Behaviour change summary

| Step | Before this Epic | After this Epic |
|---|---|---|
| 1. Tool inventory | Computed from `frame.tools` then `ToolRegistry.export_core_tools_openai()`. Unchanged. | Unchanged. |
| 2. Static prompt | `frame.system or ""` consumed directly. | Loaded via `PromptAssembler.build(ctx).static_prefix` (assembler authoritative; `frame.system` ignored when empty so the new system prompt path is the default). |
| 3. Tool inventory augmentation | `build_system_prompt_with_tools(base, llm_tools)` appends `## Available tools`. | Same call, but `build_system_prompt_with_tools` now emits the R6 trigger phrase per tool. |
| 4. Boundary marker | Absent. | Inserted by the assembler — `static_prefix` always ends with `\nSYSTEM_PROMPT_DYNAMIC_BOUNDARY\n`. |
| 5. Dynamic suffix | Absent. | `SystemPromptManifest.dynamic_suffix` appended after the boundary marker if any decorator returned a non-`None` string. |
| 6. OTEL attribute | `kosmos.prompt.hash` hashed the entire system text. | `kosmos.prompt.hash = manifest.prefix_hash` — hashes only the prefix up to (but not including) the boundary marker. |
| 7. User-message wrap | Citizen text passed through unchanged. | Citizen text wrapped via `wrap_citizen_request(text)` for messages whose `role == "user"`. Other roles (`tool`, `assistant`, `system`) are not wrapped. |

---

## R3 — Citizen utterance envelope

For each `ChatMessage` the backend constructs from `frame.messages`:

```python
def wrap_citizen_request(text: str) -> str:
    if not text:
        return text  # byte-stable for empty no-op
    return f"<citizen_request>\n{text}\n</citizen_request>"
```

Applied only when the message `role == "user"`. The wrap is added *after* the `LLMChatMessage` is constructed and before it is appended to the `llm_messages` list. The wrap is byte-stable — no whitespace stripping, no normalisation, no encoding transformation.

**Why only `role == "user"`**: tool-result messages (`role == "tool"`) and assistant continuations (`role == "assistant"`) are produced by the agentic loop itself, not by the citizen, so they are not prompt-injection vectors. System messages (`role == "system"`) carry the trusted instructions and explicitly must not be wrapped.

---

## R4 — Boundary marker + cache-prefix hash

The `static_prefix` returned by `PromptAssembler.build(ctx)` always ends with the literal:

```text

SYSTEM_PROMPT_DYNAMIC_BOUNDARY

```

(leading and trailing newlines included). The `prefix_hash` is `sha256(static_prefix.encode("utf-8")).hexdigest()` — recorded as the OTEL `kosmos.prompt.hash` attribute on the chat-request span (Spec 021 surface; the existing emission point in `_handle_chat_request` is updated to read from `manifest.prefix_hash` instead of recomputing).

The dynamic suffix is concatenated after the boundary marker without any separator:

```text
{static_prefix}{dynamic_suffix}
```

Empty `dynamic_suffix` is the common path (no decorator registered or all decorators return `None`); in that case the boundary marker still appears, terminating the system message. Tests assert presence regardless of injector activity.

---

## R5 — Developer-context excision (TUI side)

The Python contract above receives `frame.system` from the TUI. The TUI changes (excising `getSystemContext` / `getUserContext` / `appendSystemContext` / `prependUserContext` from the chat-request emit path) are governed by the spec.md SC-4 audit rule. The Python contract is intentionally tolerant: `frame.system` may be empty (the new default after R5) or may carry an externally-injected override (current TUI behaviour). The assembler is the source-of-truth — when the TUI sends an empty `frame.system`, the assembler-built prefix is used; when the TUI sends a non-empty `frame.system`, current behaviour is preserved for parity tests during the migration.

After R5 ships, the production TUI path always sends `frame.system == ""`. The conditional path is kept for one Epic for compatibility; a follow-up Epic may remove it.

---

## Invariants (enforced by tests)

| ID | Invariant | Test location |
|---|---|---|
| I-C1 | After `_handle_chat_request` constructs `llm_messages`, the system message contains the literal `\nSYSTEM_PROMPT_DYNAMIC_BOUNDARY\n` exactly once (R4). | `tests/ipc/test_stdio_chat_request.py::test_boundary_marker_in_system_message` |
| I-C2 | The OTEL span emitted for the chat request carries `kosmos.prompt.hash` equal to `sha256(static_prefix).hexdigest()` (R4 + Spec 021). | `tests/ipc/test_stdio_chat_request.py::test_prompt_hash_matches_prefix` |
| I-C3 | Every `LLMChatMessage` whose `role == "user"` has content starting with `<citizen_request>\n` and ending with `\n</citizen_request>` (R3). | `tests/ipc/test_stdio_chat_request.py::test_user_messages_wrapped` |
| I-C4 | No `LLMChatMessage` whose `role` is `"tool"`, `"assistant"`, or `"system"` is wrapped (R3 negative assertion). | `tests/ipc/test_stdio_chat_request.py::test_non_user_messages_not_wrapped` |
| I-C5 | Two consecutive chat requests in the same session with the same registered tool inventory produce byte-identical `kosmos.prompt.hash` values across both spans (SC-3). | `tests/ipc/test_stdio_chat_request.py::test_prompt_hash_byte_stable_across_turns` |
| I-C6 | Empty user-message content is not wrapped — `wrap_citizen_request("") == ""` (FR-015 spirit; no-op invariance). | `tests/ipc/test_stdio_chat_request.py::test_empty_user_no_wrap` |

---

## Out of scope for this contract

- Adding new IPC frame arms or fields. The existing `ChatRequestFrame` is sufficient.
- Changing the agentic-loop turn budget (`KOSMOS_AGENTIC_LOOP_MAX_TURNS`). Owned by Spec 1978 / Epic #2077.
- Streaming token emission shape (`AssistantChunkFrame`). Unchanged.
