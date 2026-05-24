import { afterEach, describe, expect, it } from 'bun:test'
import { homedir } from 'os'
import { join } from 'path'
import { getClaudeConfigHomeDir } from '../../../src/utils/envUtils.js'

function clearConfigHomeCache(): void {
  const cacheHolder = getClaudeConfigHomeDir as typeof getClaudeConfigHomeDir & {
    cache?: { clear?: () => void }
  }
  cacheHolder.cache?.clear?.()
}

describe('UMMAYA config home boundary', () => {
  afterEach(() => {
    delete process.env.UMMAYA_CONFIG_DIR
    delete process.env.CLAUDE_CONFIG_DIR
    clearConfigHomeCache()
  })

  it('stores runtime state under ~/.ummaya by default', () => {
    clearConfigHomeCache()

    expect(getClaudeConfigHomeDir()).toBe(join(homedir(), '.ummaya').normalize('NFC'))
  })

  it('prefers UMMAYA_CONFIG_DIR over the legacy Claude config override', () => {
    process.env.CLAUDE_CONFIG_DIR = '/tmp/legacy-claude-config'
    process.env.UMMAYA_CONFIG_DIR = '/tmp/ummaya-config'
    clearConfigHomeCache()

    expect(getClaudeConfigHomeDir()).toBe('/tmp/ummaya-config')
  })
})
