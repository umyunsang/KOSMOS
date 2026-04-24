// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 P2 · stub-noop replacement for CC GrowthBook.
//
// The original Anthropic GrowthBook feature-flag client has been removed.
// KOSMOS does not ship with feature flags in P1+P2 scope; every gate
// resolves to its "disabled" branch (false / null / default).
//
// If a future Epic reintroduces feature flags, the KOSMOS equivalent will
// be a single provider configured via KOSMOS_ env vars — not the Anthropic
// GrowthBook SDK.

// ---------------------------------------------------------------------------
// Feature value lookup — always returns the caller-supplied default.
// ---------------------------------------------------------------------------

export function getFeatureValue_CACHED_MAY_BE_STALE<T>(
  _flagName: string,
  defaultValue: T,
): T {
  return defaultValue
}

export async function getFeatureValue<T>(
  _flagName: string,
  defaultValue: T,
): Promise<T> {
  return defaultValue
}

// ---------------------------------------------------------------------------
// Boolean gate check — always returns false (closed).
// ---------------------------------------------------------------------------

export function checkGate_CACHED_OR_BLOCKING(_gateName: string): boolean {
  return false
}

export async function checkGate(_gateName: string): Promise<boolean> {
  return false
}

// ---------------------------------------------------------------------------
// Lifecycle — no-ops.
// ---------------------------------------------------------------------------

export async function initializeGrowthBook(): Promise<void> {
  // Intentional no-op.
}

export function resetGrowthBook(): void {
  // Intentional no-op.
}

export default {
  getFeatureValue,
  getFeatureValue_CACHED_MAY_BE_STALE,
  checkGate,
  checkGate_CACHED_OR_BLOCKING,
  initializeGrowthBook,
  resetGrowthBook,
}
