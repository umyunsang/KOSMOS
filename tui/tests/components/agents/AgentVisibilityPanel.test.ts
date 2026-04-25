// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — AgentVisibilityPanel + swarm predicate unit tests (T058)
//
// Covers FR-025 (5-state enum), FR-027 (swarm A+C union), FR-028 (IPC mapping),
// SC-007 (live update correctness).

import { describe, expect, test } from 'bun:test'
import {
  shouldActivateSwarm,
  AgentVisibilityEntry,
  AgentState,
  AgentHealth,
  dotColorForPrimitive,
} from '../../../src/schemas/ui-l2/agent.js'
import type { AgentVisibilityEntryT } from '../../../src/schemas/ui-l2/agent.js'

// ── shouldActivateSwarm boundary cases (FR-027 A+C union) ───────────────────

describe('shouldActivateSwarm — A+C union semantics (FR-027)', () => {
  // Condition A only

  test('A: exactly 3 distinct ministries → activates', () => {
    expect(
      shouldActivateSwarm({
        mentioned_ministries: ['MOHW', 'KNPA', 'MOIS'],
        complexity_tag: 'simple',
      }),
    ).toBe(true)
  })

  test('A: 4 ministries → activates', () => {
    expect(
      shouldActivateSwarm({
        mentioned_ministries: ['MOHW', 'KNPA', 'MOIS', 'KOROAD'],
        complexity_tag: 'simple',
      }),
    ).toBe(true)
  })

  test('A: 2 ministries → does NOT activate (no C)', () => {
    expect(
      shouldActivateSwarm({
        mentioned_ministries: ['MOHW', 'KNPA'],
        complexity_tag: 'simple',
      }),
    ).toBe(false)
  })

  test('A: 1 ministry → does NOT activate', () => {
    expect(
      shouldActivateSwarm({
        mentioned_ministries: ['MOHW'],
        complexity_tag: 'simple',
      }),
    ).toBe(false)
  })

  test('A: 0 ministries → does NOT activate', () => {
    expect(
      shouldActivateSwarm({
        mentioned_ministries: [],
        complexity_tag: 'simple',
      }),
    ).toBe(false)
  })

  // Condition C only

  test('C: LLM "complex" tag → activates regardless of ministry count', () => {
    expect(
      shouldActivateSwarm({
        mentioned_ministries: ['MOHW'],
        complexity_tag: 'complex',
      }),
    ).toBe(true)
  })

  test('C: "complex" tag with 0 ministries → activates', () => {
    expect(
      shouldActivateSwarm({
        mentioned_ministries: [],
        complexity_tag: 'complex',
      }),
    ).toBe(true)
  })

  // A + C combined (edge case from spec.md edge cases)

  test('A+C: 2 ministries + "complex" tag → activates (OR semantics)', () => {
    expect(
      shouldActivateSwarm({
        mentioned_ministries: ['MOHW', 'KNPA'],
        complexity_tag: 'complex',
      }),
    ).toBe(true)
  })

  test('A+C: 3 ministries + "complex" tag → activates', () => {
    expect(
      shouldActivateSwarm({
        mentioned_ministries: ['MOHW', 'KNPA', 'MOIS'],
        complexity_tag: 'complex',
      }),
    ).toBe(true)
  })

  // De-duplication of ministry list

  test('A: duplicate ministries are de-duplicated (distinct count)', () => {
    // ['MOHW','MOHW','KNPA'] has only 2 distinct — should NOT trigger A
    expect(
      shouldActivateSwarm({
        mentioned_ministries: ['MOHW', 'MOHW', 'KNPA'],
        complexity_tag: 'simple',
      }),
    ).toBe(false)
  })

  test('A: whitespace-padded entries are trimmed before distinct count', () => {
    // ' MOHW' and 'MOHW' should both count as the same ministry
    expect(
      shouldActivateSwarm({
        mentioned_ministries: [' MOHW', 'MOHW', 'KNPA'],
        complexity_tag: 'simple',
      }),
    ).toBe(false)
  })

  test('A: 3 distinct whitespace-padded ministries → activates after trim', () => {
    expect(
      shouldActivateSwarm({
        mentioned_ministries: [' MOHW ', ' KNPA ', ' MOIS '],
        complexity_tag: 'simple',
      }),
    ).toBe(true)
  })

  // Empty strings filtered

  test('A: empty string entries are filtered out before distinct count', () => {
    expect(
      shouldActivateSwarm({
        mentioned_ministries: ['', 'MOHW', '', 'KNPA', ''],
        complexity_tag: 'simple',
      }),
    ).toBe(false)
  })
})

