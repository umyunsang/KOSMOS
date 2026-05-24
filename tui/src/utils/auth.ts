import memoize from 'lodash-es/memoize.js'
import { normalizeApiKeyForConfig } from './authPortable.js'
import { getGlobalConfig, saveGlobalConfig } from './config.js'

export const FRIENDLI_PRIMARY_ENV = 'UMMAYA_FRIENDLI_TOKEN'
export const FRIENDLI_LOGIN_REQUIRED_MESSAGE =
  'Not logged in to FriendliAI. Run /login and paste a FriendliAI API key before sending a request.'

export type ApiKeySource =
  | typeof FRIENDLI_PRIMARY_ENV
  | 'ANTHROPIC_API_KEY'
  | 'apiKeyHelper'
  | '/login managed key'
  | 'none'

export type AuthTokenSource =
  | 'ANTHROPIC_AUTH_TOKEN'
  | 'CLAUDE_CODE_OAUTH_TOKEN'
  | 'apiKeyHelper'
  | 'claude.ai'
  | 'none'

function normalizeFriendliApiKey(apiKey: string): string {
  const trimmed = apiKey.trim()
  if (trimmed.length === 0) {
    throw new Error('FriendliAI API key must not be empty.')
  }
  if (/[\u0000-\u001f\u007f]/.test(trimmed)) {
    throw new Error('FriendliAI API key must be a single line.')
  }
  return trimmed
}

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

export function getAuthTokenSource(): {
  source: AuthTokenSource
  hasToken: boolean
} {
  return { source: 'none', hasToken: false }
}

export function getRateLimitTier(): 0 {
  return 0
}

export function getAnthropicApiKey(): null | string {
  return getAnthropicApiKeyWithSource().key
}

export function getAnthropicApiKeyWithSource(
  _opts: { skipRetrievingKeyFromApiKeyHelper?: boolean } = {},
): { key: null | string; source: ApiKeySource } {
  const envKey = process.env[FRIENDLI_PRIMARY_ENV]?.trim()
  if (envKey) {
    return { key: envKey, source: FRIENDLI_PRIMARY_ENV }
  }

  const saved = getApiKeyFromConfigOrMacOSKeychain()
  if (saved) {
    return { key: saved, source: '/login managed key' }
  }

  return { key: null, source: 'none' }
}

export function hasAnthropicApiKeyAuth(): boolean {
  return (
    getAnthropicApiKeyWithSource({
      skipRetrievingKeyFromApiKeyHelper: true,
    }).key !== null
  )
}

export async function saveApiKey(apiKey: string): Promise<void> {
  const normalized = normalizeFriendliApiKey(apiKey)
  process.env[FRIENDLI_PRIMARY_ENV] = normalized
  saveGlobalConfig(current => {
    const truncated = normalizeApiKeyForConfig(normalized)
    const approved = current.customApiKeyResponses?.approved ?? []
    return {
      ...current,
      primaryApiKey: normalized,
      customApiKeyResponses: {
        ...current.customApiKeyResponses,
        approved: approved.includes(truncated)
          ? approved
          : [...approved, truncated],
        rejected: current.customApiKeyResponses?.rejected ?? [],
      },
    }
  })
  getApiKeyFromConfigOrMacOSKeychain.cache?.clear?.()
}

export async function removeApiKey(): Promise<void> {
  delete process.env[FRIENDLI_PRIMARY_ENV]
  saveGlobalConfig(current => ({
    ...current,
    primaryApiKey: undefined,
  }))
  getApiKeyFromConfigOrMacOSKeychain.cache?.clear?.()
}

export function getApiKeyFromApiKeyHelper(): null {
  return null
}

export const getApiKeyFromConfigOrMacOSKeychain = memoize((): null | string => {
  const configKey = getGlobalConfig().primaryApiKey?.trim()
  return configKey && configKey.length > 0 ? configKey : null
})

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
  getApiKeyFromConfigOrMacOSKeychain.cache?.clear?.()
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

export async function validateForceLoginOrg(): Promise<{ valid: true }> {
  return { valid: true }
}

export function assertFriendliApiKeyForUse(
  env: Record<string, string | undefined> = process.env,
): string {
  const envKey = env[FRIENDLI_PRIMARY_ENV]?.trim()
  if (envKey) {
    return envKey
  }

  if (env === process.env) {
    const { key } = getAnthropicApiKeyWithSource()
    if (key) {
      env[FRIENDLI_PRIMARY_ENV] = key
      return key
    }
  }

  throw new Error(FRIENDLI_LOGIN_REQUIRED_MESSAGE)
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
  hasAnthropicApiKeyAuth,
  saveApiKey,
  removeApiKey,
  getApiKeyFromApiKeyHelper,
  getApiKeyFromConfigOrMacOSKeychain,
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
  assertFriendliApiKeyForUse,
}

export default _default
