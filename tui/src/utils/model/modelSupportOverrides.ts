// KOSMOS Epic #2112: legacy 3-tier per-model env-var overrides removed.
// KOSMOS uses a single FriendliAI Serverless deployment configured via
// KOSMOS_FRIENDLI_MODEL only. Helper signature preserved for caller import-graph.

import memoize from 'lodash-es/memoize.js'

export type ModelCapabilityOverride =
  | 'effort'
  | 'max_effort'
  | 'thinking'
  | 'adaptive_thinking'
  | 'interleaved_thinking'

export const get3PModelCapabilityOverride = memoize(
  (_model: string, _capability: ModelCapabilityOverride): boolean | undefined => undefined,
  (model, capability) => `${model.toLowerCase()}:${capability}`,
)
