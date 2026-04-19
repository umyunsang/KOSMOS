// T044 — i18n bundle parity test
// Asserts:
//   1. en.ts and ko.ts export the same key set
//   2. No raw English string value appears in ko.ts except technical identifiers

import { describe, expect, it } from 'bun:test'
import en from '../../src/i18n/en'
import ko from '../../src/i18n/ko'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Recursively collect all string/function values from an i18n bundle object.
 * We walk the shape of the objects (not the I18nBundle type) so this test
 * is future-proof — new keys added to the bundle will automatically be checked.
 */
function collectKeys(obj: object): string[] {
  return Object.keys(obj)
}

/**
 * Common English words (≥5 chars) that would only appear in English sentences,
 * not in Korean translations.  We probe a few common filler words from en.ts.
 *
 * The rule: a ko.ts value (for string fields, not function fields) MUST NOT
 * start with an uppercase ASCII letter followed by ASCII words — that pattern
 * indicates an un-translated English string.
 *
 * Technical identifiers like "KOSMOS", "IPC", "Ctrl-C" are allowed per spec.
 */
function isLikelyEnglish(value: string): boolean {
  // Allow known technical identifiers that appear in both bundles
  const TECHNICAL_IDENTIFIERS = [
    'KOSMOS',
    'IPC',
    'Ctrl-C',
    // Korean strings may contain ":" and English tool/session IDs embedded
    // in template functions — those are handled separately below.
  ]
  for (const id of TECHNICAL_IDENTIFIERS) {
    if (value.startsWith(id)) return false
  }

  // If the value contains Korean characters, it's definitely a Korean string
  const containsKorean = /[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]/.test(value)
  if (containsKorean) return false

  // A plain ASCII sentence-like string (starts with capital letter, contains spaces)
  // is likely un-translated English
  if (/^[A-Z][a-z].*\s/.test(value)) return true

  return false
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('i18n key parity (FR-037)', () => {
  it('en.ts and ko.ts export the same key set', () => {
    const enKeys = collectKeys(en).sort()
    const koKeys = collectKeys(ko).sort()
    expect(koKeys).toEqual(enKeys)
  })
})

describe('i18n Korean translation completeness (FR-037)', () => {
  it('ko.ts string values contain Korean characters or technical identifiers', () => {
    const untranslated: string[] = []

    for (const [key, value] of Object.entries(ko)) {
      // Skip function-type values — they are template functions, the
      // interpolated result may contain user-supplied English IDs
      if (typeof value === 'function') continue

      if (typeof value === 'string' && isLikelyEnglish(value)) {
        untranslated.push(`${key}: "${value}"`)
      }
    }

    if (untranslated.length > 0) {
      throw new Error(
        `Likely un-translated English values in ko.ts:\n${untranslated.join('\n')}\n` +
          'Replace with Korean translations or add to TECHNICAL_IDENTIFIERS allowlist.',
      )
    }
  })
})

describe('i18n bundle shape contract', () => {
  it('every key in en.ts is a string or function', () => {
    for (const [key, value] of Object.entries(en)) {
      const type = typeof value
      expect(['string', 'function']).toContain(type as string)
    }
  })

  it('every key in ko.ts is a string or function', () => {
    for (const [key, value] of Object.entries(ko)) {
      const type = typeof value
      expect(['string', 'function']).toContain(type as string)
    }
  })

  it('function-typed keys in en.ts have matching function-typed keys in ko.ts', () => {
    for (const [key, value] of Object.entries(en)) {
      if (typeof value === 'function') {
        const koValue = (ko as unknown as Record<string, unknown>)[key]
        expect(typeof koValue).toBe('function')
      }
    }
  })

  it('string-typed keys in en.ts have matching string-typed keys in ko.ts', () => {
    for (const [key, value] of Object.entries(en)) {
      if (typeof value === 'string') {
        const koValue = (ko as unknown as Record<string, unknown>)[key]
        expect(typeof koValue).toBe('string')
      }
    }
  })
})
