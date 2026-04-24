// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.
//
// Claude Code's macOS Keychain / Linux libsecret-backed secure storage has no
// counterpart in KOSMOS (LLM credentials live exclusively in the
// FRIENDLI_API_KEY environment variable). The stub exposes an in-memory
// placeholder so callers compile; every getter returns null.

import type { SecureStorageData } from './types.js'

interface SecureStorageApi {
  get(_key: string): Promise<SecureStorageData | null>
  set(_key: string, _value: string): Promise<void>
  delete(_key: string): Promise<void>
}

export function getSecureStorage(): SecureStorageApi {
  return {
    async get() {
      return null
    },
    async set() {
      /* no-op */
    },
    async delete() {
      /* no-op */
    },
  }
}
