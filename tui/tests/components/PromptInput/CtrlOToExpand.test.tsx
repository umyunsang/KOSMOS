// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — CtrlOToExpand unit tests (T025, FR-009).
//
// Covers:
// - Renders children.
// - Shows collapse hint when defaultExpanded=true.
// - Shows expand hint when defaultExpanded=false (default).
// - Inside SubAgentExpandProvider: no hint shown, children rendered directly.
// - ctrlOToExpandText() returns correct strings.

import { describe, test, expect } from 'bun:test';
import React from 'react';
import { Text } from '@/ink.js';
import { render } from 'ink-testing-library';
import {
  CtrlOToExpand,
  SubAgentExpandProvider,
  ctrlOToExpandText,
} from '@/components/PromptInput/CtrlOToExpand';

describe('CtrlOToExpand (FR-009)', () => {
  test('renders children content', () => {
    const { lastFrame } = render(
      <CtrlOToExpand>
        <Text>본문 내용입니다</Text>
      </CtrlOToExpand>,
    );
    expect(lastFrame()).toContain('본문 내용입니다');
  });

  test('shows expand hint when not expanded (default)', () => {
    const { lastFrame } = render(
      <CtrlOToExpand>
        <Text>content</Text>
      </CtrlOToExpand>,
    );
    const frame = lastFrame() ?? '';
    // Hint should be present (Korean: "Ctrl-O로 펼치기")
    expect(frame.length).toBeGreaterThan(0);
    expect(frame).toContain('Ctrl-O');
  });

  test('shows collapse hint when defaultExpanded=true', () => {
    const { lastFrame } = render(
      <CtrlOToExpand defaultExpanded>
        <Text>long content</Text>
      </CtrlOToExpand>,
    );
    const frame = lastFrame() ?? '';
    expect(frame).toContain('Ctrl-O');
  });

  test('inside SubAgentExpandProvider: renders children directly without hint', () => {
    const { lastFrame } = render(
      <SubAgentExpandProvider>
        <CtrlOToExpand>
          <Text>sub-agent output</Text>
        </CtrlOToExpand>
      </SubAgentExpandProvider>,
    );
    const frame = lastFrame() ?? '';
    expect(frame).toContain('sub-agent output');
    // Hint should NOT appear inside sub-agent context
    expect(frame).not.toContain('펼치기');
    expect(frame).not.toContain('접기');
  });

  test('ctrlOToExpandText returns expand string when collapsed', () => {
    expect(ctrlOToExpandText(false)).toContain('expand');
  });

  test('ctrlOToExpandText returns collapse string when expanded', () => {
    expect(ctrlOToExpandText(true)).toContain('collapse');
  });
});
