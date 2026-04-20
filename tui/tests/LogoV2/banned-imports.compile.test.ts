// SPDX-License-Identifier: Apache-2.0
// T043 — static source-scan banned-import guard (Epic H #1302).
// Invariant I-22: every file in the LogoV2 + chrome + onboarding family
// must contain ZERO references to the CC-only component names below.

import { describe, expect, it } from 'bun:test'
import { readFileSync } from 'node:fs'
import { globSync } from 'node:fs'
import { resolve } from 'node:path'

const ROOT = resolve(import.meta.dir, '../..')

const SCAN_GLOBS = [
  'src/components/onboarding/LogoV2/**/*.{ts,tsx}',
  'src/components/chrome/KosmosCoreIcon.tsx',
  'src/components/onboarding/Onboarding.tsx',
  'src/components/onboarding/PIPAConsentStep.tsx',
  'src/components/onboarding/MinistryScopeStep.tsx',
]

const BANNED_RE =
  /(?:^|\W)(Clawd|AnimatedClawd|GuestPassesUpsell|EmergencyTip|VoiceModeNotice|Opus1mMergeNotice|ChannelsNotice|OverageCreditUpsell)(?:$|\W)/m

function collectSources(): string[] {
  const files: string[] = []
  for (const pattern of SCAN_GLOBS) {
    for (const match of globSync(pattern, { cwd: ROOT })) {
      files.push(resolve(ROOT, match))
    }
  }
  return Array.from(new Set(files))
}

/**
 * Strips `//...` line comments and `/* ... *\/` block comments from a TS/TSX
 * source body before the banned-import regex runs.  The ban is about
 * executable references — documentation that enumerates the banned names
 * (e.g. the LogoV2.tsx header's "BANNED IMPORTS" note) must NOT count.
 */
function stripComments(body: string): string {
  // Block comments first (non-greedy across lines).
  const noBlock = body.replace(/\/\*[\s\S]*?\*\//g, '')
  // Then line comments (until end-of-line).
  return noBlock.replace(/\/\/[^\n]*/g, '')
}

describe('banned-imports compile-time guard (I-22)', () => {
  it('scans at least one file', () => {
    expect(collectSources().length).toBeGreaterThan(0)
  })

  it('zero occurrences of banned CC component names in LogoV2/chrome/onboarding', () => {
    const offenders: string[] = []
    for (const file of collectSources()) {
      const body = stripComments(readFileSync(file, 'utf8'))
      if (BANNED_RE.test(body)) offenders.push(file)
    }
    expect(offenders).toEqual([])
  })
})
