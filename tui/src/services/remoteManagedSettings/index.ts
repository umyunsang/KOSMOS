// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.
//
// Claude Code's remote-managed-settings service (enterprise settings pushed
// from console.anthropic.com) has no counterpart in KOSMOS. Deleted by Epic
// #1633; restored here as a no-op stub for the import graph.

let promise: Promise<void> | null = null

export function initializeRemoteManagedSettingsLoadingPromise(): void {
  if (promise === null) {
    promise = Promise.resolve()
  }
}

export async function waitForRemoteManagedSettingsToLoad(): Promise<void> {
  if (promise === null) {
    initializeRemoteManagedSettingsLoadingPromise()
  }
  await promise
}

export function isEligibleForRemoteManagedSettings(): boolean {
  return false
}

export async function loadRemoteManagedSettings(): Promise<void> {
  /* no-op */
}

export async function refreshRemoteManagedSettings(): Promise<void> {
  /* no-op */
}
