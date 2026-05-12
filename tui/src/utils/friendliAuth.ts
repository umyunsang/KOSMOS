// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — FriendliAI API-key auth with persisted session recovery.
//
// Mirrors Claude Code's login/logout lifecycle shape, but UMMAYA does not use
// OAuth, keychain, or config-file persistence. A /login token is written to the
// user-memdir once and reloaded across app launches, then restored into the
// process env for the active session. /logout clears both the process env and the
// persisted copy.

import {
  closeSync,
  fsyncSync,
  mkdirSync,
  openSync,
  readFileSync,
  renameSync,
  unlinkSync,
  writeSync,
} from 'node:fs'
import { dirname, join } from 'node:path'
import { getUmmayaUserTierRoot } from './ummayaPaths.js'

export const FRIENDLI_PRIMARY_ENV = 'UMMAYA_FRIENDLI_TOKEN'
export const FRIENDLI_SESSION_ENV = 'UMMAYA_FRIENDLI_SESSION_ACTIVE'
const FRIENDLI_CREDENTIAL_DIR = 'friendli'
const FRIENDLI_CREDENTIAL_FILE = 'session.json'
const FRIENDLI_CREDENTIAL_VERSION = 1

type FriendliCredentialStorageOptions = {
  persist?: boolean
}

export type FriendliCredentialSource =
  | typeof FRIENDLI_PRIMARY_ENV
  | 'none'

export const FRIENDLI_LOGIN_REQUIRED_MESSAGE =
  'Not logged in to FriendliAI. Run /login and paste a FriendliAI API key before sending a request.'

function getFriendliCredentialStoragePath(): string {
  return join(getUmmayaUserTierRoot(), 'credentials', FRIENDLI_CREDENTIAL_DIR, FRIENDLI_CREDENTIAL_FILE)
}

function getPersistedFriendliCredential(): string | null {
  const path = getFriendliCredentialStoragePath()
  try {
    const raw = readFileSync(path, 'utf8').trim()
    if (!raw) {
      return null
    }

    try {
      const parsed = JSON.parse(raw)
      if (
        parsed !== null &&
        typeof parsed === 'object' &&
        typeof parsed.token === 'string'
      ) {
        const token = parsed.token.trim()
        return token.length > 0 ? token : null
      }
    } catch {
      return raw.length > 0 ? raw : null
    }
  } catch {
    return null
  }

  return null
}

function persistFriendliCredential(token: string): void {
  const payload = JSON.stringify({
    v: FRIENDLI_CREDENTIAL_VERSION,
    token,
    updatedAt: new Date().toISOString(),
  })
  const path = getFriendliCredentialStoragePath()
  const dir = dirname(path)
  mkdirSync(dir, { recursive: true, mode: 0o700 })
  const tmp = `${path}.tmp`
  const fd = openSync(tmp, 'w', 0o600)
  try {
    writeSync(fd, payload)
    fsyncSync(fd)
  } finally {
    closeSync(fd)
  }
  renameSync(tmp, path)
}

function clearPersistedFriendliCredential(): void {
  const path = getFriendliCredentialStoragePath()
  try {
    unlinkSync(path)
  } catch {
    // If the file doesn't exist, nothing to clear.
  }
}

export function normalizeFriendliApiKey(value: string): string {
  const trimmed = value.trim()
  if (trimmed.length === 0) {
    throw new Error('FriendliAI API key must not be empty.')
  }
  return trimmed
}

export function getFriendliCredentialSource(
  env: Record<string, string | undefined> = process.env,
): FriendliCredentialSource {
  if (env[FRIENDLI_SESSION_ENV] !== '1') {
    return 'none'
  }

  const primary = env[FRIENDLI_PRIMARY_ENV]
  if (primary && primary.trim().length > 0) {
    return FRIENDLI_PRIMARY_ENV
  }

  return 'none'
}

export function hasFriendliCredential(
  env: Record<string, string | undefined> = process.env,
): boolean {
  return getFriendliCredentialSource(env) !== 'none'
}

export function bootstrapFriendliCredentialFromStorage(
  env: Record<string, string | undefined> = process.env,
): void {
  if (getFriendliCredentialSource(env) !== 'none') {
    return
  }

  const stored = getPersistedFriendliCredential()
  if (!stored) {
    return
  }

  try {
    installFriendliCredential(stored, env, { persist: false })
  } catch (_error) {
    clearPersistedFriendliCredential()
  }
}

export function installFriendliCredential(
  apiKey: string,
  env: Record<string, string | undefined> = process.env,
  options: FriendliCredentialStorageOptions = {},
): void {
  const normalized = normalizeFriendliApiKey(apiKey)
  env[FRIENDLI_PRIMARY_ENV] = normalized
  env[FRIENDLI_SESSION_ENV] = '1'
  if (options.persist !== false) {
    persistFriendliCredential(normalized)
  }
}

export function clearFriendliCredential(
  env: Record<string, string | undefined> = process.env,
  options: FriendliCredentialStorageOptions = {},
): void {
  delete env[FRIENDLI_PRIMARY_ENV]
  delete env[FRIENDLI_SESSION_ENV]
  if (options.persist !== false) {
    clearPersistedFriendliCredential()
  }
}

export function assertFriendliCredentialForUse(
  env: Record<string, string | undefined> = process.env,
): void {
  if (!hasFriendliCredential(env)) {
    throw new Error(FRIENDLI_LOGIN_REQUIRED_MESSAGE)
  }
}
