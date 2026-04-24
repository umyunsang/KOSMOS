// Unit test for the `bun:bundle` runtime stub (Epic #1632 · T007 · FR-003).
//
// Verifies that every known feature flag from the ported CC 2.1.88 source
// resolves to `false`, and that unknown / edge-case flags are equally safe.

import { describe, expect, it } from 'bun:test';
import { feature } from 'bun:bundle';

// The 17 flags enumerated in Epic #1632 file-level scope.
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
] as const;

describe('bun:bundle feature stub', () => {
  for (const flag of KNOWN_FLAGS) {
    it(`returns false for known flag ${flag}`, () => {
      expect(feature(flag)).toBe(false);
    });
  }

  it('returns false for an unknown flag', () => {
    expect(feature('UNKNOWN_FLAG_XYZ')).toBe(false);
  });

  it('returns false for an empty string without throwing', () => {
    expect(() => feature('')).not.toThrow();
    expect(feature('')).toBe(false);
  });

  it('is a synchronous function (no promise return)', () => {
    const result = feature('KAIROS');
    expect(typeof result).toBe('boolean');
  });
});
