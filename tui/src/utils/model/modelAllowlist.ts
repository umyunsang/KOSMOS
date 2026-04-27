// KOSMOS Epic #2112: legacy family-alias and version-prefix allowlist matchers
// removed. Single-fixed K-EXAONE means availableModels semantics collapse to
// "is the user-supplied name K-EXAONE or in the user's explicit allowlist?".

import { getSettings_DEPRECATED } from '../settings/settings.js'
import { isModelAlias } from './aliases.js'
import { KOSMOS_K_EXAONE_MODEL } from './constants.js'
import { resolveOverriddenModel } from './modelStrings.js'

export function isModelAllowed(model: string): boolean {
  const settings = getSettings_DEPRECATED() || {}
  const { availableModels } = settings
  if (!availableModels) {
    return true // No restrictions
  }
  if (availableModels.length === 0) {
    return false // Empty allowlist blocks all user-specified models
  }

  const resolved = resolveOverriddenModel(model)
  const normalised = resolved.trim().toLowerCase()
  const allowlist = availableModels.map(m => m.trim().toLowerCase())

  if (allowlist.includes(normalised)) {
    return true
  }
  // The canonical K-EXAONE identifier is always allowed when the allowlist
  // is non-empty — required so getDefaultMainLoopModel() never trips its own gate.
  if (normalised === KOSMOS_K_EXAONE_MODEL.toLowerCase()) {
    return true
  }
  // Aliases (e.g. legacy 'default') resolve via parseUserSpecifiedModel — if
  // the input is a known alias, accept it.
  if (isModelAlias(normalised)) {
    return true
  }
  return false
}
