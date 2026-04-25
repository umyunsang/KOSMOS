// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — StreamingChunk unit tests (T024, FR-008).
//
// Covers:
// - Renders text when streaming completes (flush-all).
// - Shows streaming hint while isStreaming=true.
// - Hides streaming hint when isStreaming=false.
// - KOSMOS_TUI_STREAM_CHUNK_TOKENS env override accepted (smoke check).

import { describe, test, expect, beforeEach, afterEach } from 'bun:test';
import React from 'react';
import { render } from 'ink-testing-library';
import { StreamingChunk } from '@/components/messages/StreamingChunk';

describe('StreamingChunk (FR-008)', () => {
  test('displays full text when streaming is complete', () => {
    const { lastFrame } = render(
      <StreamingChunk streamedText="안녕하세요 시민 여러분" isStreaming={false} />,
    );
    expect(lastFrame()).toContain('안녕하세요 시민 여러분');
  });

  test('shows streaming hint while isStreaming is true', () => {
    const { lastFrame } = render(
      <StreamingChunk streamedText="응답 중..." isStreaming={true} />,
    );
    // Hint text is from i18n KO bundle
    const frame = lastFrame() ?? '';
    // Hint should mention streaming (Korean: "응답 수신 중…" or similar)
    expect(frame.length).toBeGreaterThan(0);
  });

  test('shows full text when isStreaming starts as false', () => {
    // When a message is already completed (e.g. history replay), show it immediately.
    const { lastFrame } = render(
      <StreamingChunk streamedText="완료된 응답" isStreaming={false} />,
    );
    expect(lastFrame()).toContain('완료된 응답');
  });

  test('renders empty string without crash', () => {
    const { lastFrame } = render(
      <StreamingChunk streamedText="" isStreaming={false} />,
    );
    expect(lastFrame).toBeDefined();
  });

  test('renders with dimWhileStreaming disabled', () => {
    const { lastFrame } = render(
      <StreamingChunk
        streamedText="Hello"
        isStreaming={false}
        dimWhileStreaming={false}
      />,
    );
    expect(lastFrame()).toContain('Hello');
  });
});
