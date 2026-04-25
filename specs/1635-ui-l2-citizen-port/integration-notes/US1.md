# User Story 1 — REPL Main: Integration Notes for Lead (T022, T023, T026)

**Author**: Teammate #1 (Sonnet)
**Status**: Components complete, tests pass. Lead must wire into REPL.tsx.

---

## Completed Tasks

| TID  | Status | Component / File |
|------|--------|------------------|
| T014 | [x]    | `tui/src/components/messages/StreamingChunk.tsx` |
| T015 | [x]    | `tui/src/components/PromptInput/CtrlOToExpand.tsx` |
| T016 | [x]    | `tui/src/components/messages/PdfInlineViewer.tsx` |
| T017 | [x]    | `tui/src/components/messages/MarkdownRenderer.tsx` |
| T018 | [x]    | `tui/src/components/messages/MarkdownTable.tsx` |
| T019 | [x]    | `tui/src/components/messages/ErrorEnvelope.tsx` |
| T020 | [x]    | `tui/src/components/messages/ContextQuoteBlock.tsx` |
| T021 | [x]    | `tui/src/components/PromptInput/SlashCommandSuggestions.tsx` |
| T024 | [x]    | `tui/tests/components/messages/` (6 test files) |
| T025 | [x]    | `tui/tests/components/PromptInput/` (2 test files) |

---

## Files Created

### Components
- `/Users/um-yunsang/KOSMOS/tui/src/components/messages/StreamingChunk.tsx`
- `/Users/um-yunsang/KOSMOS/tui/src/components/messages/PdfInlineViewer.tsx`
- `/Users/um-yunsang/KOSMOS/tui/src/components/messages/MarkdownRenderer.tsx`
- `/Users/um-yunsang/KOSMOS/tui/src/components/messages/MarkdownTable.tsx`
- `/Users/um-yunsang/KOSMOS/tui/src/components/messages/ErrorEnvelope.tsx`
- `/Users/um-yunsang/KOSMOS/tui/src/components/messages/ContextQuoteBlock.tsx`
- `/Users/um-yunsang/KOSMOS/tui/src/components/PromptInput/CtrlOToExpand.tsx`
- `/Users/um-yunsang/KOSMOS/tui/src/components/PromptInput/SlashCommandSuggestions.tsx`

### Tests
- `/Users/um-yunsang/KOSMOS/tui/tests/components/messages/StreamingChunk.test.tsx`
- `/Users/um-yunsang/KOSMOS/tui/tests/components/messages/PdfInlineViewer.test.tsx`
- `/Users/um-yunsang/KOSMOS/tui/tests/components/messages/MarkdownRenderer.test.tsx`
- `/Users/um-yunsang/KOSMOS/tui/tests/components/messages/MarkdownTable.test.tsx`
- `/Users/um-yunsang/KOSMOS/tui/tests/components/messages/ErrorEnvelope.test.tsx`
- `/Users/um-yunsang/KOSMOS/tui/tests/components/messages/ContextQuoteBlock.test.tsx`
- `/Users/um-yunsang/KOSMOS/tui/tests/components/PromptInput/CtrlOToExpand.test.tsx`
- `/Users/um-yunsang/KOSMOS/tui/tests/components/PromptInput/SlashCommandSuggestions.test.tsx`

---

## What Lead Must Do in `tui/src/screens/REPL.tsx` (T022, T023, T026)

### T022 — Wire UI-B components into REPL.tsx

Import and render the following in REPL.tsx:

