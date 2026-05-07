import { describe, expect, it } from 'bun:test'
import packageJson from '../../package.json' with { type: 'json' }

describe('KOSMOS version branding', () => {
  it('does not expose issue numbers as SemVer build metadata', () => {
    expect(packageJson.version).toBe('0.1.0-alpha')
    expect(packageJson.version).not.toMatch(/\+\d+$/)
    expect(packageJson.version).not.toContain('+1978')
  })
})
