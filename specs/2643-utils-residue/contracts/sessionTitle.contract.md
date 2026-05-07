# Contract — `tui/src/utils/sessionTitle.ts`

**Status**: NEW (byte-copy from CC `.references/.../utils/sessionTitle.ts`)
**Source-of-truth**: `.references/claude-code-sourcemap/restored-src/src/utils/sessionTitle.ts` (CC 2.1.88, 129 LOC)

## Module-level constants

```ts
const MAX_CONVERSATION_TEXT = 1000

const SESSION_TITLE_PROMPT = `Generate a concise, sentence-case title (3-7 words) that captures the main topic or goal of this coding session. The title should be clear enough that the user recognizes the session in a list. Use sentence case: capitalize only the first word and proper nouns.

Return JSON with a single "title" field.

Good examples:
{"title": "Fix login button on mobile"}
{"title": "Add OAuth authentication"}
{"title": "Debug failing CI tests"}
{"title": "Refactor API client error handling"}

Bad (too vague): {"title": "Code changes"}
Bad (too long): {"title": "Investigate and fix the issue where the login button does not respond on mobile devices"}
Bad (wrong case): {"title": "Fix Login Button On Mobile"}`

const titleSchema = lazySchema(() => z.object({ title: z.string() }))
```

**Note**: All three constants are byte-identical with CC. The "coding session" wording remains in the prompt because (a) AGENTS.md hard rule "All source text in English" applies, (b) K-EXAONE responds equally well to either generic or coding-specific phrasing for short title tasks, (c) byte-copy fidelity is the higher policy per CORE THESIS.

## Exported functions

### `extractConversationText(messages: Message[]): string`

Filters `messages` to user/assistant typed entries with no `isMeta` flag and no non-human origin; concatenates text content with `\n`; tail-slices to last `MAX_CONVERSATION_TEXT` chars.

### `generateSessionTitle(description: string, signal: AbortSignal): Promise<string | null>`

**Inputs**:
- `description`: user-supplied free-text (typically first user message; may be Korean).
- `signal`: AbortSignal that, when aborted, triggers `queryHaiku` to throw `APIUserAbortError` → caught → returns `null`.

**Behavior** (byte-copy CC):
1. Trim `description`. If empty → return `null` immediately.
2. Call `queryHaiku` with:
   - `systemPrompt: asSystemPrompt([SESSION_TITLE_PROMPT])`
   - `userPrompt: trimmed`
   - `outputFormat: { type: 'json_schema', schema: { type: 'object', properties: { title: { type: 'string' } }, required: ['title'], additionalProperties: false } }`
   - `signal`
   - `options: { querySource: 'generate_session_title', agents: [], isNonInteractiveSession: getIsNonInteractiveSession(), hasAppendSystemPrompt: false, mcpTools: [] }`
3. Extract text from `result.message.content` via `extractTextContent`.
4. Parse text with `safeParseJSON` then validate with `titleSchema().safeParse(...)`.
5. If valid: return `parsed.data.title.trim() || null`.
6. Always emit `logEvent('tengu_session_title_generated', { success: title !== null })`.
7. On any thrown error: `logForDebugging(...)`, emit `tengu_session_title_generated success=false`, return `null`.

**Returns**: `Promise<string | null>` — sentence-case title or null on any failure.

## Swap-1 deviation log

| Line (CC) | CC | KOSAX | Reason |
|---|---|---|---|
| Line 0 (new) | (no header) | `// SWAP/llm-swap(2643): queryHaiku target = K-EXAONE via FriendliAI (Spec 2521 byte-copy bridge).` | swap-1 attribution comment per AGENTS.md SWAP convention |

All other lines byte-identical with CC.

## Test plan (Layer 1b — `tui/src/utils/__tests__/sessionTitle.test.ts`)

```ts
import { test, expect, mock } from 'bun:test'

// Mock queryHaiku to return a deterministic title
mock.module('src/services/api/claude.js', () => ({
  queryHaiku: async ({ userPrompt }: { userPrompt: string }) => ({
    message: { content: [{ type: 'text', text: JSON.stringify({ title: 'Test session title' }) }] },
  }),
}))

const { generateSessionTitle } = await import('src/utils/sessionTitle.js')

test('generateSessionTitle returns null for empty description', async () => {
  const ctl = new AbortController()
  expect(await generateSessionTitle('', ctl.signal)).toBeNull()
  expect(await generateSessionTitle('   ', ctl.signal)).toBeNull()
})

test('generateSessionTitle returns title from valid mock response', async () => {
  const ctl = new AbortController()
  const title = await generateSessionTitle('한강 다리 사고', ctl.signal)
  expect(title).toBe('Test session title')
})

// Edge: malformed JSON, abort signal, etc. — covered by integration mocking variants
```

## CC import preservation invariant

The PORTed file's import block MUST match CC line-for-line:

```ts
import { z } from 'zod/v4'
import { getIsNonInteractiveSession } from '../bootstrap/state.js'
import { logEvent } from '../services/analytics/index.js'
import { queryHaiku } from '../services/api/claude.js'
import type { Message } from '../types/message.js'
import { logForDebugging } from './debug.js'
import { safeParseJSON } from './json.js'
import { lazySchema } from './lazySchema.js'
import { extractTextContent } from './messages.js'
import { asSystemPrompt } from './systemPromptType.js'
```

All 10 imports MUST resolve in KOSAX without modification (verified Phase 0 R-5).
