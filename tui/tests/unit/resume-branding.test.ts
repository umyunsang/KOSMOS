// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — guards user-visible resume instructions from regressing
// to Claude Code's upstream CLI name.

import { describe, expect, test } from 'bun:test'
import { readFileSync } from 'fs'
import { join } from 'path'
import {
  UMMAYA_CLI_COMMAND,
  UMMAYA_CONTINUE_COMMAND,
  UMMAYA_PRINT_RESUME_USAGE,
  formatUmmayaResumeCommand,
} from '../../src/constants/cli'

const REPO_ROOT = join(import.meta.dir, '..', '..', '..')

const RESUME_SURFACE_FILES = [
  'tui/src/utils/gracefulShutdown.ts',
  'tui/src/utils/crossProjectResume.ts',
  'tui/src/services/tips/tipRegistry.ts',
  'tui/src/cli/print.ts',
]

describe('UMMAYA resume branding', () => {
  test('formats resume commands with the UMMAYA CLI name', () => {
    expect(UMMAYA_CLI_COMMAND).toBe('ummaya')
    expect(UMMAYA_CONTINUE_COMMAND).toBe('ummaya --continue')
    expect(UMMAYA_PRINT_RESUME_USAGE).toBe('ummaya -p --resume <session-id>')
    expect(formatUmmayaResumeCommand('550e8400-e29b-41d4-a716-446655440000')).toBe(
      'ummaya --resume 550e8400-e29b-41d4-a716-446655440000',
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

    expect(replSource).toContain("?? 'UMMAYA'")
    expect(replSource).not.toContain("?? 'Claude Code'")
    expect(mainSource).toContain("process.title = 'ummaya'")
    expect(mainSource).not.toContain("process.title = 'claude'")
  })
})
