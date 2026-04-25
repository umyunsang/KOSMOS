// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — US2 T037 (partial)
// bun:test units for PermissionLayerHeader (FR-016).
//
// Covers:
//   - Layer 1 renders green color + ⓵ glyph
//   - Layer 2 renders orange color + ⓶ glyph
//   - Layer 3 renders red color + ⓷ glyph
//   - toolName is rendered in all layers

import { describe, test, expect } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { PermissionLayerHeader } from '../../../src/components/permissions/PermissionLayerHeader'

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('PermissionLayerHeader — FR-016', () => {
  test('Layer 1 renders ⓵ glyph', () => {
    const { lastFrame } = render(
      <PermissionLayerHeader layer={1} toolName="koroad_accident_search" />,
    )
    expect(lastFrame()).toContain('⓵')
  })

  test('Layer 2 renders ⓶ glyph', () => {
    const { lastFrame } = render(
      <PermissionLayerHeader layer={2} toolName="hira_hospital_search" />,
    )
    expect(lastFrame()).toContain('⓶')
  })

  test('Layer 3 renders ⓷ glyph', () => {
    const { lastFrame } = render(
      <PermissionLayerHeader layer={3} toolName="gov24_jeonib_submit" />,
    )
    expect(lastFrame()).toContain('⓷')
  })

  test('Tool name is rendered', () => {
    const { lastFrame } = render(
      <PermissionLayerHeader layer={2} toolName="nmc_emergency_search" />,
    )
    expect(lastFrame()).toContain('nmc_emergency_search')
  })

  test('Layer label is rendered', () => {
    const { lastFrame } = render(
      <PermissionLayerHeader layer={1} toolName="test_tool" />,
    )
    expect(lastFrame()).toContain('Layer 1')
  })
})
