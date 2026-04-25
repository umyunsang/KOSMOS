// SPDX-License-Identifier: Apache-2.0
// T051 — /lang command unit tests (FR-004, T047).

import { afterEach, beforeEach, describe, expect, it } from 'bun:test'
import {
  getCurrentLocale,
  parseLangCommand,
  type LangCommandResult,
} from '../../src/commands/lang'

// Save and restore KOSMOS_TUI_LOCALE across tests
const SAVED_LOCALE = process.env['KOSMOS_TUI_LOCALE']

beforeEach(() => {
  delete process.env['KOSMOS_TUI_LOCALE']
})

afterEach(() => {
  if (SAVED_LOCALE !== undefined) {
    process.env['KOSMOS_TUI_LOCALE'] = SAVED_LOCALE
  } else {
    delete process.env['KOSMOS_TUI_LOCALE']
  }
})

describe('parseLangCommand — valid locales', () => {
  it('switches to Korean (ko)', () => {
    const result = parseLangCommand('ko')
    expect(result.ok).toBe(true)
    expect((result as Extract<LangCommandResult, { ok: true }>).locale).toBe('ko')
    expect(process.env['KOSMOS_TUI_LOCALE']).toBe('ko')
  })

  it('switches to English (en)', () => {
    const result = parseLangCommand('en')
    expect(result.ok).toBe(true)
    expect((result as Extract<LangCommandResult, { ok: true }>).locale).toBe('en')
    expect(process.env['KOSMOS_TUI_LOCALE']).toBe('en')
  })

  it('is case-insensitive — KO normalizes to ko', () => {
    const result = parseLangCommand('KO')
    expect(result.ok).toBe(true)
    expect((result as Extract<LangCommandResult, { ok: true }>).locale).toBe('ko')
  })

  it('is case-insensitive — EN normalizes to en', () => {
    const result = parseLangCommand('EN')
    expect(result.ok).toBe(true)
    expect((result as Extract<LangCommandResult, { ok: true }>).locale).toBe('en')
  })

  it('trims whitespace', () => {
    const result = parseLangCommand('  en  ')
    expect(result.ok).toBe(true)
  })
})

describe('parseLangCommand — invalid inputs', () => {
  it('returns error for empty argument', () => {
    const result = parseLangCommand('')
    expect(result.ok).toBe(false)
    expect((result as Extract<LangCommandResult, { ok: false }>).message).toContain('Usage')
  })

  it('returns error for unsupported locale', () => {
    const result = parseLangCommand('ja')
    expect(result.ok).toBe(false)
    expect((result as Extract<LangCommandResult, { ok: false }>).message).toContain('ja')
    expect((result as Extract<LangCommandResult, { ok: false }>).message).toContain('ko')
    expect((result as Extract<LangCommandResult, { ok: false }>).message).toContain('en')
  })

  it('does not mutate process.env on error', () => {
    process.env['KOSMOS_TUI_LOCALE'] = 'ko'
    parseLangCommand('unsupported')
    expect(process.env['KOSMOS_TUI_LOCALE']).toBe('ko')
  })
})

describe('getCurrentLocale', () => {
  it('returns ko by default when KOSMOS_TUI_LOCALE is unset', () => {
    delete process.env['KOSMOS_TUI_LOCALE']
    expect(getCurrentLocale()).toBe('ko')
  })

  it('returns en when KOSMOS_TUI_LOCALE=en', () => {
    process.env['KOSMOS_TUI_LOCALE'] = 'en'
    expect(getCurrentLocale()).toBe('en')
  })

  it('returns ko as fallback for unrecognised locale values', () => {
    process.env['KOSMOS_TUI_LOCALE'] = 'ja'
    expect(getCurrentLocale()).toBe('ko')
  })
})

describe('parseLangCommand — side effect on process.env', () => {
  it('subsequent getCurrentLocale returns updated locale', () => {
    parseLangCommand('en')
    expect(getCurrentLocale()).toBe('en')
    parseLangCommand('ko')
    expect(getCurrentLocale()).toBe('ko')
  })
})
