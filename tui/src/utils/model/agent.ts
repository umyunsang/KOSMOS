// KOSMOS Epic #2112: legacy subagent model-selection logic collapsed. KOSMOS
// runs a single FriendliAI K-EXAONE deployment, so subagents always inherit
// that model via getRuntimeMainLoopModel. Bedrock region-prefix carry-over is
// preserved as a stub; getAgentModelOptions exposes only the inherit option.

import type { PermissionMode } from '../permissions/PermissionMode.js'
import { capitalize } from '../stringUtils.js'
import { MODEL_ALIASES, type ModelAlias } from './aliases.js'
import { getRuntimeMainLoopModel, parseUserSpecifiedModel } from './model.js'

export const AGENT_MODEL_OPTIONS = [...MODEL_ALIASES, 'inherit'] as const
export type AgentModelAlias = (typeof AGENT_MODEL_OPTIONS)[number]

export type AgentModelOption = {
  value: AgentModelAlias
  label: string
  description: string
}

export function getDefaultSubagentModel(): string {
  return 'inherit'
}

/**
 * Get the effective model string for an agent.
 *
 * KOSMOS: single-fixed FriendliAI provider; cross-region inference prefixes are
 * dead, alias-based downgrades are dead. Always resolves through
 * parseUserSpecifiedModel which collapses every input to K-EXAONE.
 */
export function getAgentModel(
  agentModel: string | undefined,
  parentModel: string,
  toolSpecifiedModel?: ModelAlias,
  permissionMode?: PermissionMode,
): string {
  if (process.env.KOSMOS_SUBAGENT_MODEL) {
    return parseUserSpecifiedModel(process.env.KOSMOS_SUBAGENT_MODEL)
  }

  if (toolSpecifiedModel) {
    return parseUserSpecifiedModel(toolSpecifiedModel)
  }

  const agentModelWithExp = agentModel ?? getDefaultSubagentModel()

  if (agentModelWithExp === 'inherit') {
    return getRuntimeMainLoopModel({
      permissionMode: permissionMode ?? 'default',
      mainLoopModel: parentModel,
      exceeds200kTokens: false,
    })
  }

  return parseUserSpecifiedModel(agentModelWithExp)
}

export function getAgentModelDisplay(model: string | undefined): string {
  if (!model) return 'Inherit from parent (default)'
  if (model === 'inherit') return 'Inherit from parent'
  return capitalize(model)
}

/**
 * Get available model options for agents. KOSMOS exposes only the inherit
 * choice — every concrete alias resolves to the same K-EXAONE model anyway.
 */
export function getAgentModelOptions(): AgentModelOption[] {
  return [
    {
      value: 'inherit',
      label: 'Inherit from parent',
      description: 'Use the same model as the main conversation',
    },
  ]
}
