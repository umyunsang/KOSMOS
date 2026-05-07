// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — ContextQuoteBlock unit tests (T024, FR-013).
//
// Covers:
// - Renders ⎿ prefix glyph (brand-frozen FR-036).
// - Renders children.
// - Renders optional label.
// - No crash with empty children.

import { describe, test, expect } from 'bun:test';
import React from 'react';
import { Text } from '@/ink.js';
import { render } from 'ink-testing-library';
import { ContextQuoteBlock, QUOTE_GLYPH } from '@/components/messages/ContextQuoteBlock';

describe('ContextQuoteBlock (FR-013)', () => {
  test('renders the brand-frozen ⎿ glyph', () => {
    // Ink requires string children to be wrapped in <Text>
    const { lastFrame } = render(
      <ContextQuoteBlock><Text>인용 내용</Text></ContextQuoteBlock>,
    );
    expect(lastFrame()).toContain(QUOTE_GLYPH);
    // Glyph must be exactly ⎿ per FR-036
    expect(QUOTE_GLYPH).toBe('⎿');
  });

  test('renders children', () => {
    const { lastFrame } = render(
      <ContextQuoteBlock><Text>이전 대화 내용입니다.</Text></ContextQuoteBlock>,
    );
    expect(lastFrame()).toContain('이전 대화 내용입니다.');
  });

  test('renders optional label when provided', () => {
    const { lastFrame } = render(
      <ContextQuoteBlock label="Turn 2"><Text>인용</Text></ContextQuoteBlock>,
    );
    expect(lastFrame()).toContain('Turn 2');
  });

  test('renders without label when label is omitted', () => {
    const { lastFrame } = render(
      <ContextQuoteBlock><Text>no label here</Text></ContextQuoteBlock>,
    );
    expect(lastFrame()).toContain('no label here');
  });
});
