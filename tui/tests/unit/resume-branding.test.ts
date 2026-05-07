// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — guards user-visible resume instructions from regressing
// to Claude Code's upstream CLI name.

import { describe, expect, test } from 'bun:test'
import { readFileSync } from 'fs'
import { join } from 'path'
import {
  KOSMOS_CLI_COMMAND,
  KOSMOS_CONTINUE_COMMAND,
  KOSMOS_PRINT_RESUME_USAGE,
  formatKosmosResumeCommand,
} from '../../src/constants/cli'

const REPO_ROOT = join(import.meta.dir, '..', '..', '..')

const RESUME_SURFACE_FILES = [
  'tui/src/utils/gracefulShutdown.ts',
  'tui/src/utils/crossProjectResume.ts',
  'tui/src/services/tips/tipRegistry.ts',
  'tui/src/cli/print.ts',
]

describe('KOSMOS resume branding', () => {
  test('formats resume commands with the KOSMOS CLI name', () => {
    expect(KOSMOS_CLI_COMMAND).toBe('kosmos')
    expect(KOSMOS_CONTINUE_COMMAND).toBe('kosmos --continue')
    expect(KOSMOS_PRINT_RESUME_USAGE).toBe('kosmos -p --resume <session-id>')
    expect(formatKosmosResumeCommand('550e8400-e29b-41d4-a716-446655440000')).toBe(
      'kosmos --resume 550e8400-e29b-41d4-a716-446655440000',
    )
  })

  test.each(RESUME_SURFACE_FILES)('%s does not expose Claude resume commands', path => {
    const content = readFileSync(join(REPO_ROOT, path), 'utf8')
    expect(content).not.toContain('claude --resume')
    expect(content).not.toContain('claude --continue')
    expect(content).not.toContain('Usage: claude -p --resume')
  })

  test('does not use Claude Code as the terminal title fallback', () => {
    const replSource = readFileSync(
      join(REPO_ROOT, 'tui/src/screens/REPL.tsx'),
      'utf8',
    )
    const mainSource = readFileSync(join(REPO_ROOT, 'tui/src/main.tsx'), 'utf8')

    expect(replSource).toContain("?? 'KOSMOS'")
    expect(replSource).not.toContain("?? 'Claude Code'")
    expect(mainSource).toContain("process.title = 'kosmos'")
    expect(mainSource).not.toContain("process.title = 'claude'")
  })
})
