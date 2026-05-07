// SPDX-License-Identifier: Apache-2.0
/**
 * Unit tests for tui/src/utils/ummayaPaths.ts
 *
 * Verifies:
 *   1. Default paths resolve to ~/.ummaya/memdir/user[/sessions]
 *   2. UMMAYA_MEMDIR_USER env override is respected
 *   3. Memoize invalidation fires when the env var changes between calls
 */

import { test, expect, beforeEach, afterEach } from 'bun:test'
import { homedir } from 'os'
import { join } from 'path'

// We import by absolute path so bun module cache isolation works correctly.
// Each test that mutates process.env must re-import via dynamic import to
// bypass the module cache — or clear the cache via module mock. Because
// ummayaPaths.ts uses a plain closure cache (not lodash memoize), the same
// module instance is fine: mutating env + calling the function again is
// sufficient to observe invalidation.

let getUmmayaUserTierRoot: () => string
let getUmmayaSessionsDir: () => string

const ORIGINAL_UMMAYA_MEMDIR_USER = process.env.UMMAYA_MEMDIR_USER

beforeEach(async () => {
  // Remove any env override so we start from the default state.
  delete process.env.UMMAYA_MEMDIR_USER

  // Dynamic re-import ensures the closure cache is warm-started in the
  // default (no-override) state for each test group.
  const mod = await import('../ummayaPaths.js')
  getUmmayaUserTierRoot = mod.getUmmayaUserTierRoot
  getUmmayaSessionsDir = mod.getUmmayaSessionsDir
})

afterEach(() => {
  // Restore original env state to avoid cross-test pollution.
  if (ORIGINAL_UMMAYA_MEMDIR_USER === undefined) {
    delete process.env.UMMAYA_MEMDIR_USER
  } else {
    process.env.UMMAYA_MEMDIR_USER = ORIGINAL_UMMAYA_MEMDIR_USER
  }
})

// ---------------------------------------------------------------------------
// Default values (no env override)
// ---------------------------------------------------------------------------

test('getUmmayaUserTierRoot returns ~/.ummaya/memdir/user by default', () => {
  delete process.env.UMMAYA_MEMDIR_USER
  const expected = join(homedir(), '.ummaya', 'memdir', 'user')
  expect(getUmmayaUserTierRoot()).toBe(expected)
})

test('getUmmayaSessionsDir returns ~/.ummaya/memdir/user/sessions by default', () => {
  delete process.env.UMMAYA_MEMDIR_USER
  const expected = join(homedir(), '.ummaya', 'memdir', 'user', 'sessions')
  expect(getUmmayaSessionsDir()).toBe(expected)
})

// ---------------------------------------------------------------------------
// Env override
// ---------------------------------------------------------------------------

test('getUmmayaUserTierRoot respects UMMAYA_MEMDIR_USER env override', () => {
  process.env.UMMAYA_MEMDIR_USER = '/tmp/ummaya-test/memdir/user'
  expect(getUmmayaUserTierRoot()).toBe('/tmp/ummaya-test/memdir/user')
})

test('getUmmayaSessionsDir appends /sessions to UMMAYA_MEMDIR_USER override', () => {
  process.env.UMMAYA_MEMDIR_USER = '/tmp/ummaya-test/memdir/user'
  expect(getUmmayaSessionsDir()).toBe('/tmp/ummaya-test/memdir/user/sessions')
})

// ---------------------------------------------------------------------------
// Memoize invalidation — changing the env var between calls gets a fresh value
// ---------------------------------------------------------------------------

test('getUmmayaUserTierRoot invalidates cache when UMMAYA_MEMDIR_USER changes', () => {
  delete process.env.UMMAYA_MEMDIR_USER
  const defaultVal = getUmmayaUserTierRoot()
  expect(defaultVal).toBe(join(homedir(), '.ummaya', 'memdir', 'user'))

  // Now set the env var and call again — must see the new value.
  process.env.UMMAYA_MEMDIR_USER = '/tmp/new-root'
  const overrideVal = getUmmayaUserTierRoot()
  expect(overrideVal).toBe('/tmp/new-root')
})

test('getUmmayaSessionsDir invalidates cache when UMMAYA_MEMDIR_USER changes', () => {
  delete process.env.UMMAYA_MEMDIR_USER
  const defaultVal = getUmmayaSessionsDir()
  expect(defaultVal).toBe(join(homedir(), '.ummaya', 'memdir', 'user', 'sessions'))

  // Switch to override.
  process.env.UMMAYA_MEMDIR_USER = '/tmp/new-root'
  const overrideVal = getUmmayaSessionsDir()
  expect(overrideVal).toBe('/tmp/new-root/sessions')
})

test('getUmmayaSessionsDir returns cached value when env is unchanged', () => {
  process.env.UMMAYA_MEMDIR_USER = '/tmp/stable-root'
  const first = getUmmayaSessionsDir()
  const second = getUmmayaSessionsDir()
  // Referential equality — same string instance returned from cache.
  expect(first).toBe(second)
})
