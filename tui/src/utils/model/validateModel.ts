// KOSMOS Epic #2112: legacy model-validation API call removed. KOSMOS uses a
// single-fixed FriendliAI deployment; the only valid model is the canonical
// K-EXAONE id (or any alias / explicit allowlist match).

import { MODEL_ALIASES } from './aliases.js'
import { KOSMOS_K_EXAONE_MODEL } from './constants.js'
import { isModelAllowed } from './modelAllowlist.js'

export async function validateModel(
  model: string,
): Promise<{ valid: boolean; error?: string }> {
  const normalised = model.trim()
  if (!normalised) {
    return { valid: false, error: 'Model name cannot be empty' }
  }

  if (!isModelAllowed(normalised)) {
    return {
      valid: false,
      error: `Model '${normalised}' is not in the list of available models`,
    }
  }

  const lowered = normalised.toLowerCase()
  if ((MODEL_ALIASES as readonly string[]).includes(lowered)) {
    return { valid: true }
  }

  if (normalised === KOSMOS_K_EXAONE_MODEL) {
    return { valid: true }
  }

  if (normalised === process.env.KOSMOS_CUSTOM_MODEL_OPTION) {
    return { valid: true }
  }

  return {
    valid: false,
    error: `Model '${normalised}' is not recognised by KOSMOS (expected ${KOSMOS_K_EXAONE_MODEL} or an entry in availableModels).`,
  }
}
