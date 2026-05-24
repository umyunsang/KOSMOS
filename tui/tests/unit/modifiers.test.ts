// SPDX-License-Identifier: Apache-2.0
// Apple Terminal Enter must not depend on Claude Code's private native bundle.

import { describe, expect, it } from 'bun:test'
import { isModifierPressed } from '../../src/utils/modifiers'

describe('modifier detection', () => {
  it('fails closed when the native modifier bridge is unavailable', () => {
    expect(() => isModifierPressed('shift')).not.toThrow()
    expect(typeof isModifierPressed('shift')).toBe('boolean')
  })
})
