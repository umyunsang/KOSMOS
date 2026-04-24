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

export default {
  getOrganizationUUID,
  getUserUUID,
  getAccessToken,
  refreshAccessToken,
  revokeAccessToken,
}
