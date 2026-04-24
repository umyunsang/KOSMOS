// Unit test for the `bun:bundle` runtime stub (Epic #1632 · T007 · FR-003).
//
// Bun's compiler treats `feature()` imported via `bun:bundle` as a special
// macro that's only legal inside `if` conditions / ternaries — calling it as
// a bare expression in a test is rejected at parse time. To still exercise
// the stub's behavior, we import it directly from the stub file (not via the
// `bun:bundle` virtual module), which bypasses the macro check.

import { describe, expect, it } from 'bun:test'
import { feature } from '../../../src/stubs/bun-bundle.js'

const KNOWN_FLAGS = [
  'COORDINATOR_MODE',
  'KAIROS',
  'KAIROS_BRIEF',
  'KAIROS_CHANNELS',
  'TRANSCRIPT_CLASSIFIER',
  'DIRECT_CONNECT',
  'LODESTONE',
  'SSH_REMOTE',
  'UDS_INBOX',
  'BG_SESSIONS',
  'UPLOAD_USER_SETTINGS',
  'WEB_BROWSER_TOOL',
  'CHICAGO_MCP',
  'PROACTIVE',
  'HARD_FAIL',
  'CCR_MIRROR',
  'AGENT_MEMORY_SNAPSHOT',
  'BRIDGE_MODE',
] as const

describe('bun:bundle feature stub', () => {
  for (const flag of KNOWN_FLAGS) {
    it(`returns false for known flag ${flag}`, () => {
      expect(feature(flag)).toBe(false)
    })
  }

  it('returns false for an unknown flag', () => {
    expect(feature('UNKNOWN_FLAG_XYZ')).toBe(false)
  })

  it('returns false for an empty string without throwing', () => {
    expect(() => feature('')).not.toThrow()
    expect(feature('')).toBe(false)
  })

  it('returns a synchronous boolean', () => {
    const result = feature('KAIROS')
    expect(typeof result).toBe('boolean')
  })
})
