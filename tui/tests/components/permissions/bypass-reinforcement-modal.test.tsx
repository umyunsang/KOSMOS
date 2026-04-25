// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — US2 T037 (partial)
// bun:test units for BypassReinforcementModal (FR-022).
//
// Covers:
//   - Modal renders the reinforcement warning text
//   - Y key → onConfirm called
//   - N key → onCancel called
//   - Escape → onCancel called

import { describe, test, expect, mock } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { BypassReinforcementModal } from '../../../src/components/permissions/BypassReinforcementModal'

describe('BypassReinforcementModal — FR-022', () => {
  test('renders bypass warning text', () => {
    const { lastFrame } = render(
      <BypassReinforcementModal onConfirm={() => {}} onCancel={() => {}} />,
    )
    const frame = lastFrame() ?? ''
    // Should contain either Korean or English bypass warning
    expect(
      frame.includes('bypass') ||
        frame.includes('우회') ||
        frame.includes('bypassPermissions') ||
        frame.includes('모든 Layer') ||
        frame.includes('모든 권한'),
    ).toBe(true)
  })

  test('Y key calls onConfirm', () => {
    const onConfirm = mock(() => {})
    const onCancel = mock(() => {})
    const { stdin } = render(
      <BypassReinforcementModal onConfirm={onConfirm} onCancel={onCancel} />,
    )
    stdin.write('y')
    expect(onConfirm).toHaveBeenCalledTimes(1)
    expect(onCancel).not.toHaveBeenCalled()
  })

  test('N key calls onCancel', () => {
    const onConfirm = mock(() => {})
    const onCancel = mock(() => {})
    const { stdin } = render(
      <BypassReinforcementModal onConfirm={onConfirm} onCancel={onCancel} />,
    )
    stdin.write('n')
    expect(onCancel).toHaveBeenCalledTimes(1)
    expect(onConfirm).not.toHaveBeenCalled()
  })

  test('Escape key calls onCancel', () => {
    const onConfirm = mock(() => {})
    const onCancel = mock(() => {})
    const { stdin } = render(
      <BypassReinforcementModal onConfirm={onConfirm} onCancel={onCancel} />,
    )
    // Escape key in ink-testing-library
    stdin.write('\x1b')
    expect(onCancel).toHaveBeenCalledTimes(1)
    expect(onConfirm).not.toHaveBeenCalled()
  })

  test('Uppercase Y also calls onConfirm', () => {
    const onConfirm = mock(() => {})
    const onCancel = mock(() => {})
    const { stdin } = render(
      <BypassReinforcementModal onConfirm={onConfirm} onCancel={onCancel} />,
    )
    stdin.write('Y')
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })
})
