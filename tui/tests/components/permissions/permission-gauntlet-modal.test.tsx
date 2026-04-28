// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — US2 T037 (partial)
// Spec 1979 — Y/A/N direct-keystroke pattern replaced with CC arrow+Enter.
// bun:test units for PermissionGauntletModal (FR-015/017/023/024).

import { describe, test, expect, mock } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { PermissionGauntletModal } from '../../../src/components/permissions/PermissionGauntletModal'
import type { PermissionDecisionT } from '../../../src/schemas/ui-l2/permission'

// ---------------------------------------------------------------------------
// Helpers — VT100 escape sequences as emitted by Ink's stdin.
// ---------------------------------------------------------------------------

function tick(ms = 20): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

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

const ENTER = '\r'
const DOWN = '[B'
const ESC = ''
const CTRL_C = '\x03'

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('PermissionGauntletModal — FR-015/016/017/023 (CC arrow+Enter pattern)', () => {
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

  test('Enter on first option → allow_once (FR-017)', async () => {
    const decisions: PermissionDecisionT[] = []
    const onDecide = mock((d: PermissionDecisionT) => decisions.push(d))
    const { stdin } = render(wrap(1, onDecide))
    await tick()
    stdin.write(ENTER)
    await tick()
    expect(decisions).toEqual(['allow_once'])
  })

  test('Down → Enter → allow_session (FR-017)', async () => {
    const decisions: PermissionDecisionT[] = []
    const onDecide = mock((d: PermissionDecisionT) => decisions.push(d))
    const { stdin } = render(wrap(2, onDecide))
    await tick()
    stdin.write(DOWN)
    await tick()
    stdin.write(ENTER)
    await tick()
    expect(decisions).toEqual(['allow_session'])
  })

  test('Down → Down → Enter → deny (FR-017)', async () => {
    const decisions: PermissionDecisionT[] = []
    const onDecide = mock((d: PermissionDecisionT) => decisions.push(d))
    const { stdin } = render(wrap(2, onDecide))
    await tick()
    stdin.write(DOWN)
    await tick()
    stdin.write(DOWN)
    await tick()
    stdin.write(ENTER)
    await tick()
    expect(decisions).toEqual(['deny'])
  })

  test('Esc → deny (FR-017)', async () => {
    const decisions: PermissionDecisionT[] = []
    const onDecide = mock((d: PermissionDecisionT) => decisions.push(d))
    const { stdin } = render(wrap(1, onDecide))
    await tick()
    stdin.write(ESC)
    await tick()
    expect(decisions).toEqual(['deny'])
  })

  test('Layer 3 shows reinforcement notice (FR-017)', () => {
    const onDecide = mock(() => {})
    const { lastFrame } = render(wrap(3, onDecide))
    const frame = lastFrame() ?? ''
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
    expect(frame.includes('외부 시스템') || frame.includes('external systems')).toBe(
      false,
    )
  })

  test('onDecide fires at most once (idempotent on double-press)', async () => {
    const decisions: PermissionDecisionT[] = []
    const onDecide = mock((d: PermissionDecisionT) => decisions.push(d))
    const { stdin } = render(wrap(1, onDecide))
    await tick()
    stdin.write(ENTER) // selects allow_once
    await tick()
    stdin.write(ENTER) // second press — decidedRef guards
    await tick()
    expect(decisions).toHaveLength(1)
    expect(decisions[0]).toBe('allow_once')
  })
})

describe('PermissionGauntletModal — Ctrl-C auto_denied_at_cancel (FR-023)', () => {
  test('Ctrl-C → auto_denied_at_cancel', async () => {
    const decisions: PermissionDecisionT[] = []
    const onDecide = mock((d: PermissionDecisionT) => decisions.push(d))
    const { stdin } = render(wrap(1, onDecide))
    await tick()
    stdin.write(CTRL_C)
    await tick()
    expect(decisions).toEqual(['auto_denied_at_cancel'])
  })
})
