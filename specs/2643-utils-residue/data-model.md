# Data Model — Epic G · Utils 잔존 정리 (Phase 1)

**Date**: 2026-05-03
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

This Epic introduces 1 new TypeScript type and re-exposes 2 existing CC function shapes. No persistent data, no schema migration, no Pydantic models.

## E1 — `YoloClassifierResult` (TypeScript type alias)

**Module**: `tui/src/utils/permissions/yoloClassifier.ts`

**Source-of-truth**: UMMAYA-side stub (CC's interior is Spec 1633 deletion target; the type *shape* is preserved for callsite stability).

**Definition**:

```ts
export type YoloClassifierResult = {
  unavailable: boolean
  shouldBlock: boolean
  errorDumpPath?: string
  usage?: {
    inputTokens?: number
    outputTokens?: number
    cacheReadInputTokens?: number
    cacheCreationInputTokens?: number
  }
  model?: string
  durationMs?: number
  promptLengths?: {
    systemPrompt?: number
    toolCalls?: number
    userPrompts?: number
  }
  stage?: string
  stage1Usage?: { inputTokens?: number; outputTokens?: number; cacheReadInputTokens?: number; cacheCreationInputTokens?: number }
  stage1DurationMs?: number
  stage1RequestId?: string
  stage1MsgId?: string
  stage2Usage?: { inputTokens?: number; outputTokens?: number; cacheReadInputTokens?: number; cacheCreationInputTokens?: number }
  stage2DurationMs?: number
  stage2RequestId?: string
  stage2MsgId?: string
}
```

**Rationale**: Byte-identical with the inline shape currently absorbed in `permissions.ts:103-145`. Moving the type to the sibling `yoloClassifier.ts` module is a pure refactor — callsites see the same surface.

**Validation rules**:
- Always returned with `unavailable: true, shouldBlock: false` (UMMAYA auto-mode = no-op per Spec 1633).
- All optional fields remain `undefined` in the stub (CC's stage1/stage2 telemetry not surfaced).

**Lifecycle**: Created on every `classifyYoloAction` invocation; consumed by `permissions.ts` decision branches; not persisted.

## E2 — `DateTimeParseResult` (re-exposed from CC)

**Module**: `tui/src/utils/mcp/dateTimeParser.ts` (PORT target)

**Source-of-truth**: `.references/.../utils/mcp/dateTimeParser.ts:6-8` (byte-copy).

**Definition** (byte-identical with CC):

```ts
export type DateTimeParseResult =
  | { success: true; value: string }
  | { success: false; error: string }
```

**Validation rules**:
- `success: true` ⇒ `value` is a non-empty ISO 8601 string passing the `^\d{4}` sanity check (FR-008).
- `success: false` ⇒ `error` is a user-facing message (English source per AGENTS.md hard rule).

**Lifecycle**: Returned synchronously from `parseNaturalLanguageDateTime` to `validateElicitationInputAsync`; not persisted.

**Migration impact**: `tui/src/utils/mcp/elicitationValidation.ts` currently defines a local `type DateParseResult = ...` (line 15) — this MUST be deleted in favor of importing `DateTimeParseResult` from `./dateTimeParser.js`. (Note: the inline local was named `DateParseResult` to avoid shadowing — after deletion, callsites in `elicitationValidation.ts:324-339` already use the same shape, so import-only refactor.)

## E3 — Functional Surfaces (no new types — function-shape contracts)

### `generateSessionTitle`

**Module**: `tui/src/utils/sessionTitle.ts` (PORT target)

**Source-of-truth**: `.references/.../utils/sessionTitle.ts:79-129` (byte-copy except SWAP comment).

**Signature**:

```ts
export async function generateSessionTitle(
  description: string,
  signal: AbortSignal,
): Promise<string | null>
```

**Behavior contract**:
1. Empty/whitespace `description` → return `null` immediately (no K-EXAONE call).
2. Calls `queryHaiku` with system prompt `SESSION_TITLE_PROMPT` + JSON schema constraint.
3. Parses response with `safeParseJSON` + zod `titleSchema`.
4. Returns `parsed.data.title.trim() || null`.
5. Catches all errors; returns `null` on any failure.
6. Emits `tengu_session_title_generated` analytics event with `{success: title !== null}`.

**Side effects**:
- `logEvent('tengu_session_title_generated', ...)` on every invocation.
- `logForDebugging(..., {level: 'error'})` on caught error path.

### `extractConversationText`

**Module**: `tui/src/utils/sessionTitle.ts` (PORT target)

**Signature** (byte-copy CC):

```ts
export function extractConversationText(messages: Message[]): string
```

**Behavior contract**:
1. Filters to `user` + `assistant` typed messages with no `isMeta` flag and no non-human `origin`.
2. Concatenates extracted text content with `\n` separator.
3. Tail-slices to last 1000 chars (`MAX_CONVERSATION_TEXT`).

**Note**: This helper is also re-imported by CC's `commands/rename/generateSessionName.ts` — UMMAYA keeps that helper inlined locally (Spec 1633 deletion of `generateSessionName.ts` itself), so UMMAYA only needs one copy here.

### `parseNaturalLanguageDateTime`

**Module**: `tui/src/utils/mcp/dateTimeParser.ts` (PORT target)

**Source-of-truth**: `.references/.../utils/mcp/dateTimeParser.ts:23-110` (byte-copy except SWAP comment).

**Signature**:

```ts
export async function parseNaturalLanguageDateTime(
  input: string,
  format: 'date' | 'date-time',
  signal: AbortSignal,
): Promise<DateTimeParseResult>
```

**Behavior contract** — see [contracts/dateTimeParser.contract.ts.md](./contracts/dateTimeParser.contract.ts.md).

### `looksLikeISO8601`

**Module**: `tui/src/utils/mcp/dateTimeParser.ts` (PORT target)

**Signature**:

```ts
export function looksLikeISO8601(input: string): boolean
```

**Behavior contract**: regex `/^\d{4}-\d{2}-\d{2}(T|$)/` against trimmed input.

### `classifyYoloAction`

**Module**: `tui/src/utils/permissions/yoloClassifier.ts` (NEW — Path B stub)

**Signature**:

```ts
export async function classifyYoloAction(
  messages: AssistantMessage[],
  action: string,
  tools: Tool[],
  permissionContext: ToolPermissionContext,
  signal: AbortSignal,
): Promise<YoloClassifierResult>
```

**Behavior contract**: always returns `{unavailable: true, shouldBlock: false}` (UMMAYA auto-mode = no-op per Spec 1633). Promise resolves synchronously without awaiting any I/O.

### `formatActionForClassifier`

**Module**: `tui/src/utils/permissions/yoloClassifier.ts` (NEW — Path B stub)

**Signature**:

```ts
export function formatActionForClassifier(toolName: string, input: unknown): string
```

**Behavior contract**: always returns empty string `''`. CC signature compatibility only — not invoked for any meaningful classification in UMMAYA.

## Migration Map (caller stability invariant)

| Caller | Before (UMMAYA main) | After (Epic G) | Behavior |
|---|---|---|---|
| `tui/src/cli/print.ts:156` | `import { generateSessionTitle } from 'src/utils/sessionTitle.js'` (broken — file missing) | unchanged (resolves naturally) | Unchanged |
| `tui/src/cli/print.ts:3803` | `await generateSessionTitle(description, titleSignal)` (dead — unreachable due to broken import) | resolves to `Promise<string \| null>` | Restored |
| `tui/src/utils/mcp/elicitationValidation.ts:10-19` | inline ISO8601-only stub | `import { parseNaturalLanguageDateTime, looksLikeISO8601 } from './dateTimeParser.js'` | NL parsing restored |
| `tui/src/utils/mcp/elicitationValidation.ts:15` | local `type DateParseResult = ...` | DELETED (use re-exported `DateTimeParseResult`) | type-name change is internal |
| `tui/src/utils/mcp/elicitationValidation.ts:323-339` | passes `schema.format` as `_formatHint` | passes `schema.format` as 2nd arg of CC signature | shape compatible |
| `tui/src/utils/permissions/permissions.ts:102-145` | inline 43-LOC stub | `import { classifyYoloAction, formatActionForClassifier } from './yoloClassifier.js'` | Behavior identical (always no-op) |
| `tui/src/utils/permissions/permissions.ts:670, 710, 777` | callsite uses `inProtectedNamespace()` + classifier results | unchanged | unchanged |

## Constitution Re-check (post-Phase 1)

All 6 principles still PASS. No new types violate Pydantic v2 strict typing (TypeScript-only Epic). No UMMAYA-invented permission classifications introduced (`YoloClassifierResult` is byte-identical CC shape preserved for callsite stability, not a new policy invention).
