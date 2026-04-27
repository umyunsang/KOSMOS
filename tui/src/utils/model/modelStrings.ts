// KOSMOS Epic #2112: provider-specific model-string lookup collapsed to a single
// K-EXAONE entry. Bedrock inference-profile fetching is dead (no-op stub in
// bedrock.ts). resolveOverriddenModel preserved for settings-driven overrides.

import {
  getModelStrings as getModelStringsState,
  setModelStrings as setModelStringsState,
} from 'src/bootstrap/state.js'
import { logError } from '../log.js'
import { getInitialSettings } from '../settings/settings.js'
import { ALL_MODEL_CONFIGS, CANONICAL_ID_TO_KEY, type CanonicalModelId, type ModelKey } from './configs.js'
import { type APIProvider, getAPIProvider } from './providers.js'

export type ModelStrings = Record<ModelKey, string>

const MODEL_KEYS = Object.keys(ALL_MODEL_CONFIGS) as ModelKey[]

function getBuiltinModelStrings(provider: APIProvider): ModelStrings {
  const out = {} as ModelStrings
  for (const key of MODEL_KEYS) {
    out[key] = ALL_MODEL_CONFIGS[key][provider]
  }
  return out
}

/**
 * Layer user-configured modelOverrides on top of the provider-derived strings.
 * Keys are canonical first-party model IDs (KOSMOS: only `kexaone`).
 */
function applyModelOverrides(ms: ModelStrings): ModelStrings {
  const overrides = getInitialSettings().modelOverrides
  if (!overrides) {
    return ms
  }
  const out = { ...ms }
  for (const [canonicalId, override] of Object.entries(overrides)) {
    const key = CANONICAL_ID_TO_KEY[canonicalId as CanonicalModelId]
    if (key && override) {
      out[key] = override
    }
  }
  return out
}

export function resolveOverriddenModel(modelId: string): string {
  let overrides: Record<string, string> | undefined
  try {
    overrides = getInitialSettings().modelOverrides
  } catch {
    return modelId
  }
  if (!overrides) {
    return modelId
  }
  for (const [canonicalId, override] of Object.entries(overrides)) {
    if (override === modelId) {
      return canonicalId
    }
  }
  return modelId
}

function initModelStrings(): void {
  const ms = getModelStringsState()
  if (ms !== null) {
    return
  }
  try {
    setModelStringsState(getBuiltinModelStrings(getAPIProvider()))
  } catch (error) {
    logError(error as Error)
  }
}

export function getModelStrings(): ModelStrings {
  const ms = getModelStringsState()
  if (ms === null) {
    initModelStrings()
    return applyModelOverrides(getBuiltinModelStrings(getAPIProvider()))
  }
  return applyModelOverrides(ms)
}

export async function ensureModelStringsInitialized(): Promise<void> {
  const ms = getModelStringsState()
  if (ms !== null) {
    return
  }
  setModelStringsState(getBuiltinModelStrings(getAPIProvider()))
}
