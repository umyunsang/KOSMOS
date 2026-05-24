// Unit test for the local `bun:bundle` runtime feature registry.
// CC's restored source imports `feature()` from `bun:bundle`, a virtual module
// supplied by the production bundle. UMMAYA source-run mode installs the same
// contract as a local runtime package so normal `bun run tui` works without
// test-only mocks.

import { describe, expect, it } from 'bun:test'
import {
  feature,
  isKnownFeature,
  listKnownFeatures,
} from '../../../src/runtime/bundle-package/index.js'

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

describe('bun:bundle feature registry', () => {
  for (const flag of KNOWN_FLAGS) {
    it(`returns false for known flag ${flag}`, () => {
      expect(isKnownFeature(flag)).toBe(true)
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

  it('lists known restored-source feature names', () => {
    expect(listKnownFeatures()).toContain('VOICE_MODE')
    expect(listKnownFeatures()).toContain('TEAMMEM')
  })
})