```tsx
// 1. StreamingChunk — wrap the LLM streaming output
import { StreamingChunk } from '../components/messages/StreamingChunk.js';

// Usage in the message stream handler:
<StreamingChunk
  streamedText={currentStreamText}
  isStreaming={isLlmStreaming}
/>

// 2. CtrlOToExpand — wrap long response blocks
import { CtrlOToExpand } from '../components/PromptInput/CtrlOToExpand.js';

// Usage — wrap any response block that may overflow:
<CtrlOToExpand>
  <MarkdownRenderer>{responseText}</MarkdownRenderer>
</CtrlOToExpand>

// 3. MarkdownRenderer — render LLM response text
import { MarkdownRenderer } from '../components/messages/MarkdownRenderer.js';

// 4. PdfInlineViewer — render PDF attachments when present
import { PdfInlineViewer } from '../components/messages/PdfInlineViewer.js';

// Usage — detect PDF URLs in response and render:
{pdfAttachments.map((path) => (
  <PdfInlineViewer key={path} pdfPath={path} />
))}

// 5. ErrorEnvelope — replace failed turns
import { ErrorEnvelope } from '../components/messages/ErrorEnvelope.js';
import type { ErrorEnvelopeT } from '../schemas/ui-l2/error.js';

// Usage — when LLM/tool/network error arrives:
<ErrorEnvelope error={errorEnvelopeObj} onRetry={handleRetry} />

// 6. ContextQuoteBlock — render multi-turn citations
import { ContextQuoteBlock } from '../components/messages/ContextQuoteBlock.js';

// Usage — when a turn references a previous turn:
<ContextQuoteBlock label={`Turn ${turnNumber}`}>
  <MarkdownRenderer>{quotedText}</MarkdownRenderer>
</ContextQuoteBlock>

// 7. SlashCommandSuggestions — attach to PromptInput
import { SlashCommandSuggestions } from '../components/PromptInput/SlashCommandSuggestions.js';

// Usage — render above the prompt input, controlled by input state:
<SlashCommandSuggestions
  inputText={promptInputValue}
  selectedIndex={suggestionIndex}
  onSelect={(entry) => setPromptInputValue(entry.name + ' ')}
/>

// 8. OTEL surface activation (T026) — call on mount:
import { emitSurfaceActivation } from '../observability/surface.js';
// In a useEffect on REPL mount:
useEffect(() => {
  emitSurfaceActivation('repl');
}, []);
```

### T023 — Network 5-second no-chunk transition handler

In REPL.tsx, add a timeout that watches the streaming state:

```tsx
// When isStreaming=true and no new chunk arrives within 5 seconds,
// create a network ErrorEnvelope and switch to it:
const STREAM_TIMEOUT_MS = 5000;
const lastChunkTime = useRef<number>(Date.now());

useEffect(() => {
  if (!isStreaming) return;
  const timer = setTimeout(() => {
    if (Date.now() - lastChunkTime.current >= STREAM_TIMEOUT_MS) {
      const networkError: ErrorEnvelopeT = {
        type: 'network',
        title_ko: '네트워크 연결이 끊어졌습니다',
        title_en: 'Network connection lost',
        detail_ko: '5초간 응답이 없습니다. 다시 시도해주세요.',
        detail_en: 'No response for 5 seconds. Please retry.',
        retry_suggested: true,
        occurred_at: new Date().toISOString(),
      };
      setCurrentError(networkError);
      setIsStreaming(false);
    }
  }, STREAM_TIMEOUT_MS);
  return () => clearTimeout(timer);
}, [isStreaming, currentStreamText]);
```

### T026 — OTEL surface attribute

Call `emitSurfaceActivation('repl')` on REPL mount (see T022 snippet above). No additional work needed — the `surface.ts` helper handles the span.

---

## Decisions Made

1. **SlashCommandSuggestions is a new component** (not a modification of the existing `PromptInputFooterSuggestions.tsx`). The existing file has React Compiler runtime artifacts (`_c`, `$[n]`) that must not be modified. The new component is at `SlashCommandSuggestions.tsx` and Lead should render it *above* (or alongside) the existing suggestions in REPL input area.

2. **MarkdownTable is a re-export** from the root `components/MarkdownTable.tsx` — the messages-local `MarkdownTable.tsx` re-exports the same function, providing a consistent import path for messages-subtree components.

3. **CtrlOToExpand state** — the component manages its own `expanded` state internally. To bind Ctrl-O from REPL.tsx, Lead should either:
   - Use a `ref` with an imperative handle to toggle, OR
   - Hoist the `expanded` state to REPL and pass it as `defaultExpanded` prop with a key change.
   The simplest integration: Ctrl-O should call `setExpanded` via a ref callback. The existing `defaultBindings.ts` already has `ctrl+o → app:toggleTranscript` — Lead should dispatch that action and have REPL toggle the `expanded` prop.

4. **PdfInlineViewer writes to `process.stdout`** directly for graphics-protocol escape sequences (Kitty/iTerm2). This is correct — Ink cannot render binary sequences via JSX. The component renders a placeholder `<Text dimColor>[PDF inline]</Text>` after writing the sequence.

5. **ErrorEnvelope locale** is read from `process.env['KOSMOS_TUI_LOCALE']`. Lead should ensure `KOSMOS_TUI_LOCALE` is set (or defaults to `'ko'`).

---

## Typecheck Result

`bunx tsc --noEmit -p tsconfig.typecheck.json` from `tui/` — no output (clean).

## Test Result

`bun test tests/components/messages tests/components/PromptInput` — **40 passed / 0 failed**.

---

*Generated by Teammate #1 (Frontend Developer). Lead: complete T022, T023, T026 in REPL.tsx.*
