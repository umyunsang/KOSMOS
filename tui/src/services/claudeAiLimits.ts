// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.

export interface ClaudeAILimits {
  readonly remaining: number
  readonly limit: number
  readonly resetAt: number
}

export type OverageDisabledReason = 'quota' | 'policy' | 'none'

const EMPTY_LIMITS: ClaudeAILimits = {
  remaining: Number.POSITIVE_INFINITY,
  limit: Number.POSITIVE_INFINITY,
  resetAt: 0,
}

export const currentLimits: ClaudeAILimits = EMPTY_LIMITS
// Callers expect a Set — use `add`/`delete` interfaces. KOSMOS never fires
// listeners since FriendliAI has no claude.ai-style subscription rate limit.
export const statusListeners: Set<(l: ClaudeAILimits) => void> = new Set()

export function getRateLimitWarning(): string | null {
  return null
}

export function getRawUtilization(): ClaudeAILimits {
  return EMPTY_LIMITS
}

export function getUsingOverageText(): string {
  return ''
}
