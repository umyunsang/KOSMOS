// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — /agents command unit tests (T058)
//
// Covers parseAgentsArgs, validateAgentsArgs, and swarm boundary integration.
// FR-026: /agents and /agents --detail
// FR-027: swarm activation boundary cases are exercised in AgentVisibilityPanel.test.ts
//         and duplicated here for command-level regression protection.

import { describe, expect, test } from 'bun:test'
import {
  parseAgentsArgs,
  validateAgentsArgs,
} from '../../src/commands/agents.tsx'
import { shouldActivateSwarm } from '../../src/schemas/ui-l2/agent.js'

// ── parseAgentsArgs ──────────────────────────────────────────────────────────

describe('parseAgentsArgs', () => {
  test('empty string → detail: false', () => {
    expect(parseAgentsArgs('')).toEqual({ detail: false })
  })

  test('whitespace only → detail: false', () => {
    expect(parseAgentsArgs('   ')).toEqual({ detail: false })
  })

  test('--detail → detail: true', () => {
    expect(parseAgentsArgs('--detail')).toEqual({ detail: true })
  })

  test('-d shorthand → detail: true', () => {
    expect(parseAgentsArgs('-d')).toEqual({ detail: true })
  })

  test('whitespace around --detail is trimmed', () => {
    expect(parseAgentsArgs('  --detail  ')).toEqual({ detail: true })
  })

  test('unknown flag → detail: false (not --detail)', () => {
    // Unknown flags pass through as detail:false; validateAgentsArgs handles rejection
    expect(parseAgentsArgs('--verbose')).toEqual({ detail: false })
  })
})

// ── validateAgentsArgs ───────────────────────────────────────────────────────

describe('validateAgentsArgs', () => {
  test('empty string is valid', () => {
    expect(validateAgentsArgs('')).toBeNull()
  })

  test('--detail is valid', () => {
    expect(validateAgentsArgs('--detail')).toBeNull()
  })

  test('-d is valid', () => {
    expect(validateAgentsArgs('-d')).toBeNull()
  })

  test('whitespace only is valid (treated as default)', () => {
    expect(validateAgentsArgs('  ')).toBeNull()
  })

  test('unknown flag returns error message', () => {
    const result = validateAgentsArgs('--verbose')
    expect(result).toBeTypeOf('string')
    expect(result).toContain('Unknown argument')
    expect(result).toContain('--verbose')
  })

  test('positional arg returns error message', () => {
    const result = validateAgentsArgs('MOHW')
    expect(result).toBeTypeOf('string')
    expect(result).toContain('Unknown argument')
  })
})

// ── Swarm boundary — command-level regression (FR-027) ───────────────────────

describe('shouldActivateSwarm boundary (command regression)', () => {
  test('2-ministry simple → swarm inactive', () => {
    expect(
      shouldActivateSwarm({ mentioned_ministries: ['MOHW', 'KNPA'], complexity_tag: 'simple' }),
    ).toBe(false)
  })

  test('3-ministry simple → swarm active (threshold A)', () => {
    expect(
      shouldActivateSwarm({ mentioned_ministries: ['MOHW', 'KNPA', 'MOIS'], complexity_tag: 'simple' }),
    ).toBe(true)
  })

  test('2-ministry complex → swarm active (threshold C)', () => {
    expect(
      shouldActivateSwarm({ mentioned_ministries: ['MOHW', 'KNPA'], complexity_tag: 'complex' }),
    ).toBe(true)
  })

  test('1-ministry simple → swarm inactive', () => {
    expect(
      shouldActivateSwarm({ mentioned_ministries: ['MOHW'], complexity_tag: 'simple' }),
    ).toBe(false)
  })

  test('0-ministry complex → swarm active (C alone is sufficient)', () => {
    expect(
      shouldActivateSwarm({ mentioned_ministries: [], complexity_tag: 'complex' }),
    ).toBe(true)
  })
})
