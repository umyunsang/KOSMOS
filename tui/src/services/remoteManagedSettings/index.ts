// SPDX-License-Identifier: Apache-2.0
// KOSMOS-1633 — remote-managed-settings minimal stub.
//
// CC's remote-managed-settings subsystem synchronized admin policy from a
// signed Anthropic endpoint, validated it against an embedded x509 chain
// (`securityCheck.jsx`), and cached it in disk + in-memory state
// (`syncCache.js` / `syncCacheState.js`). KOSMOS does not consume that
// endpoint and admin policy is delivered via Spec 026 prompt registry +
// `prompts/manifest.yaml`.
//
// Consumers in this codebase reference `refreshRemoteManagedSettings` (login
// flow) plus a handful of lifecycle helpers; we expose stable no-op
// surfaces for the symbols they import without dragging in axios / OAuth
// helpers / Anthropic API key resolution. The shape stays sync-compatible
// with the original module so callers do not need to be edited.

import type { SettingsJson } from '../../utils/settings/types.js'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type RemoteManagedSettings = SettingsJson

const EMPTY_REMOTE_MANAGED_SETTINGS = Object.freeze({}) as RemoteManagedSettings

// ---------------------------------------------------------------------------
// Lifecycle promises (login.tsx + bootstrap consumers)
// ---------------------------------------------------------------------------

let loadingPromise: Promise<void> | null = null

export function initializeRemoteManagedSettingsLoadingPromise(): void {
  // KOSMOS does not fetch anything — resolve immediately so any awaiter
  // proceeds without blocking startup.
  loadingPromise = Promise.resolve()
}

export async function waitForRemoteManagedSettingsToLoad(): Promise<void> {
  if (loadingPromise === null) {
    initializeRemoteManagedSettingsLoadingPromise()
  }
  return loadingPromise!
}

// ---------------------------------------------------------------------------
// Cache + checksum helpers (kept for shape compatibility)
// ---------------------------------------------------------------------------

export function computeChecksumFromSettings(_settings: SettingsJson): string {
  return ''
}

export function isEligibleForRemoteManagedSettings(): boolean {
  return false
}

export async function clearRemoteManagedSettingsCache(): Promise<void> {
  // no-op — there is no cache.
}

// ---------------------------------------------------------------------------
// Refresh entrypoints (login.tsx is the primary caller)
// ---------------------------------------------------------------------------

export async function loadRemoteManagedSettings(): Promise<void> {
  // no-op — KOSMOS reads admin policy from prompts/manifest.yaml at boot
  // (Spec 026), not from a remote endpoint.
}

export async function refreshRemoteManagedSettings(): Promise<void> {
  // no-op — see loadRemoteManagedSettings.
}

// ---------------------------------------------------------------------------
// Background polling (preserved as no-op so bootstrap teardown is safe)
// ---------------------------------------------------------------------------

export function startBackgroundPolling(): void {
  // no-op
}

export function stopBackgroundPolling(): void {
  // no-op
}

// ---------------------------------------------------------------------------
// Read-only accessors
// ---------------------------------------------------------------------------

export function getRemoteManagedSettings(): RemoteManagedSettings {
  return EMPTY_REMOTE_MANAGED_SETTINGS
}

export function isRemoteManagedSettingsEnabled(): boolean {
  return false
}

export function subscribeRemoteManagedSettings(
  _listener: (settings: RemoteManagedSettings) => void,
): () => void {
  return () => {}
}
