// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — Epic #1633 T011 env credential helper.
//
// UMMAYA now boots without a FriendliAI credential so /login can collect a
// process-scoped API key. The model/tool loop still fails closed before first
// backend use when no key is present.
//
// Intentionally Node/Bun-stdlib only: no imports from ipc/, bridge/, or
// LLM layers — this runs *before* anything else in main().

import {
  FRIENDLI_PRIMARY_ENV,
  hasAnthropicApiKeyAuth,
} from '../utils/auth.js'

export const ENV_GUARD_MESSAGE =
  'FriendliAI API key not configured yet. Start UMMAYA and run /login before sending a request.'

/**
 * Check whether the current process has a FriendliAI API key. UMMAYA keeps the
 * CC auth surface, so an environment key and a /login-managed config key are
 * both valid sources.
 */
export function hasFriendliCredential(
  env: Record<string, string | undefined> = process.env,
): boolean {
  if (env[FRIENDLI_PRIMARY_ENV]?.trim()) {
    return true
  }
  return env === process.env ? hasAnthropicApiKeyAuth() : false
}

/**
 * Warns when no FriendliAI credential is present. Boot continues so the
 * citizen can run /login; query/deps.ts enforces the actual fail-closed gate.
 *
 * The second argument is injection seams for tests — production callers
 * should invoke with no arguments so the real `process.env` and `console.error`
 * are used.
 */
export function warnIfMissingFriendliCredential(
  env: Record<string, string | undefined> = process.env,
  hooks: {
    writeError?: (msg: string) => void
  } = {},
): void {
  if (hasFriendliCredential(env)) {
    return
  }

  const writeError = hooks.writeError ?? ((msg: string) => console.error(msg))
  writeError(ENV_GUARD_MESSAGE)
}

/**
 * Backward-compatible wrapper for older imports. It no longer exits at boot;
 * the hard auth gate lives at first model/backend use.
 */
export function enforceFriendliCredential(
  env: Record<string, string | undefined> = process.env,
  hooks: {
    writeError?: (msg: string) => void
    exit?: (code: number) => never
  } = {},
): void {
  void hooks.exit
  warnIfMissingFriendliCredential(env, hooks)
}
