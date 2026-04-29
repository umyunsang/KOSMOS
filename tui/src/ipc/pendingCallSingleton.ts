// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic ζ #2297 Phase 0b · T007/T013
//
// Process-wide singleton PendingCallRegistry for TUI primitive dispatches.
//
// The registry is session-scoped by contract (data-model.md § 3), but since
// the TUI process hosts exactly one chat session at a time, a module-level
// singleton is safe and matches the bridge singleton pattern in bridgeSingleton.ts.
//
// Tests inject a fresh PendingCallRegistry directly via LLMClientOptions.pendingCallRegistry
// to avoid sharing state between test cases.

import { PendingCallRegistry } from '../tools/_shared/pendingCallRegistry.js'

let _registry: PendingCallRegistry | null = null

/**
 * Return (or lazily create) the process-wide PendingCallRegistry.
 * Called by dispatchPrimitive.ts and by the LLMClient frame consumer loop.
 */
export function getOrCreatePendingCallRegistry(): PendingCallRegistry {
  if (_registry === null) {
    _registry = new PendingCallRegistry()
  }
  return _registry
}

/**
 * Reset the singleton — used by tests and on session teardown.
 * Clears all pending calls and nulls the singleton so the next
 * getOrCreatePendingCallRegistry() returns a fresh instance.
 */
export function resetPendingCallRegistry(): void {
  if (_registry !== null) {
    _registry.clear()
    _registry = null
  }
}