// ── AgentVisibilityEntry Zod schema (FR-025) ─────────────────────────────────

describe('AgentVisibilityEntry schema validation (FR-025)', () => {
  const validEntry: AgentVisibilityEntryT = {
    agent_id: 'worker-mohw-001',
    ministry: 'MOHW',
    state: 'running',
    sla_remaining_ms: 30_000,
    health: 'green',
    rolling_avg_response_ms: 210,
    last_transition_at: new Date().toISOString(),
  }

  test('valid entry parses without errors', () => {
    const result = AgentVisibilityEntry.safeParse(validEntry)
    expect(result.success).toBe(true)
  })

  test('all 5 AgentState values are valid', () => {
    const states = ['idle', 'dispatched', 'running', 'waiting-permission', 'done'] as const
    for (const state of states) {
      const result = AgentState.safeParse(state)
      expect(result.success).toBe(true)
    }
  })

  test('unknown state value is rejected', () => {
    const result = AgentState.safeParse('stuck')
    expect(result.success).toBe(false)
  })

  test('all 3 AgentHealth values are valid', () => {
    const healths = ['green', 'amber', 'red'] as const
    for (const health of healths) {
      const result = AgentHealth.safeParse(health)
      expect(result.success).toBe(true)
    }
  })

  test('sla_remaining_ms may be null (dispatched state)', () => {
    const result = AgentVisibilityEntry.safeParse({
      ...validEntry,
      state: 'dispatched',
      sla_remaining_ms: null,
    })
    expect(result.success).toBe(true)
  })

  test('sla_remaining_ms must be nonnegative integer when set', () => {
    const negative = AgentVisibilityEntry.safeParse({
      ...validEntry,
      sla_remaining_ms: -1,
    })
    expect(negative.success).toBe(false)

    const float = AgentVisibilityEntry.safeParse({
      ...validEntry,
      sla_remaining_ms: 1.5,
    })
    expect(float.success).toBe(false)
  })

  test('rolling_avg_response_ms may be null', () => {
    const result = AgentVisibilityEntry.safeParse({
      ...validEntry,
      rolling_avg_response_ms: null,
    })
    expect(result.success).toBe(true)
  })

  test('rolling_avg_response_ms must be nonnegative when set', () => {
    const negative = AgentVisibilityEntry.safeParse({
      ...validEntry,
      rolling_avg_response_ms: -0.1,
    })
    expect(negative.success).toBe(false)
  })

  test('agent_id must be non-empty', () => {
    const result = AgentVisibilityEntry.safeParse({ ...validEntry, agent_id: '' })
    expect(result.success).toBe(false)
  })

  test('ministry must be non-empty', () => {
    const result = AgentVisibilityEntry.safeParse({ ...validEntry, ministry: '' })
    expect(result.success).toBe(false)
  })
})

// ── dotColorForPrimitive (proposal-iv dot color regulation) ─────────────────

describe('dotColorForPrimitive — primitive dot color regulation', () => {
  test('lookup → primitiveLookup', () => {
    expect(dotColorForPrimitive('lookup')).toBe('primitiveLookup')
  })

  test('submit → primitiveSubmit', () => {
    expect(dotColorForPrimitive('submit')).toBe('primitiveSubmit')
  })

  test('verify → primitiveVerify', () => {
    expect(dotColorForPrimitive('verify')).toBe('primitiveVerify')
  })

  test('subscribe → primitiveSubscribe', () => {
    expect(dotColorForPrimitive('subscribe')).toBe('primitiveSubscribe')
  })

  test('plugin.* → primitivePlugin', () => {
    expect(dotColorForPrimitive('plugin.seoul-subway')).toBe('primitivePlugin')
    expect(dotColorForPrimitive('plugin.post-office')).toBe('primitivePlugin')
  })

  test('unknown verb falls back to primitivePlugin', () => {
    expect(dotColorForPrimitive('unknown_verb')).toBe('primitivePlugin')
  })
})
