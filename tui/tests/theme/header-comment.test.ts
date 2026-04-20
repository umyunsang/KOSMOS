// SPDX-License-Identifier: Apache-2.0
// T038 — header-comment assertion on tokens.ts + dark.ts (Epic H #1302).
// Contract: specs/035-onboarding-brand-port/contracts/brand-token-surface.md § 5.
// Invariant: I-20. Satisfies FR-008.

import { describe, expect, it } from 'bun:test'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const TOKENS_PATH = resolve(import.meta.dir, '../../src/theme/tokens.ts')
const DARK_PATH = resolve(import.meta.dir, '../../src/theme/dark.ts')

const SOURCE_LINE =
  '// Source: .references/claude-code-sourcemap/restored-src/src/utils/theme.ts'
const KOSMOS_RENAME_LINE =
  '// KOSMOS 브랜드 토큰으로 리네이밍됨 (ADR-006 A-9)'

describe('theme file header comments (brand-token-surface § 5)', () => {
  it('tokens.ts carries the CC source attribution line', () => {
    const body = readFileSync(TOKENS_PATH, 'utf8')
    expect(body).toContain(SOURCE_LINE)
  })

  it('tokens.ts carries the KOSMOS rename header', () => {
    const body = readFileSync(TOKENS_PATH, 'utf8')
    expect(body).toContain(KOSMOS_RENAME_LINE)
  })

  it('dark.ts carries the CC source attribution line', () => {
    const body = readFileSync(DARK_PATH, 'utf8')
    expect(body).toContain(SOURCE_LINE)
  })

  it('dark.ts carries the KOSMOS rename header', () => {
    const body = readFileSync(DARK_PATH, 'utf8')
    expect(body).toContain(KOSMOS_RENAME_LINE)
  })

  it('rename header follows the source line in tokens.ts', () => {
    const body = readFileSync(TOKENS_PATH, 'utf8')
    const sourceIdx = body.indexOf(SOURCE_LINE)
    const renameIdx = body.indexOf(KOSMOS_RENAME_LINE)
    expect(sourceIdx).toBeGreaterThan(-1)
    expect(renameIdx).toBeGreaterThan(sourceIdx)
  })

  it('rename header follows the source line in dark.ts', () => {
    const body = readFileSync(DARK_PATH, 'utf8')
    const sourceIdx = body.indexOf(SOURCE_LINE)
    const renameIdx = body.indexOf(KOSMOS_RENAME_LINE)
    expect(sourceIdx).toBeGreaterThan(-1)
    expect(renameIdx).toBeGreaterThan(sourceIdx)
  })
})
