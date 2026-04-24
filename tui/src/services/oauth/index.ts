// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 P2 · stub-noop replacement for CC OAuth barrel.

export * from './client.js'

export class OAuthService {
  async login(): Promise<null> {
    return null
  }
  async logout(): Promise<void> {
    /* no-op */
  }
  async refresh(): Promise<null> {
    return null
  }
  isAuthenticated(): boolean {
    return false
  }
}
