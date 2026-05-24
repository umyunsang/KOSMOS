// SPDX-License-Identifier: Apache-2.0
// Regression coverage for exact slash-command submission while suggestions are visible.

import { describe, expect, it } from 'bun:test'
import type { Command } from '../../src/commands.js'
import { isExactSlashCommandInput } from '../../src/utils/suggestions/commandSuggestions.js'

function makeLocalCommand(name: string, aliases?: string[]): Command {
  return {
    type: 'local',
    name,
    aliases,
    description: name,
    isHidden: false,
    inputSchema: {},
    userFacingName: () => name,
    call: async () => ({
      type: 'result',
      resultForAssistant: '',
    }),
  } as Command
}

const commands = [
  makeLocalCommand('login'),
  makeLocalCommand('logout', ['signout']),
]

describe('isExactSlashCommandInput', () => {
  it('accepts exact slash commands even when autocomplete suggestions exist', () => {
    expect(isExactSlashCommandInput('/login', commands)).toBe(true)
    expect(isExactSlashCommandInput('/login ', commands)).toBe(true)
  })

  it('accepts exact aliases', () => {
    expect(isExactSlashCommandInput('/signout', commands)).toBe(true)
  })

  it('rejects partial commands and commands with arguments', () => {
    expect(isExactSlashCommandInput('/logi', commands)).toBe(false)
    expect(isExactSlashCommandInput('/login now', commands)).toBe(false)
  })
})
