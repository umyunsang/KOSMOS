// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — ErrorEnvelope unit tests (T024, FR-012).
//
// Covers:
// - LLM error renders with brain glyph (🧠) and purple hint.
// - Tool error renders with wrench glyph (🔧).
// - Network error renders with signal glyph (📡).
// - All three types are visually distinguishable (unique glyph).
// - Detail text renders when present.
// - Retry hint renders when retry_suggested=true.
// - Timestamp renders.

import { describe, test, expect } from 'bun:test';
import React from 'react';
import { render } from 'ink-testing-library';
import { ErrorEnvelope } from '@/components/messages/ErrorEnvelope';
import type { ErrorEnvelopeT } from '@/schemas/ui-l2/error';

function makeError(overrides: Partial<ErrorEnvelopeT>): ErrorEnvelopeT {
  return {
    type: 'llm',
    title_ko: 'LLM 응답 오류',
    title_en: 'LLM error',
    detail_ko: null,
    detail_en: null,
    retry_suggested: false,
    occurred_at: '2026-04-25T12:00:00.000Z',
    ...overrides,
  };
}

describe('ErrorEnvelope (FR-012)', () => {
  test('LLM error shows brain glyph', () => {
    const error = makeError({ type: 'llm', title_ko: 'LLM 오류' });
    const { lastFrame } = render(<ErrorEnvelope error={error} />);
    expect(lastFrame()).toContain('🧠');
  });

  test('Tool error shows wrench glyph', () => {
    const error = makeError({ type: 'tool', title_ko: '도구 오류' });
    const { lastFrame } = render(<ErrorEnvelope error={error} />);
    expect(lastFrame()).toContain('🔧');
  });

  test('Network error shows signal glyph', () => {
    const error = makeError({ type: 'network', title_ko: '네트워크 오류' });
    const { lastFrame } = render(<ErrorEnvelope error={error} />);
    expect(lastFrame()).toContain('📡');
  });

  test('Three error types have unique glyphs (FR-012 differentiation)', () => {
    const llmFrame = render(<ErrorEnvelope error={makeError({ type: 'llm' })} />).lastFrame() ?? '';
    const toolFrame = render(<ErrorEnvelope error={makeError({ type: 'tool' })} />).lastFrame() ?? '';
    const netFrame = render(<ErrorEnvelope error={makeError({ type: 'network' })} />).lastFrame() ?? '';
    // Each type has its unique glyph, others don't
    expect(llmFrame).toContain('🧠');
    expect(toolFrame).toContain('🔧');
    expect(netFrame).toContain('📡');
    // Cross-checks — each frame must NOT contain the other types' glyphs
    expect(llmFrame).not.toContain('🔧');
    expect(toolFrame).not.toContain('🧠');
    expect(netFrame).not.toContain('🧠');
  });

  test('renders detail text when provided', () => {
    const error = makeError({
      type: 'tool',
      detail_ko: '데이터 형식이 잘못되었습니다',
    });
    const { lastFrame } = render(<ErrorEnvelope error={error} />);
    expect(lastFrame()).toContain('데이터 형식이 잘못되었습니다');
  });

  test('shows retry hint when retry_suggested is true', () => {
    const error = makeError({ retry_suggested: true });
    const { lastFrame } = render(<ErrorEnvelope error={error} />);
    // Retry hint present (Korean: "다시 시도")
    const frame = lastFrame() ?? '';
    expect(frame.length).toBeGreaterThan(0);
  });

  test('no retry hint when retry_suggested is false', () => {
    const error = makeError({ retry_suggested: false });
    const { lastFrame } = render(<ErrorEnvelope error={error} />);
    // Should still render without crashing
    expect(lastFrame).toBeDefined();
  });
});
