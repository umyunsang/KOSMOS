// KOSMOS Epic #2112: legacy model-validation API call removed. After the
// Codex P2 fix the validator delegates the accept/reject decision entirely
// to `isModelAllowed` (which honours `settings.availableModels`). Anything
// that survives the allowlist gate is shippable to FriendliAI; unknown
// names are resolved to K-EXAONE by `parseUserSpecifiedModel` at request
// time.

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

  // Codex P2 (PR #2151): once isModelAllowed gates the input, the function
  // must accept it. Previously this branch only honoured the canonical
  // K-EXAONE id and KOSMOS_CUSTOM_MODEL_OPTION, which contradicted both the
  // function's own error message and the docstring intent — making `/model
  // <id>` fail when `<id>` is explicitly listed in `settings.availableModels`.
  // Anything that survives the allowlist gate above is, by definition, valid
  // for KOSMOS to ship to FriendliAI; runtime resolution is handled by
  // parseUserSpecifiedModel which collapses unknown names back to K-EXAONE.
  return { valid: true }
}
