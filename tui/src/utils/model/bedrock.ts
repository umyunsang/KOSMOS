// KOSMOS Epic #2112: AWS Bedrock provider integration is dead under the
// single-fixed FriendliAI invariant. All exports preserved as no-op stubs for
// caller import-graph stability (modelStrings.ts, agent.ts).

import memoize from 'lodash-es/memoize.js'

export const getBedrockInferenceProfiles = memoize(
  async function (): Promise<string[]> {
    return []
  },
)

export function findFirstMatch(profiles: string[], substring: string): string | null {
  return profiles.find(p => p.includes(substring)) ?? null
}

/**
 * Extract a cross-region inference prefix (e.g. "eu.", "us.") from a Bedrock
 * model ID, or null if none is present. KOSMOS does not target Bedrock, so this
 * always returns null — the caller in agent.ts will then skip prefix carry-over.
 */
export function getBedrockRegionPrefix(_model: string): string | null {
  return null
}

/**
 * Apply a region prefix to a Bedrock model ID. KOSMOS no-op — returns the model
 * unchanged.
 */
export function applyBedrockRegionPrefix(model: string, _prefix: string): string {
  return model
}

/**
 * Detect whether a model ID is a Bedrock-foundation-model identifier (as opposed
 * to a cross-region inference profile or a custom deployment ARN). KOSMOS does
 * not target Bedrock — preserved as a no-op stub for tokenEstimation.ts caller.
 */
export function isFoundationModel(model: string): string | null {
  return model
}

/**
 * Bedrock runtime client factory. KOSMOS does not target Bedrock — call sites
 * (tokenEstimation.ts) wrap this in try/catch; throwing here keeps their fallback
 * path (null token count) intact without dragging the Bedrock dead-code into the
 * P1 deletion perimeter.
 */
export async function createBedrockRuntimeClient(): Promise<never> {
  throw new Error('KOSMOS Epic #2112: Bedrock runtime client is not available — KOSMOS uses FriendliAI Serverless.')
}

/**
 * Resolve the foundation model ID backing a Bedrock inference profile ARN.
 * KOSMOS-unused; returns null so tokenEstimation.ts falls through to the fallback.
 */
export async function getInferenceProfileBackingModel(_arn: string): Promise<string | null> {
  return null
}
