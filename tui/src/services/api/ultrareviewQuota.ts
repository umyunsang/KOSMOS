import axios from 'axios'
// constants/oauth removed in P1+P2 (Spec 1633); KOSMOS uses FriendliAI, not Anthropic OAuth.
const getOauthConfig = (): { authorizationUrl: string; tokenUrl: string; clientId: string; scopes: readonly string[]; BASE_API_URL: string } => ({ authorizationUrl: '', tokenUrl: '', clientId: '', scopes: [] as readonly string[], BASE_API_URL: '' })
import { isClaudeAISubscriber } from '../../utils/auth.js'
import { logForDebugging } from '../../utils/debug.js'
import { getOAuthHeaders, prepareApiRequest } from '../../utils/teleport/api.js'

export type UltrareviewQuotaResponse = {
  reviews_used: number
  reviews_limit: number
  reviews_remaining: number
  is_overage: boolean
}

/**
 * Peek the ultrareview quota for display and nudge decisions. Consume
 * happens server-side at session creation. Null when not a subscriber or
 * the endpoint errors.
 */
export async function fetchUltrareviewQuota(): Promise<UltrareviewQuotaResponse | null> {
  if (!isClaudeAISubscriber()) return null
  try {
    const { accessToken, orgUUID } = await prepareApiRequest()
    const response = await axios.get<UltrareviewQuotaResponse>(
      `${getOauthConfig().BASE_API_URL}/v1/ultrareview/quota`,
      {
        headers: {
          ...getOAuthHeaders(accessToken),
          'x-organization-uuid': orgUUID,
        },
        timeout: 5000,
      },
    )
    return response.data
  } catch (error) {
    logForDebugging(`fetchUltrareviewQuota failed: ${error}`)
    return null
  }
}
