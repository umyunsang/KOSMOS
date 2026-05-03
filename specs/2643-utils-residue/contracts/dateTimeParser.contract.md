# Contract — `tui/src/utils/mcp/dateTimeParser.ts`

**Status**: NEW (byte-copy from CC `.references/.../utils/mcp/dateTimeParser.ts`)
**Source-of-truth**: `.references/claude-code-sourcemap/restored-src/src/utils/mcp/dateTimeParser.ts` (CC 2.1.88, 121 LOC)

## Exported types

```ts
export type DateTimeParseResult =
  | { success: true; value: string }
  | { success: false; error: string }
```

## Exported functions

### `parseNaturalLanguageDateTime(input: string, format: 'date' | 'date-time', signal: AbortSignal): Promise<DateTimeParseResult>`

**Inputs**:
- `input`: raw user-typed string (Korean natural language permitted).
- `format`: discriminator for output shape — `date` ⇒ `YYYY-MM-DD`, `date-time` ⇒ `YYYY-MM-DDTHH:MM:SS<tz>`.
- `signal`: AbortSignal forwarded to `queryHaiku`.

**Behavior** (byte-copy CC):
1. Compute `now = new Date()`, ISO timestamp, timezone string `±HH:MM`, day-of-week (English, via `toLocaleDateString('en-US', { weekday: 'long' })`).
2. Build system prompt (8-line English, byte-identical with CC):
   - "You are a date/time parser that converts natural language into ISO 8601 format."
   - "You MUST respond with ONLY the ISO 8601 formatted string, with no explanation or additional text."
   - "If the input is ambiguous, prefer future dates over past dates."
   - "For times without dates, use today's date."
   - "For dates without times, do not include a time component."
   - "If the input is incomplete or you cannot confidently parse it into a valid date, respond with exactly \"INVALID\" (nothing else)."
   - "Examples of INVALID input: partial dates like \"2025-01-\", lone numbers like \"13\", gibberish."
   - "Examples of valid natural language: \"tomorrow\", \"next Monday\", \"jan 1st 2025\", \"in 2 hours\", \"yesterday\"."
3. Build user prompt with rich context (current datetime, timezone, day of week, user input, target format).
4. Call `queryHaiku` with `querySource: 'mcp_datetime_parse'`, `enablePromptCaching: false` (per CC).
5. Extract text from response, trim.
6. If parsedText empty or `'INVALID'` → return `{ success: false, error: 'Unable to parse date/time from input' }`.
7. If parsedText doesn't match `/^\d{4}/` → return same failure shape.
8. Otherwise → return `{ success: true, value: parsedText }`.
9. On thrown error: `logError(error)`, return `{ success: false, error: 'Unable to parse date/time. Please enter in ISO 8601 format manually.' }`.

### `looksLikeISO8601(input: string): boolean`

Returns whether trimmed `input` matches `/^\d{4}-\d{2}-\d{2}(T|$)/`.

## Swap-1 deviation log

| Line (CC) | CC | KOSMOS | Reason |
|---|---|---|---|
| Line 0 (new) | (no header) | `// SWAP/llm-swap(2643): queryHaiku target = K-EXAONE via FriendliAI (Spec 2521 byte-copy bridge).` | swap-1 attribution per AGENTS.md SWAP convention |

All other lines byte-identical with CC, including the English system prompt (AGENTS.md hard rule "All source text in English").

## Test plan (Layer 1b — `tui/src/utils/mcp/__tests__/dateTimeParser.test.ts`)

```ts
import { test, expect, mock } from 'bun:test'

// Mock queryHaiku to return deterministic responses keyed by user prompt content
mock.module('../../services/api/claude.js', () => ({
  queryHaiku: async ({ userPrompt }: { userPrompt: string }) => {
    if (userPrompt.includes('내일 오후 3시')) {
      return { message: { content: [{ type: 'text', text: '2026-05-04T15:00:00+09:00' }] } }
    }
    if (userPrompt.includes('다음주 월요일 오전 9시')) {
      return { message: { content: [{ type: 'text', text: '2026-05-11T09:00:00+09:00' }] } }
    }
    if (userPrompt.includes('다음주 월요일')) {
      return { message: { content: [{ type: 'text', text: '2026-05-11' }] } }
    }
    if (userPrompt.includes('asdf')) {
      return { message: { content: [{ type: 'text', text: 'INVALID' }] } }
    }
    return { message: { content: [{ type: 'text', text: 'INVALID' }] } }
  },
}))

const { parseNaturalLanguageDateTime, looksLikeISO8601 } =
  await import('../dateTimeParser.js')

test('parseNaturalLanguageDateTime: 내일 오후 3시 → ISO date-time', async () => {
  const ctl = new AbortController()
  const result = await parseNaturalLanguageDateTime('내일 오후 3시', 'date-time', ctl.signal)
  expect(result).toEqual({ success: true, value: '2026-05-04T15:00:00+09:00' })
})

test('parseNaturalLanguageDateTime: 다음주 월요일 오전 9시 → ISO date-time', async () => {
  const ctl = new AbortController()
  const result = await parseNaturalLanguageDateTime('다음주 월요일 오전 9시', 'date-time', ctl.signal)
  expect(result).toEqual({ success: true, value: '2026-05-11T09:00:00+09:00' })
})

test('parseNaturalLanguageDateTime: 다음주 월요일 → ISO date', async () => {
  const ctl = new AbortController()
  const result = await parseNaturalLanguageDateTime('다음주 월요일', 'date', ctl.signal)
  expect(result).toEqual({ success: true, value: '2026-05-11' })
})

test('parseNaturalLanguageDateTime: asdf → INVALID failure', async () => {
  const ctl = new AbortController()
  const result = await parseNaturalLanguageDateTime('asdf', 'date', ctl.signal)
  expect(result).toEqual({ success: false, error: 'Unable to parse date/time from input' })
})

test('looksLikeISO8601: positive + negative cases', () => {
  expect(looksLikeISO8601('2026-05-03')).toBe(true)
  expect(looksLikeISO8601('2026-05-03T14:30:00Z')).toBe(true)
  expect(looksLikeISO8601('내일')).toBe(false)
  expect(looksLikeISO8601('asdf')).toBe(false)
})
```

## `elicitationValidation.ts` migration

**Before** (lines 10-19):
```ts
// KOSMOS Spec 1633 / Epic #2293 — utils/mcp/dateTimeParser deleted (Anthropic
// queryHaiku natural-language parser); inline ISO8601-only stubs preserve the
// {success, value, error} contract that validateElicitationInputAsync expects.
const ISO8601_REGEX = /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?$/
const looksLikeISO8601 = (value: string): boolean => ISO8601_REGEX.test(value)
type DateParseResult = { success: true; value: string } | { success: false; error: string }
const parseNaturalLanguageDateTime = async (value: string, _formatHint?: string): Promise<DateParseResult> =>
  looksLikeISO8601(value)
    ? { success: true, value }
    : { success: false, error: 'KOSMOS: natural-language datetime parsing not available; please use ISO 8601 format (e.g. 2026-04-29T12:00:00Z)' }
```

**After**:
```ts
import { looksLikeISO8601, parseNaturalLanguageDateTime } from './dateTimeParser.js'
```

**Callsite** (line 323-328) `parseNaturalLanguageDateTime(stringValue, schema.format, signal)` — already CC-shape compatible (3-arg form). KOSMOS-side currently uses `_formatHint` param name (CC: `format`), so the callsite signature works without further edit.
