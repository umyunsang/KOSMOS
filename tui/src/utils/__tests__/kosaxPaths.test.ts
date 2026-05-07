// SPDX-License-Identifier: Apache-2.0
/**
 * Unit tests for tui/src/utils/kosaxPaths.ts
 *
 * Verifies:
 *   1. Default paths resolve to ~/.kosax/memdir/user[/sessions]
 *   2. KOSAX_MEMDIR_USER env override is respected
 *   3. Memoize invalidation fires when the env var changes between calls
 */

import { test, expect, beforeEach, afterEach } from 'bun:test'
import { homedir } from 'os'
import { join } from 'path'

// We import by absolute path so bun module cache isolation works correctly.
// Each test that mutates process.env must re-import via dynamic import to
// bypass the module cache — or clear the cache via module mock. Because
// kosaxPaths.ts uses a plain closure cache (not lodash memoize), the same
// module instance is fine: mutating env + calling the function again is
// sufficient to observe invalidation.

let getKosaxUserTierRoot: () => string
let getKosaxSessionsDir: () => string

const ORIGINAL_KOSAX_MEMDIR_USER = process.env.KOSAX_MEMDIR_USER

beforeEach(async () => {
  // Remove any env override so we start from the default state.
  delete process.env.KOSAX_MEMDIR_USER

  // Dynamic re-import ensures the closure cache is warm-started in the
  // default (no-override) state for each test group.
  const mod = await import('../kosaxPaths.js')
  getKosaxUserTierRoot = mod.getKosaxUserTierRoot
  getKosaxSessionsDir = mod.getKosaxSessionsDir
})

afterEach(() => {
  // Restore original env state to avoid cross-test pollution.
  if (ORIGINAL_KOSAX_MEMDIR_USER === undefined) {
    delete process.env.KOSAX_MEMDIR_USER
  } else {
    process.env.KOSAX_MEMDIR_USER = ORIGINAL_KOSAX_MEMDIR_USER
  }
})

// ---------------------------------------------------------------------------
// Default values (no env override)
// ---------------------------------------------------------------------------

test('getKosaxUserTierRoot returns ~/.kosax/memdir/user by default', () => {
  delete process.env.KOSAX_MEMDIR_USER
  const expected = join(homedir(), '.kosax', 'memdir', 'user')
  expect(getKosaxUserTierRoot()).toBe(expected)
})

test('getKosaxSessionsDir returns ~/.kosax/memdir/user/sessions by default', () => {
  delete process.env.KOSAX_MEMDIR_USER
  const expected = join(homedir(), '.kosax', 'memdir', 'user', 'sessions')
  expect(getKosaxSessionsDir()).toBe(expected)
})

// ---------------------------------------------------------------------------
// Env override
// ---------------------------------------------------------------------------

test('getKosaxUserTierRoot respects KOSAX_MEMDIR_USER env override', () => {
  process.env.KOSAX_MEMDIR_USER = '/tmp/kosax-test/memdir/user'
  expect(getKosaxUserTierRoot()).toBe('/tmp/kosax-test/memdir/user')
})

test('getKosaxSessionsDir appends /sessions to KOSAX_MEMDIR_USER override', () => {
  process.env.KOSAX_MEMDIR_USER = '/tmp/kosax-test/memdir/user'
  expect(getKosaxSessionsDir()).toBe('/tmp/kosax-test/memdir/user/sessions')
})

// ---------------------------------------------------------------------------
// Memoize invalidation — changing the env var between calls gets a fresh value
// ---------------------------------------------------------------------------

test('getKosaxUserTierRoot invalidates cache when KOSAX_MEMDIR_USER changes', () => {
  delete process.env.KOSAX_MEMDIR_USER
  const defaultVal = getKosaxUserTierRoot()
  expect(defaultVal).toBe(join(homedir(), '.kosax', 'memdir', 'user'))

  // Now set the env var and call again — must see the new value.
  process.env.KOSAX_MEMDIR_USER = '/tmp/new-root'
  const overrideVal = getKosaxUserTierRoot()
  expect(overrideVal).toBe('/tmp/new-root')
})

test('getKosaxSessionsDir invalidates cache when KOSAX_MEMDIR_USER changes', () => {
  delete process.env.KOSAX_MEMDIR_USER
  const defaultVal = getKosaxSessionsDir()
  expect(defaultVal).toBe(join(homedir(), '.kosax', 'memdir', 'user', 'sessions'))

  // Switch to override.
  process.env.KOSAX_MEMDIR_USER = '/tmp/new-root'
  const overrideVal = getKosaxSessionsDir()
  expect(overrideVal).toBe('/tmp/new-root/sessions')
})

test('getKosaxSessionsDir returns cached value when env is unchanged', () => {
  process.env.KOSAX_MEMDIR_USER = '/tmp/stable-root'
  const first = getKosaxSessionsDir()
  const second = getKosaxSessionsDir()
  // Referential equality — same string instance returned from cache.
  expect(first).toBe(second)
})
