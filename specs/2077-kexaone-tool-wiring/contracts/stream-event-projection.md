# Contract — Stream-event projection for `tool_call` / `tool_result` frames

> Epic [#2077](https://github.com/umyunsang/KOSMOS/issues/2077) · 2026-04-27
> `deps.ts` projects each `tool_call` frame into two CC stream events and each `tool_result` frame into a user-role transcript message. Mirrors `_cc_reference/claude.ts:1995-2052` and `_cc_reference/messages.ts:ensureToolResultPairing()`.

## Module

`tui/src/query/deps.ts` (modified — Steps 5 and 6).

## Current behavior (line 237-249)

```typescript
} else if (fa.kind === 'tool_call') {
  const argsPreview = summarizeArgs(fa.arguments)
  yield createSystemMessage(`🔧 ${fa.name ?? '(unknown tool)'}${argsPreview}`, 'info', fa.call_id)
} else if (fa.kind === 'tool_result') {
  const env = fa.envelope ?? {}
  const status = (env.kind as string | undefined) ?? 'done'
  const summary = summarizeResult(env)
  yield createSystemMessage(`✓ ${status}${summary}`, 'info', fa.call_id)
}
```

## New behavior — `tool_call` frame projection

```typescript
} else if (fa.kind === 'tool_call') {
  // CC pattern (claude.ts:1995-2052): yield content_block_start + content_block_stop
  // for each tool_use block. handleMessageFromStream pushes to streamingToolUses;
  // AssistantToolUseMessage renders natively on terminal message_stop.
  const toolUseBlock = {
    type: 'tool_use' as const,
    id: fa.call_id ?? '',
    name: fa.name ?? '(unknown)',
    input: fa.arguments ?? {},
  }
  yield {
    type: 'stream_event' as const,
    event: {
      type: 'content_block_start' as const,
      index: ++blockIndex,
      content_block: toolUseBlock,
    },
  }
  yield {
    type: 'stream_event' as const,
    event: {
      type: 'content_block_stop' as const,
      index: blockIndex,
    },
  }
  // Also accumulate into the assistant message's content array so the
  // terminal AssistantMessage carries the tool_use block (used by
  // handleMessageFromStream:line 2935-3099 for transcript persistence).
  pendingContentBlocks.push(toolUseBlock)
}
```

## New behavior — `tool_result` frame projection

```typescript
} else if (fa.kind === 'tool_result') {
  // CC pattern (messages.ts:ensureToolResultPairing): user-role message
  // carrying a single tool_result content block. The next LLM turn picks
  // it up as part of context (FR-010).
  const env = fa.envelope ?? {}
  const isError = env.kind === 'error'
  yield createUserMessage([{
    type: 'tool_result' as const,
    tool_use_id: fa.call_id ?? '',
    content: JSON.stringify(env),
    ...(isError ? { is_error: true as const } : {}),
  }])
}
```

## State variables added to `deps.ts`

```typescript
let blockIndex = 0  // already exists implicitly in fdfd3e9 paint chain — promote to explicit
const pendingContentBlocks: ContentBlock[] = []  // collects text + tool_use blocks for terminal AssistantMessage
```

## `blockIndex` continuity

After `fdfd3e9`, `deps.ts` emits `content_block_start{index: 0, type: 'text'}` on the first chunk. Subsequent `content_block_delta` events use `index: 0`. This epic adds `tool_use` blocks at `index >= 1`. The CC convention is sequential, gap-free indexing. Implementation MUST:

- Initialize `blockIndex = 0` at turn start (alongside `messageStartEmitted = false`).
- Increment **before** emitting `content_block_start` for each `tool_use`.
- The text block remains at `index: 0`; tool_use blocks fill `1, 2, …`.

## Terminal `AssistantMessage` content array

The final `createAssistantMessage` (today on `done=true` chunk) must include the accumulated tool_use blocks alongside the accumulated text:

```typescript
if (fa.done === true) {
  // existing text accumulation
  const finalContent: ContentBlock[] = [
    { type: 'text' as const, text: accumulated },
    ...pendingContentBlocks,
  ]
  yield createAssistantMessage(finalContent, /* ... existing args */)
  // emit message_stop / content_block_stop chain (existing)
  return
}
```

## `handleMessageFromStream` integration

`tui/src/utils/messages.ts` already routes:

- `content_block_start{type: 'tool_use'}` → push to `streamingToolUses`.
- `content_block_stop` for a tool_use index → seal the block.
- AssistantMessage with tool_use content blocks → render via `AssistantToolUseMessage`.

No modifications to `messages.ts` are required for Steps 5/6. This contract is satisfied entirely by `deps.ts` changes.

## Pairing invariant enforcement

For every `tool_call` frame with `call_id = X`, there MUST eventually be a `tool_result` frame with `call_id = X` before the agentic loop terminates. This is the backend's responsibility (already enforced in `stdio.py` agentic loop). The TUI projection layer simply propagates the pairing.

If the backend emits a `tool_result` frame whose `call_id` does not match any prior `tool_call` (orphan):

- Today: created as SystemMessage progress line (silently absorbed).
- After this change: appears as a user-role tool_result message with `tool_use_id` that has no prior tool_use block → `handleMessageFromStream` surfaces an `ErrorEnvelope` (existing component, 113 LOC) marking it as orphan. FR-009 satisfied.

## Test coverage

### `tui/tests/ipc/handlers.test.ts` (modified)

| Test | Asserts |
|---|---|
| `tool_call frame yields two stream events` | First yield is `content_block_start{type: 'tool_use'}`, second is `content_block_stop`. No SystemMessage. |
| `tool_call sets correct content_block_start fields` | `content_block.id === fa.call_id`, `content_block.name === fa.name`, `content_block.input === fa.arguments`. |
| `tool_result frame yields createUserMessage with tool_result content block` | One yielded message; role 'user'; content[0].type === 'tool_result'; `tool_use_id` matches. |
| `tool_result is_error flag set when envelope.kind === 'error'` | `is_error: true` present in content block. |
| `multiple tool_call in same turn produce sequential indices` | Block indices 1, 2, 3 (text block at 0). |
| `terminal AssistantMessage contains tool_use blocks alongside text` | content array length 1 + N where N is number of tool calls. |

### Backend integration test (`tests/integration/test_agentic_loop.py`)

- Citizen prompt → backend emits `tool_call` → backend emits `tool_result` → next LLM turn includes both in context → final answer references tool result.

## OTEL spans

No new spans introduced. Existing spans on `tool_call` / `tool_result` frames already carry `kosmos.tool.name`, `kosmos.tool.call_id`, `kosmos.tool.duration_ms`. The projection is a TUI-side transformation invisible to backend OTEL.
