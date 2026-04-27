# Contract — `toolToFunctionSchema()` + `getToolDefinitionsForFrame()` (TS)

> Epic [#2077](https://github.com/umyunsang/KOSMOS/issues/2077) · 2026-04-27
> New TypeScript module that converts the TUI's Zod-defined tool catalog into `ToolDefinition[]` for `ChatRequestFrame.tools`. Uses `zod/v4`'s built-in `z.toJSONSchema()` (verified Draft 2020-12 in research § R-1).

## Module

`tui/src/query/toolSerialization.ts` (NEW).

## Public API

```typescript
import { z } from 'zod/v4'
import type { Tool } from '../Tool.js'
import type { ToolDefinition } from '../ipc/codec.js'

export function toolToFunctionSchema(tool: Tool): ToolDefinition

export function getToolDefinitionsForFrame(): ToolDefinition[]
```

## `toolToFunctionSchema(tool)` semantics

Converts a single Tool into a single ToolDefinition.

```typescript
export function toolToFunctionSchema(tool: Tool): ToolDefinition {
  const schema = tool.inputSchema
  const description = tool.description ? await tool.description() : ''
  const prompt = tool.prompt ? (await tool.prompt()).slice(0, 200) : ''
  return {
    type: 'function' as const,
    function: {
      name: tool.name,
      description: [description, prompt].filter(Boolean).join('\n\n'),
      parameters: z.toJSONSchema(schema) as Record<string, unknown>,
    },
  }
}
```

> **Note**: this is the synchronous *shape* of the contract. Tool's `description()` and `prompt()` are async — the implementation MUST be `async function toolToFunctionSchema(tool): Promise<ToolDefinition>` and `getToolDefinitionsForFrame()` MUST be async. The existing `deps.ts` already runs in an async generator context, so this is fine.

## `getToolDefinitionsForFrame()` semantics

Walks the TUI's tool catalog and returns the publishable inventory.

```typescript
export async function getToolDefinitionsForFrame(): Promise<ToolDefinition[]> {
  const allTools = getAllBaseTools()  // existing in tui/src/tools.ts
  const visible = allTools.filter(isPublishedToLLM)
  const defs = await Promise.all(visible.map(toolToFunctionSchema))
  return defs.sort((a, b) => a.function.name.localeCompare(b.function.name))
}
```

`isPublishedToLLM(tool)` is a local predicate that returns true only for the five primitives + the MVP-7 auxiliary tools. This is the source of the FR-003 single-source rule on the TUI side.

## Filter rule (`isPublishedToLLM`)

| Tool name | Published to LLM? | Source |
|---|---|---|
| `lookup` | ✓ | Migration Tree § L1-C.C1 (root primitive) |
| `resolve_location` | ✓ | Migration Tree § L1-C.C1 |
| `submit` | ✓ | Migration Tree § L1-C.C1 |
| `subscribe` | ✓ | Migration Tree § L1-C.C1 |
| `verify` | ✓ | Migration Tree § L1-C.C1 |
| `WebFetch`, `WebSearch`, `Task`, `Translate`, `Calculator`, `DateParser`, `ExportPDF` | ✓ | Migration Tree § L1-C.C6 (MVP-7) |
| `Read`, `Write`, `Edit`, `Bash`, `Glob`, `Grep`, `NotebookEdit` | ✗ | Migration Tree § L1-C.C6 (excluded — citizen UX) |
| Plugin tools (`plugin.*`) | ✗ this epic | Epic #1979 introduces in Phase P5 |

## Zod-to-JSON-Schema conversion guarantees

Per research § R-1 verification, `z.toJSONSchema()` from `zod/v4`:

- Emits `"$schema": "https://json-schema.org/draft/2020-12/schema"` natively.
- Preserves `.describe(...)` strings as JSON Schema `description`.
- Preserves `.min(N)` / `.max(N)` / `.int()` as `minLength` / `maxLength` / `minimum` / `maximum` / `type: integer`.
- Handles `z.discriminatedUnion(...)` as `anyOf` (used by `LookupPrimitive`, `SubscribePrimitive`).
- Handles `z.literal(...)` as `const`.
- Handles `z.optional()` correctly (excluded from `required` array).
- Sets `additionalProperties: false` by default.

These guarantees are testable — `tui/tests/tools/serialization.test.ts` includes one assertion per guarantee.

## Test coverage (`tui/tests/tools/serialization.test.ts`)

| Test | Asserts |
|---|---|
| `lookup-primitive emits draft 2020-12 schema` | Output contains `$schema: 'https://json-schema.org/draft/2020-12/schema'` and `anyOf` discriminant for mode. |
| `submit-primitive describes preserved` | `.describe(...)` strings in primitive Zod schema appear in JSON Schema `description`. |
| `optional fields excluded from required` | `top_k` (optional) absent from `required`; `mode` and `query` present. |
| `getToolDefinitionsForFrame returns >= 5 entries` | 5 primitives at minimum. |
| `getToolDefinitionsForFrame is alphabetically sorted` | `.map(d => d.function.name)` is sorted. |
| `getToolDefinitionsForFrame excludes Read/Bash/etc` | Output names ∩ `{Read, Bash, Glob}` = ∅. |
| `serialization is deterministic` | Two calls produce structurally equal output. |

## OTEL attributes (TUI side)

- `kosmos.tools.serialized.count` (int) — number of definitions emitted.
- `kosmos.tools.serialized.duration_ms` (float) — wall-clock for the serialization pass.

## Performance budget

- `getToolDefinitionsForFrame()` is called once per `chat_request`. Budget: ≤ 50ms on the dev laptop baseline (5 primitives + 7 auxiliary = 12 schemas; Zod conversion is fast).
- `Tool.description()` and `Tool.prompt()` are async but always memoized in existing tool implementations — the wall-clock is dominated by the first call per session.
