// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 P2 · stub-noop replacement for CC OAuth client.
//
// The original Anthropic OAuth client (authorization-code flow, PKCE, token
// exchange) has been removed. KOSMOS does not ship an OAuth surface in the
// TUI — authentication is `FRIENDLI_API_KEY` env-var only, consumed by the
// Python backend.

/**
 * Returns the organization UUID for the current OAuth session. KOSMOS has
 * no OAuth surface — always null.
 */
export function getOrganizationUUID(): string | null {
  return null
}

/**
 * Returns the user UUID for the current OAuth session. KOSMOS has no OAuth
 * surface — always null.
 */
export function getUserUUID(): string | null {
  return null
}

/**
 * Returns the active OAuth access token. KOSMOS has no OAuth surface —
 * always null.
 */
export function getAccessToken(): string | null {
  return null
}

/**
 * Refreshes the OAuth access token. KOSMOS has no OAuth surface — no-op.
 */
export async function refreshAccessToken(): Promise<null> {
  return null
}

/**
 * Revokes the OAuth access token. KOSMOS has no OAuth surface — no-op.
 */
export async function revokeAccessToken(): Promise<void> {
  // Intentional no-op.
}

export async function createAndStoreApiKey(): Promise<null> {
  return null
}

export async function fetchAndStoreUserRoles(): Promise<void> {
  /* no-op */
}

export async function populateOAuthAccountInfoIfNeeded(): Promise<void> {
  /* no-op */
}

export async function refreshOAuthToken(): Promise<null> {
  return null
}

export function shouldUseClaudeAIAuth(): boolean {
  return false
}

export async function storeOAuthAccountInfo(): Promise<void> {
  /* no-op */
}

/**
 * Lifted from CC restored-src services/oauth/client.ts:344 (verbatim, CC 2.1.88,
 * research-use). Imported by services/analytics/firstPartyEventLoggingExporter.ts.
 *
 * Returns true if the OAuth access token expires within the next 5 minutes.
 * KOSMOS has no OAuth surface — every getter in this file returns null — so
 * `expiresAt` is always null at runtime and this returns false. Function shape
 * preserved per Constitution §I CC fidelity rule.
 */
export function isOAuthTokenExpired(expiresAt: number | null): boolean {
  if (expiresAt === null) {
    return false
  }

  const bufferTime = 5 * 60 * 1000
  const now = Date.now()
  const expiresWithBuffer = now + bufferTime
  return expiresWithBuffer >= expiresAt
}

export default {
  getOrganizationUUID,
  getUserUUID,
  getAccessToken,
  refreshAccessToken,
  revokeAccessToken,
  createAndStoreApiKey,
  fetchAndStoreUserRoles,
  populateOAuthAccountInfoIfNeeded,
  refreshOAuthToken,
  shouldUseClaudeAIAuth,
  storeOAuthAccountInfo,
}
