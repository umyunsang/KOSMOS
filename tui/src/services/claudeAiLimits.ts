// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration · Epic #2077 surface preservation.
// Research use — adapted from Claude Code 2.1.88 src/services/claudeAiLimits.ts
// permissive no-op for CC compatibility. KOSMOS has no claude.ai subscription
// quota; adapter-layer rate limiting is enforced by Spec 022 `usage_tracker`
// and the per-API `KOSMOS_*` env vars. Type aliases remain so the
// `rateLimitMessages.ts` and `mockRateLimits.ts` consumers compile.

export type ClaudeAILimits = {
  readonly tier?: string
  readonly resetAtSeconds?: number
  readonly remaining?: number
  readonly [extraField: string]: unknown
}

export type OverageDisabledReason =
  | 'kosmos_no_overage'
  | 'unknown'
  | string
