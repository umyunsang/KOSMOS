// KOSMOS Epic #2112: legacy model-option matrix removed; collapsed to a single
// K-EXAONE entry. Exported function signatures preserved per FR-006 caller-reach
// rule (subscription-tier helpers retained as imports — deferred to P2 issue #2146).

import { getInitialMainLoopModel } from '../../bootstrap/state.js'
import { isClaudeAISubscriber } from '../auth.js'
import { getSettings_DEPRECATED } from '../settings/settings.js'
import { isModelAllowed } from './modelAllowlist.js'
import {
  getClaudeAiUserDefaultModelDescription,
  getDefaultMainLoopModel,
  getUserSpecifiedModelSetting,
  type ModelSetting,
} from './model.js'
import { getGlobalConfig } from '../config.js'

export type ModelOption = {
  value: ModelSetting
  label: string
  description: string
  descriptionForModel?: string
}

const KOSMOS_K_EXAONE_LABEL = 'K-EXAONE'
const KOSMOS_K_EXAONE_DESCRIPTION = 'KOSMOS default via FriendliAI Serverless'

function kosmosDefaultOption(): ModelOption {
  return {
    value: null,
    label: 'Default (recommended)',
    description: isClaudeAISubscriber()
      ? getClaudeAiUserDefaultModelDescription()
      : `Use the default model (currently ${getDefaultMainLoopModel()})`,
    descriptionForModel: KOSMOS_K_EXAONE_DESCRIPTION,
  }
}

function kosmosKExaoneOption(): ModelOption {
  return {
    value: getDefaultMainLoopModel(),
    label: KOSMOS_K_EXAONE_LABEL,
    description: KOSMOS_K_EXAONE_DESCRIPTION,
    descriptionForModel: KOSMOS_K_EXAONE_DESCRIPTION,
  }
}

export function getDefaultOptionForUser(_fastMode = false): ModelOption {
  return kosmosDefaultOption()
}

// [Deferred to P2 — issue #2147]: legacy 1M-context option exports preserved as
// stubs returning the canonical K-EXAONE entry; removed when the picker UI is
// migrated in Phase P2/P3.
export function getSonnet46_1MOption(): ModelOption {
  return kosmosKExaoneOption()
}

export function getOpus46_1MOption(_fastMode = false): ModelOption {
  return kosmosKExaoneOption()
}

export function getMaxSonnet46_1MOption(): ModelOption {
  return kosmosKExaoneOption()
}

export function getMaxOpus46_1MOption(_fastMode = false): ModelOption {
  return kosmosKExaoneOption()
}

export function getModelOptions(fastMode = false): ModelOption[] {
  const options: ModelOption[] = [getDefaultOptionForUser(fastMode), kosmosKExaoneOption()]

  // KOSMOS_CUSTOM_MODEL_OPTION env var lets advanced users register an extra
  // entry without touching code (e.g. an alternate FriendliAI deployment).
  const envCustomModel = process.env.KOSMOS_CUSTOM_MODEL_OPTION
  if (envCustomModel && !options.some(existing => existing.value === envCustomModel)) {
    options.push({
      value: envCustomModel,
      label: process.env.KOSMOS_CUSTOM_MODEL_OPTION_NAME ?? envCustomModel,
      description:
        process.env.KOSMOS_CUSTOM_MODEL_OPTION_DESCRIPTION ?? `Custom model (${envCustomModel})`,
    })
  }

  // Append additional model options fetched during bootstrap.
  for (const opt of getGlobalConfig().additionalModelOptionsCache ?? []) {
    if (!options.some(existing => existing.value === opt.value)) {
      options.push(opt)
    }
  }

  // Add the user-specified custom model if it is not already present.
  let customModel: ModelSetting = null
  const currentMainLoopModel = getUserSpecifiedModelSetting()
  const initialMainLoopModel = getInitialMainLoopModel()
  if (currentMainLoopModel !== undefined && currentMainLoopModel !== null) {
    customModel = currentMainLoopModel
  } else if (initialMainLoopModel !== null) {
    customModel = initialMainLoopModel
  }
  if (customModel !== null && !options.some(opt => opt.value === customModel)) {
    options.push({
      value: customModel,
      label: typeof customModel === 'string' ? customModel : KOSMOS_K_EXAONE_LABEL,
      description: 'Custom model',
    })
  }

  return filterModelOptionsByAllowlist(options)
}

/**
 * Filter model options by the availableModels allowlist.
 * Always preserves the "Default" option (value: null).
 */
function filterModelOptionsByAllowlist(options: ModelOption[]): ModelOption[] {
  const settings = getSettings_DEPRECATED() || {}
  if (!settings.availableModels) {
    return options
  }
  return options.filter(
    opt => opt.value === null || (opt.value !== null && isModelAllowed(opt.value)),
  )
}
