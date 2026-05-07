// SPDX-License-Identifier: Apache-2.0
// KOSAX-original — guards user-visible resume instructions from regressing
// to Claude Code's upstream CLI name.

import { describe, expect, test } from 'bun:test'
import { readFileSync } from 'fs'
import { join } from 'path'
import {
  KOSAX_CLI_COMMAND,
  KOSAX_CONTINUE_COMMAND,
  KOSAX_PRINT_RESUME_USAGE,
  formatKosaxResumeCommand,
} from '../../src/constants/cli'

const REPO_ROOT = join(import.meta.dir, '..', '..', '..')

const RESUME_SURFACE_FILES = [
  'tui/src/utils/gracefulShutdown.ts',
  'tui/src/utils/crossProjectResume.ts',
  'tui/src/services/tips/tipRegistry.ts',
  'tui/src/cli/print.ts',
]

describe('KOSAX resume branding', () => {
  test('formats resume commands with the KOSAX CLI name', () => {
    expect(KOSAX_CLI_COMMAND).toBe('kosax')
    expect(KOSAX_CONTINUE_COMMAND).toBe('kosax --continue')
    expect(KOSAX_PRINT_RESUME_USAGE).toBe('kosax -p --resume <session-id>')
    expect(formatKosaxResumeCommand('550e8400-e29b-41d4-a716-446655440000')).toBe(
      'kosax --resume 550e8400-e29b-41d4-a716-446655440000',
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

    expect(replSource).toContain("?? 'KOSAX'")
    expect(replSource).not.toContain("?? 'Claude Code'")
    expect(mainSource).toContain("process.title = 'kosax'")
    expect(mainSource).not.toContain("process.title = 'claude'")
  })
})
