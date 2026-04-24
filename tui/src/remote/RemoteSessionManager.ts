// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.

export interface RemoteSessionConfig {
  readonly sessionId?: string
}

export interface RemotePermissionResponse {
  readonly allow: boolean
}

export class RemoteSessionManager {
  constructor(_config?: RemoteSessionConfig) {
    /* no-op */
  }
  async start(): Promise<void> {
    /* no-op */
  }
  async stop(): Promise<void> {
    /* no-op */
  }
}
