// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.
//
// Anthropic OAuth constants were deleted in Epic #1633 (KOSMOS authenticates
// only via FRIENDLI_API_KEY, never via OAuth). Consumers still reference these
// symbols, so we re-export empty strings / inert config — guards around them
// must fail closed because scopes are empty.

export const CLAUDE_AI_INFERENCE_SCOPE = ''
export const CLAUDE_AI_PROFILE_SCOPE = ''
export const MCP_CLIENT_METADATA_URL = ''
export const OAUTH_BETA_HEADER = ''

export function fileSuffixForOauthConfig(): string {
  return ''
}

interface OauthConfigShape {
  readonly BASE_API_URL: string
  readonly CLIENT_ID: string
  readonly AUTHORIZE_URL: string
  readonly TOKEN_URL: string
  readonly REVOKE_URL: string
  readonly SUCCESS_URL: string
}

// FriendliAI base URL — used by several legacy call sites that still hit
// `${getOauthConfig().BASE_API_URL}/v1/...` directly. Most of those paths are
// now dead (bridge/session/grove endpoints reach Anthropic-only routes), but
// returning a non-null object avoids TypeError crashes during boot.
const KOSMOS_OAUTH_CONFIG: OauthConfigShape = {
  BASE_API_URL: 'https://api.friendli.ai/serverless',
  CLIENT_ID: '',
  AUTHORIZE_URL: '',
  TOKEN_URL: '',
  REVOKE_URL: '',
  SUCCESS_URL: '',
}

export function getOauthConfig(): OauthConfigShape {
  return KOSMOS_OAUTH_CONFIG
}
