import { describe, expect, it } from 'bun:test'
import packageJson from '../../package.json' with { type: 'json' }

describe('UMMAYA version branding', () => {
  it('uses the stable release version without issue-number build metadata', () => {
    expect(packageJson.version).toMatch(/^\d+\.\d+\.\d+$/)
    expect(packageJson.version).not.toMatch(/\+\d+$/)
    expect(packageJson.version).not.toContain('+1978')
  })

  it('brands the public CLI help as UMMAYA', async () => {
    const source = await Bun.file(new URL('../../src/main.tsx', import.meta.url)).text()

    expect(source).toContain("program.name('ummaya')")
    expect(source).toContain('UMMAYA - starts an interactive session')
    expect(source).not.toContain("program.name('claude')")
    expect(source).not.toContain('Claude Code - starts an interactive session')
  })
})
