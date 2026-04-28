// KOSMOS Epic #2112: legacy first-party base-URL check rewritten for FriendliAI.
// All callers updated to `isFirstPartyKosmosBaseUrl` (see grep history pre-Spec
// 2112 for the legacy alias name).

import type { AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS } from '../../services/analytics/index.js'
import { isEnvTruthy } from '../envUtils.js'

export type APIProvider = 'firstParty' | 'bedrock' | 'vertex' | 'foundry'

export function getAPIProvider(): APIProvider {
  return isEnvTruthy(process.env.CLAUDE_CODE_USE_BEDROCK)
    ? 'bedrock'
    : isEnvTruthy(process.env.CLAUDE_CODE_USE_VERTEX)
      ? 'vertex'
      : isEnvTruthy(process.env.CLAUDE_CODE_USE_FOUNDRY)
        ? 'foundry'
        : 'firstParty'
}

export function getAPIProviderForStatsig(): AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS {
  return getAPIProvider() as AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS
}

/**
 * Check if KOSMOS_FRIENDLI_BASE_URL points to FriendliAI Serverless.
 * Returns true if not set (default endpoint) or points to api.friendli.ai.
 */
export function isFirstPartyKosmosBaseUrl(): boolean {
  const baseUrl = process.env.KOSMOS_FRIENDLI_BASE_URL
  if (!baseUrl) {
    return true
  }
  try {
    const host = new URL(baseUrl).host
    return host === 'api.friendli.ai'
  } catch {
    return false
  }
}

