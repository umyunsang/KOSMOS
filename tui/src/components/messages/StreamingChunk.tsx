// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — StreamingChunk component (FR-008, T014).
//
// Batches incoming LLM token stream into ~20-token render frames to prevent
// per-token re-render thrash.  Chunk size is configurable via
// KOSMOS_TUI_STREAM_CHUNK_TOKENS (default 20, per research.md D-3).
//
// Source: cc:components/Messages.tsx, cc:components/Message.tsx,
//         cc:components/VirtualMessageList.tsx (streaming primitive pattern).
// KOSMOS adaptation: token-budget batching replaces CC's streaming accumulator;
// env-var override preserves "approximately" semantics (FR-008).

import React, { useEffect, useRef, useState } from 'react';
import { Box, Text } from '../../ink.js';
import { useUiL2I18n } from '../../i18n/uiL2.js';

// ---------------------------------------------------------------------------
// Token-count heuristic — word boundary approximation.
// A "token" is roughly a whitespace-delimited word (good enough for chunking
// purposes; the exact tokenizer is the LLM's concern).
// ---------------------------------------------------------------------------
function estimateTokens(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

const DEFAULT_CHUNK_TOKENS = 20;

function getChunkTokens(): number {
  const raw = process.env['KOSMOS_TUI_STREAM_CHUNK_TOKENS'];
  if (raw) {
    const n = parseInt(raw, 10);
    if (!isNaN(n) && n > 0) return n;
  }
  return DEFAULT_CHUNK_TOKENS;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
export type StreamingChunkProps = {
  /** Full accumulated text from the stream so far */
  streamedText: string;
  /** True while the LLM stream is still open */
  isStreaming: boolean;
  /** Dim the text while streaming (matches CC behaviour) */
  dimWhileStreaming?: boolean;
};

/**
 * StreamingChunk batches token stream into ~20-token render frames.
 *
 * Contract:
 * - When `isStreaming` is true, new text is buffered until ~20 tokens
 *   accumulate, then flushed to rendered output in one React state update.
 * - When `isStreaming` becomes false, the full `streamedText` is shown
 *   immediately (flush remaining buffer).
 * - `KOSMOS_TUI_STREAM_CHUNK_TOKENS` overrides the default chunk size.
 */
export function StreamingChunk({
  streamedText,
  isStreaming,
  dimWhileStreaming = true,
}: StreamingChunkProps): React.ReactNode {
  const i18n = useUiL2I18n();
  const chunkTokens = useRef(getChunkTokens()).current;

  // `displayedText` is what has been committed to the rendered output.
  // Initialize to the full text if not streaming (e.g. history replay).
  const [displayedText, setDisplayedText] = useState(() =>
    isStreaming ? '' : streamedText,
  );

  // Pending token buffer — text received since the last flush.
  const pendingRef = useRef('');

  useEffect(() => {
    if (!isStreaming) {
      // Stream ended: flush everything immediately.
      setDisplayedText(streamedText);
      pendingRef.current = '';
      return;
    }

    // Calculate the delta since last displayed text.
    const delta = streamedText.slice(displayedText.length + pendingRef.current.length);
    pendingRef.current += delta;

    const pendingTokens = estimateTokens(pendingRef.current);
    if (pendingTokens >= chunkTokens) {
      // Commit the buffer to displayed output.
      const flushed = displayedText + pendingRef.current;
      pendingRef.current = '';
      setDisplayedText(flushed);
    }
    // else: keep accumulating until the next chunk boundary.
  });

  const showHint = isStreaming;

  return (
    <Box flexDirection="column">
      <Text dimColor={dimWhileStreaming && isStreaming}>{displayedText}</Text>
      {showHint && (
        <Text dimColor>
          {i18n.streamingHint}
        </Text>
      )}
    </Box>
  );
}
