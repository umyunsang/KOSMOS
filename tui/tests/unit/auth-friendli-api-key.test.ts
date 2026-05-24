// SPDX-License-Identifier: Apache-2.0
// FriendliAI credential tests using the CC auth.ts API-key surface.

import { afterEach, beforeEach, describe, expect, it } from 'bun:test'
import {
  FRIENDLI_LOGIN_REQUIRED_MESSAGE,
  FRIENDLI_PRIMARY_ENV,
  assertFriendliApiKeyForUse,
  getAnthropicApiKeyWithSource,
  removeApiKey,
  saveApiKey,
} from '../../src/utils/auth.js'

const savedEnv: Record<string, string | undefined> = {}

beforeEach(async () => {
  savedEnv.NODE_ENV = process.env.NODE_ENV
  savedEnv[FRIENDLI_PRIMARY_ENV] = process.env[FRIENDLI_PRIMARY_ENV]
  process.env.NODE_ENV = 'test'
  delete process.env[FRIENDLI_PRIMARY_ENV]
  await removeApiKey()
})

afterEach(async () => {
  process.env.NODE_ENV = 'test'
  await removeApiKey()
  if (savedEnv.NODE_ENV === undefined) {
    delete process.env.NODE_ENV
  } else {
    process.env.NODE_ENV = savedEnv.NODE_ENV
  }
  if (savedEnv[FRIENDLI_PRIMARY_ENV] === undefined) {
    delete process.env[FRIENDLI_PRIMARY_ENV]
  } else {
    process.env[FRIENDLI_PRIMARY_ENV] = savedEnv[FRIENDLI_PRIMARY_ENV]
  }
})

describe('auth.ts FriendliAI API-key swap', () => {
  it('treats UMMAYA_FRIENDLI_TOKEN as the primary key without a session marker', () => {
    process.env[FRIENDLI_PRIMARY_ENV] = 'env-token'

    expect(getAnthropicApiKeyWithSource()).toEqual({
      key: 'env-token',
      source: FRIENDLI_PRIMARY_ENV,
    })
    expect(assertFriendliApiKeyForUse()).toBe('env-token')
  })

  it('stores /login keys through the CC managed API-key config slot', async () => {
    await saveApiKey('  saved-token  ')

    expect(process.env[FRIENDLI_PRIMARY_ENV]).toBe('saved-token')
    delete process.env[FRIENDLI_PRIMARY_ENV]
    expect(getAnthropicApiKeyWithSource()).toEqual({
      key: 'saved-token',
      source: '/login managed key',
    })
    expect(assertFriendliApiKeyForUse()).toBe('saved-token')
  })

  it('fails closed when no FriendliAI key is present', () => {
    expect(() => assertFriendliApiKeyForUse()).toThrow(FRIENDLI_LOGIN_REQUIRED_MESSAGE)
  })

  it('rejects empty and multiline /login keys', async () => {
    await expect(saveApiKey('   ')).rejects.toThrow('must not be empty')
    await expect(saveApiKey('key\nsecond-line')).rejects.toThrow('single line')
  })
})
