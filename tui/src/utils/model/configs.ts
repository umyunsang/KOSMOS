// KOSAX Epic #2112: legacy per-provider model configs removed; single-fixed
// K-EXAONE replaces the entire CLAUDE_*_CONFIG matrix. Type and registry
// signatures preserved (ModelConfig, ALL_MODEL_CONFIGS, ModelKey, CanonicalModelId,
// CANONICAL_MODEL_IDS, CANONICAL_ID_TO_KEY) for caller import-graph.

import { KOSAX_K_EXAONE_MODEL } from './constants.js'
import type { ModelName } from './model.js'
import type { APIProvider } from './providers.js'

export type ModelConfig = Record<APIProvider, ModelName>

const KOSAX_K_EXAONE_ID = KOSAX_K_EXAONE_MODEL

export const KOSAX_K_EXAONE_CONFIG = {
  firstParty: KOSAX_K_EXAONE_ID,
  bedrock: KOSAX_K_EXAONE_ID,
  vertex: KOSAX_K_EXAONE_ID,
  foundry: KOSAX_K_EXAONE_ID,
} as const satisfies ModelConfig

export const ALL_MODEL_CONFIGS = {
  kexaone: KOSAX_K_EXAONE_CONFIG,
} as const satisfies Record<string, ModelConfig>

export type ModelKey = keyof typeof ALL_MODEL_CONFIGS

export type CanonicalModelId = (typeof ALL_MODEL_CONFIGS)[ModelKey]['firstParty']

export const CANONICAL_MODEL_IDS = Object.values(ALL_MODEL_CONFIGS).map(
  c => c.firstParty,
) as [CanonicalModelId, ...CanonicalModelId[]]

export const CANONICAL_ID_TO_KEY: Record<CanonicalModelId, ModelKey> =
  Object.fromEntries(
    (Object.entries(ALL_MODEL_CONFIGS) as [ModelKey, ModelConfig][]).map(
      ([key, cfg]) => [cfg.firstParty, key],
    ),
  ) as Record<CanonicalModelId, ModelKey>
