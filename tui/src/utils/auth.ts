// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.
//
// All Anthropic OAuth / Claude.ai / ant-internal subscriber surfaces are
// inert in KOSMOS (FriendliAI API-key auth only). Every getter returns null
// or `false`; every clearer is a no-op.

export async function getClaudeAIOAuthTokens(): Promise<null> {
  return null
}

export function isClaudeAISubscriber(): boolean {
  return false
}

export function isConsumerSubscriber(): boolean {
  return false
}

export function isMaxSubscriber(): boolean {
  return false
}

export function isProSubscriber(): boolean {
  return false
}

export function isTeamSubscriber(): boolean {
  return false
}

export function isTeamPremiumSubscriber(): boolean {
  return false
}

export function isEnterpriseSubscriber(): boolean {
  return false
}

export function isAnthropicAuthEnabled(): boolean {
  return false
}

export function is1PApiCustomer(): boolean {
  return false
}

export function isUsing3PServices(): boolean {
  return false
}

export function isOverageProvisioningAllowed(): boolean {
  return false
}

export function hasProfileScope(): boolean {
  return false
}

export function getAccountInformation(): null {
  return null
}

export function getOauthAccountInfo(): null {
  return null
}

export function getOauthOrgUUID(): null {
  return null
}

export function getSubscriptionType(): 'free' {
  return 'free'
}

export function getSubscriptionName(): string {
  return ''
}

export function getAuthTokenSource(): 'none' {
  return 'none'
}

export function getRateLimitTier(): 0 {
  return 0
}

export function getAnthropicApiKey(): null {
  return null
}

export function getAnthropicApiKeyWithSource(): { key: null; source: 'none' } {
  return { key: null, source: 'none' }
}

export function getApiKeyFromApiKeyHelper(): null {
  return null
}

export function getConfiguredApiKeyHelper(): null {
  return null
}

export function getApiKeyHelperElapsedMs(): number {
  return 0
}

export async function checkAndRefreshOAuthTokenIfNeeded(): Promise<void> {
  /* no-op */
}

export async function refreshAndGetAwsCredentials(): Promise<null> {
  return null
}

export async function prefetchAwsCredentialsAndBedRockInfoIfSafe(): Promise<void> {
  /* no-op */
}

export async function prefetchGcpCredentialsIfSafe(): Promise<void> {
  /* no-op */
}

export async function prefetchApiKeyFromApiKeyHelperIfSafe(): Promise<void> {
  /* no-op */
}

export function clearApiKeyHelperCache(): void {
  /* no-op */
}

export function clearAwsCredentialsCache(): void {
  /* no-op */
}

export function clearGcpCredentialsCache(): void {
  /* no-op */
}

export function clearOAuthTokenCache(): void {
  /* no-op */
}

export async function handleOAuth401Error(): Promise<void> {
  /* no-op */
}

export async function saveOAuthTokensIfNeeded(): Promise<void> {
  /* no-op */
}

export async function validateForceLoginOrg(): Promise<boolean> {
  return false
}

const _default = {
  getClaudeAIOAuthTokens,
  isClaudeAISubscriber,
  isConsumerSubscriber,
  isMaxSubscriber,
  isProSubscriber,
  isTeamSubscriber,
  isTeamPremiumSubscriber,
  isEnterpriseSubscriber,
  isAnthropicAuthEnabled,
  is1PApiCustomer,
  isUsing3PServices,
  isOverageProvisioningAllowed,
  hasProfileScope,
  getAccountInformation,
  getOauthAccountInfo,
  getOauthOrgUUID,
  getSubscriptionType,
  getAuthTokenSource,
  getRateLimitTier,
  getAnthropicApiKey,
  getAnthropicApiKeyWithSource,
  getApiKeyFromApiKeyHelper,
  getConfiguredApiKeyHelper,
  getApiKeyHelperElapsedMs,
  checkAndRefreshOAuthTokenIfNeeded,
  refreshAndGetAwsCredentials,
  prefetchAwsCredentialsAndBedRockInfoIfSafe,
  prefetchGcpCredentialsIfSafe,
  prefetchApiKeyFromApiKeyHelperIfSafe,
  clearApiKeyHelperCache,
  clearAwsCredentialsCache,
  clearGcpCredentialsCache,
  clearOAuthTokenCache,
  handleOAuth401Error,
  saveOAuthTokensIfNeeded,
  validateForceLoginOrg,
}

export default _default
