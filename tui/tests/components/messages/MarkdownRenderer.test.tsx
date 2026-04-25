// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — MarkdownRenderer unit tests (T024, FR-011).
//
// Covers:
// - Plain text renders without markdown noise.
// - Heading is present in output.
// - No crash with empty string.
// - dimColor prop does not crash.

import { describe, test, expect } from 'bun:test';
import React from 'react';
import { render } from 'ink-testing-library';
import { MarkdownRenderer } from '@/components/messages/MarkdownRenderer';

describe('MarkdownRenderer (FR-011)', () => {
  test('renders plain text', () => {
    const { lastFrame } = render(<MarkdownRenderer>안녕하세요</MarkdownRenderer>);
    expect(lastFrame()).toContain('안녕하세요');
  });

  test('renders heading content', () => {
    const { lastFrame } = render(
      <MarkdownRenderer># 제목</MarkdownRenderer>,
    );
    const frame = lastFrame() ?? '';
    expect(frame).toContain('제목');
  });

  test('does not crash with empty string', () => {
    const { lastFrame } = render(<MarkdownRenderer>{''}</MarkdownRenderer>);
    expect(lastFrame).toBeDefined();
  });

  test('renders with dimColor prop', () => {
    const { lastFrame } = render(
      <MarkdownRenderer dimColor>텍스트</MarkdownRenderer>,
    );
    expect(lastFrame()).toContain('텍스트');
  });

  test('renders list items', () => {
    const { lastFrame } = render(
      <MarkdownRenderer>{'- 항목 1\n- 항목 2'}</MarkdownRenderer>,
    );
    const frame = lastFrame() ?? '';
    expect(frame).toContain('항목 1');
    expect(frame).toContain('항목 2');
  });
});
