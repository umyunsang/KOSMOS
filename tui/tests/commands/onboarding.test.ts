// SPDX-License-Identifier: Apache-2.0
// T051 — /onboarding command unit tests (FR-003, T046).

import { describe, expect, it } from 'bun:test'
import {
  parseOnboardingCommand,
  type OnboardingCommandResult,
} from '../../src/commands/onboarding'
import { ONBOARDING_STEP_ORDER } from '../../src/schemas/ui-l2/onboarding'

describe('parseOnboardingCommand — no argument', () => {
  it('returns { mode: "full" } for empty string', () => {
    const result = parseOnboardingCommand('')
    expect(result).toEqual({ mode: 'full' })
  })

  it('returns { mode: "full" } for whitespace-only input', () => {
    const result = parseOnboardingCommand('   ')
    expect(result).toEqual({ mode: 'full' })
  })
})

describe('parseOnboardingCommand — valid step names', () => {
  for (const step of ONBOARDING_STEP_ORDER) {
    it(`returns isolated mode for step "${step}"`, () => {
      const result = parseOnboardingCommand(step)
      expect(result).toEqual({ mode: 'isolated', step })
    })
  }

  it('handles leading/trailing whitespace around step name', () => {
    const result = parseOnboardingCommand('  theme  ')
    expect(result).toEqual({ mode: 'isolated', step: 'theme' })
  })
})

describe('parseOnboardingCommand — invalid step names', () => {
  it('returns error mode for unknown step', () => {
    const result = parseOnboardingCommand('unknown-step')
    expect(result.mode).toBe('error')
    expect((result as Extract<OnboardingCommandResult, { mode: 'error' }>).message).toContain(
      'unknown-step',
    )
    expect((result as Extract<OnboardingCommandResult, { mode: 'error' }>).message).toContain(
      'preflight',
    )
  })

  it('returns error mode for CC onboarding step names (not our steps)', () => {
    const result = parseOnboardingCommand('oauth')
    expect(result.mode).toBe('error')
  })

  it('is case-sensitive — capitalized step is invalid', () => {
    const result = parseOnboardingCommand('Theme')
    expect(result.mode).toBe('error')
  })
})

describe('parseOnboardingCommand — all 5 canonical steps are parseable', () => {
  it('parses all 5 step names without error', () => {
    for (const step of ONBOARDING_STEP_ORDER) {
      const result = parseOnboardingCommand(step)
      expect(result.mode).toBe('isolated')
    }
  })
})
