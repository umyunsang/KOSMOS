// SPDX-License-Identifier: Apache-2.0
/**
 * KOSAX canonical path helpers.
 *
 * Provides the single source-of-truth for KOSAX memdir USER-tier paths used
 * across the TUI layer. Follows the env-key memoize pattern of envUtils.ts
 * (getClaudeConfigHomeDir) but implemented without lodash — a plain closure
 * cache keyed off the current KOSAX_MEMDIR_USER env value so that tests
 * which mutate process.env get a fresh value without clearing an external
 * cache manually.
 *
 * Spec: Initiative #2290 / AGENTS.md § L1-A A5 — sessions at
 *       ~/.kosax/memdir/user/sessions/ (JSONL, per Spec 027).
 */

import { homedir } from 'os'
import { join } from 'path'

// ---------------------------------------------------------------------------
// Internal memoize state (env-key invalidated, no lodash)
// ---------------------------------------------------------------------------

let _cachedUserTierRoot: string | undefined
let _cachedUserTierRootKey: string | undefined

let _cachedSessionsDir: string | undefined
let _cachedSessionsDirKey: string | undefined

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Returns the KOSAX memdir USER-tier root directory.
 *
 * Respects `KOSAX_MEMDIR_USER` env var; falls back to
 * `~/.kosax/memdir/user`. Result is memoized and invalidated automatically
 * when the env var changes between calls (test-friendly).
 */
export function getKosaxUserTierRoot(): string {
  const key = process.env.KOSAX_MEMDIR_USER ?? ''
  if (_cachedUserTierRoot !== undefined && _cachedUserTierRootKey === key) {
    return _cachedUserTierRoot
  }
  const value =
    process.env.KOSAX_MEMDIR_USER ?? join(homedir(), '.kosax', 'memdir', 'user')
  _cachedUserTierRoot = value
  _cachedUserTierRootKey = key
  return value
}

/**
 * Returns the canonical KOSAX sessions directory.
 *
 * This is the KOSAX-native path (`~/.kosax/memdir/user/sessions/`) as
 * opposed to the CC-legacy path (`~/.claude/projects/…`). Session JSONL
 * files are written here per Spec 027.
 *
 * Respects `KOSAX_MEMDIR_USER` env var. Result is memoized and invalidated
 * when the env var changes between calls.
 */
export function getKosaxSessionsDir(): string {
  const key = process.env.KOSAX_MEMDIR_USER ?? ''
  if (_cachedSessionsDir !== undefined && _cachedSessionsDirKey === key) {
    return _cachedSessionsDir
  }
  const value = join(getKosaxUserTierRoot(), 'sessions')
  _cachedSessionsDir = value
  _cachedSessionsDirKey = key
  return value
}
