// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.
import type { ClaudeAILimits } from './claudeAiLimits.js'

export function useClaudeAiLimits(): ClaudeAILimits {
  return {
    remaining: Number.POSITIVE_INFINITY,
    limit: Number.POSITIVE_INFINITY,
    resetAt: 0,
  }
}
