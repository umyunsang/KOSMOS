// SPDX-License-Identifier: Apache-2.0
// UMMAYA must not inherit Claude Code's Anthropic remote min-version gate.

import { afterEach, beforeEach, describe, expect, it, spyOn } from 'bun:test'
import * as growthbook from '../../src/services/analytics/growthbook.js'
import * as shutdown from '../../src/utils/gracefulShutdown.js'

const getDynamicConfig = spyOn(
  growthbook,
  'getDynamicConfig_BLOCKS_ON_INIT',
).mockImplementation(async () => {
  throw new Error('Anthropic GrowthBook min-version gate must not be queried')
})
const gracefulShutdownSync = spyOn(
  shutdown,
  'gracefulShutdownSync',
).mockImplementation((_exitCode?: number) => undefined)
const consoleError = spyOn(console, 'error').mockImplementation(() => undefined)

const { assertMinVersion } = await import('../../src/utils/autoUpdater.js')

let savedNodeEnv: string | undefined
let savedMinVersion: string | undefined

beforeEach(() => {
  savedNodeEnv = process.env.NODE_ENV
  savedMinVersion = process.env.UMMAYA_MIN_VERSION
  process.env.NODE_ENV = 'production'
  delete process.env.UMMAYA_MIN_VERSION
  getDynamicConfig.mockClear()
  gracefulShutdownSync.mockClear()
  consoleError.mockClear()
})

afterEach(() => {
  if (savedNodeEnv === undefined) {
    delete process.env.NODE_ENV
  } else {
    process.env.NODE_ENV = savedNodeEnv
  }
  if (savedMinVersion === undefined) {
    delete process.env.UMMAYA_MIN_VERSION
  } else {
    process.env.UMMAYA_MIN_VERSION = savedMinVersion
  }
})

describe('UMMAYA min-version gate', () => {
  it('does not query Claude Code GrowthBook config by default', async () => {
    await assertMinVersion()

    expect(getDynamicConfig).not.toHaveBeenCalled()
    expect(gracefulShutdownSync).not.toHaveBeenCalled()
  })

  it('enforces an explicit UMMAYA_MIN_VERSION override', async () => {
    process.env.UMMAYA_MIN_VERSION = '999.0.0'

    await assertMinVersion()

    expect(getDynamicConfig).not.toHaveBeenCalled()
    expect(gracefulShutdownSync).toHaveBeenCalledWith(1)
  })
})
