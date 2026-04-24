// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.
//
// Claude Code's Anthropic-backed policy-limits service (enterprise allow/deny
// list fetched from console.anthropic.com) has no counterpart in KOSMOS.
// Epic #1633 deleted the real implementation, but several consumers
// (entrypoints/init.ts, entrypoints/cli.tsx, bridge/initReplBridge.ts,
// commands/*, components/*) still import from this path. A no-op stub keeps
// the import graph intact while making every policy query permissive.

type _PolicyKey = string

let policyLimitsPromise: Promise<void> | null = null

export function initializePolicyLimitsLoadingPromise(): void {
  if (policyLimitsPromise === null) {
    policyLimitsPromise = Promise.resolve()
  }
}

export async function waitForPolicyLimitsToLoad(): Promise<void> {
  if (policyLimitsPromise === null) {
    initializePolicyLimitsLoadingPromise()
  }
  await policyLimitsPromise
}

export function isPolicyAllowed(_key: _PolicyKey): boolean {
  return true
}

export function isPolicyLimitsEligible(): boolean {
  return false
}
