// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.
//
// Claude Code's model-cost catalog priced every Anthropic model. KOSMOS only
// invokes K-EXAONE via FriendliAI Serverless, which bills per run rather than
// per token, so cost math collapses to zero. Callers that render cost figures
// will show "$0.00" — acceptable for a student-portfolio build.

export interface CostTier {
  readonly inputPerMillion: number
  readonly outputPerMillion: number
  readonly cacheReadPerMillion: number
  readonly cacheWritePerMillion: number
}

const ZERO_TIER: CostTier = {
  inputPerMillion: 0,
  outputPerMillion: 0,
  cacheReadPerMillion: 0,
  cacheWritePerMillion: 0,
}

export const COST_HAIKU_35: CostTier = ZERO_TIER
export const COST_HAIKU_45: CostTier = ZERO_TIER
export const COST_TIER_3_15: CostTier = ZERO_TIER

export function getOpus46CostTier(): CostTier {
  return ZERO_TIER
}

export function calculateCostFromTokens(
  _inputTokens: number,
  _outputTokens: number,
  _model?: string,
): number {
  return 0
}

export function calculateUSDCost(
  _inputTokens: number,
  _outputTokens: number,
  _model?: string,
): number {
  return 0
}

export function formatModelPricing(_model: string): string {
  return '$0.00 / 1M input · $0.00 / 1M output'
}
