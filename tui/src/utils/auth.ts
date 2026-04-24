// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 P2 · stub-noop replacement for CC auth.
//
// The Anthropic OAuth / Claude-ai / ant-internal subscriber surface has been
// removed. KOSMOS authentication is API-key based and lives entirely in the
// Python backend (KOSMOS_FRIENDLI_TOKEN / FRIENDLI_API_KEY environment
// variable). The TUI never handles credentials directly.
//
// This file preserves the original export names so existing callers
// (bridge/, tools/, interactiveHelpers, etc.) compile. Every function
// resolves to the "unauthenticated / not-an-ant" branch at runtime, which
// is the correct closed-state answer for a citizen-facing TUI.

/**
 * Returns OAuth tokens for the legacy Anthropic Claude.ai subscription.
 * KOSMOS has no OAuth surface — always null.
 */
export async function getClaudeAIOAuthTokens(): Promise<null> {
  return null
}

/**
 * True if the current user has a Claude.ai (consumer) subscription.
 * KOSMOS has no such concept — always false.
 */
export function isClaudeAISubscriber(): boolean {
  return false
}

/**
 * True if the caller routes through a third-party (3P) LLM service
 * (in CC this included Bedrock / Vertex / Nova). KOSMOS has one provider
 * (FriendliAI) and treats it as first-party to KOSMOS, so this returns
 * false.
 */
export function isUsing3PServices(): boolean {
  return false
}

/**
 * Clears the Anthropic `apiKeyHelper` cached credentials. KOSMOS does not
 * cache credentials in the TUI process — no-op.
 */
export function clearApiKeyHelperCache(): void {
  // Intentional no-op.
}

/**
 * Optionally pre-fetches an API key via the CC `apiKeyHelper` hook. KOSMOS
 * has no such hook — no-op.
 */
export async function prefetchApiKeyFromApiKeyHelperIfSafe(): Promise<void> {
  // Intentional no-op.
}

/**
 * Returns the account identifier associated with the active OAuth token.
 * KOSMOS has no OAuth surface — always null.
 */
export function getOauthAccountInfo(): null {
  return null
}

/**
 * Returns the organization UUID associated with the active OAuth token.
 * KOSMOS has no OAuth surface — always null.
 */
export function getOauthOrgUUID(): null {
  return null
}

/**
 * Returns true if the active OAuth token has enterprise scope. KOSMOS has
 * no OAuth surface — always false.
 */
export function isEnterpriseSubscriber(): boolean {
  return false
}

/**
 * Returns true if the active subscription includes "Max" tier features.
 * KOSMOS has no subscription concept — always false.
 */
export function isMaxSubscriber(): boolean {
  return false
}

/**
 * Returns true if the active subscription includes "Team Premium" tier
 * features. KOSMOS has no subscription concept — always false.
 */
export function isTeamPremiumSubscriber(): boolean {
  return false
}

export default {
  getClaudeAIOAuthTokens,
  isClaudeAISubscriber,
  isUsing3PServices,
  clearApiKeyHelperCache,
  prefetchApiKeyFromApiKeyHelperIfSafe,
  getOauthAccountInfo,
  getOauthOrgUUID,
  isEnterpriseSubscriber,
  isMaxSubscriber,
  isTeamPremiumSubscriber,
}
