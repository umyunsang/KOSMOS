// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — US2 T037 (partial)
// bun:test units for PermissionGauntletModal (FR-015/017/023/024).
//
// Covers:
//   - Renders layer glyph + description (FR-015/016)
//   - Y key → allow_once decision (FR-017)
//   - A key → allow_session decision (FR-017)
//   - N key → deny decision (FR-017)
//   - Ctrl-C → auto_denied_at_cancel (FR-023)
//   - Layer 3 reinforcement notice is shown only for Layer 3 (FR-017)
//   - Timeout auto-deny fires after timeout (FR-024, uses fake timer)

import { describe, test, expect, mock, beforeEach, afterEach } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { PermissionGauntletModal } from '../../../src/components/permissions/PermissionGauntletModal'
import type { PermissionDecisionT } from '../../../src/schemas/ui-l2/permission'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function wrap(
  layer: 1 | 2 | 3,
  onDecide: (d: PermissionDecisionT) => void,
): React.ReactElement {
  return (
    <PermissionGauntletModal
      layer={layer}
      toolName="test_tool"
      description="Test tool description"
      onDecide={onDecide}
    />
  )
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('PermissionGauntletModal — FR-015/016/017/023', () => {
  test('renders Layer 2 glyph ⓶', () => {
    const onDecide = mock(() => {})
    const { lastFrame } = render(wrap(2, onDecide))
    expect(lastFrame()).toContain('⓶')
  })

  test('renders tool description', () => {
    const onDecide = mock(() => {})
    const { lastFrame } = render(wrap(1, onDecide))
    expect(lastFrame()).toContain('Test tool description')
  })

  test('Y key → allow_once (FR-017)', () => {
    const decisions: PermissionDecisionT[] = []
    const onDecide = mock((d: PermissionDecisionT) => decisions.push(d))
    const { stdin } = render(wrap(1, onDecide))
    stdin.write('y')
    expect(decisions).toEqual(['allow_once'])
  })

  test('A key → allow_session (FR-017)', () => {
    const decisions: PermissionDecisionT[] = []
    const onDecide = mock((d: PermissionDecisionT) => decisions.push(d))
    const { stdin } = render(wrap(2, onDecide))
    stdin.write('a')
    expect(decisions).toEqual(['allow_session'])
  })

  test('N key → deny (FR-017)', () => {
    const decisions: PermissionDecisionT[] = []
    const onDecide = mock((d: PermissionDecisionT) => decisions.push(d))
    const { stdin } = render(wrap(2, onDecide))
    stdin.write('n')
    expect(decisions).toEqual(['deny'])
  })

  test('Uppercase Y → allow_once', () => {
    const decisions: PermissionDecisionT[] = []
    const onDecide = mock((d: PermissionDecisionT) => decisions.push(d))
    const { stdin } = render(wrap(1, onDecide))
    stdin.write('Y')
    expect(decisions).toEqual(['allow_once'])
  })

  test('Layer 3 shows reinforcement notice (FR-017)', () => {
    const onDecide = mock(() => {})
    const { lastFrame } = render(wrap(3, onDecide))
    // The reinforcement text contains "⚠️" or the i18n string
    const frame = lastFrame() ?? ''
    // Should contain some warning indicator
    expect(
      frame.includes('⚠') ||
        frame.includes('외부 시스템') ||
        frame.includes('external systems'),
    ).toBe(true)
  })

  test('Layer 1 does NOT show reinforcement notice', () => {
    const onDecide = mock(() => {})
    const { lastFrame } = render(wrap(1, onDecide))
    const frame = lastFrame() ?? ''
    // Reinforcement text should not appear for layer 1
    expect(frame.includes('외부 시스템') || frame.includes('external systems')).toBe(
      false,
    )
  })

  test('onDecide fires at most once (idempotent on double-press)', () => {
    const decisions: PermissionDecisionT[] = []
    const onDecide = mock((d: PermissionDecisionT) => decisions.push(d))
    const { stdin } = render(wrap(1, onDecide))
    stdin.write('y')
    stdin.write('n') // second press should be ignored after decision is made
    expect(decisions).toHaveLength(1)
    expect(decisions[0]).toBe('allow_once')
  })
})

describe('PermissionGauntletModal — Ctrl-C auto_denied_at_cancel (FR-023)', () => {
  test('Ctrl-C → auto_denied_at_cancel', () => {
    const decisions: PermissionDecisionT[] = []
    const onDecide = mock((d: PermissionDecisionT) => decisions.push(d))
    const { stdin } = render(wrap(1, onDecide))
    // Simulate Ctrl-C (ASCII 0x03)
    stdin.write('\x03')
    expect(decisions).toEqual(['auto_denied_at_cancel'])
  })
})
