// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — /onboarding [step-name] command (FR-003, T046).
//
// /onboarding              — re-runs the full 5-step sequence from step 1
// /onboarding <step-name>  — re-runs a single step in isolation
//
// The command returns a descriptor that the REPL dispatcher uses to mount
// <OnboardingFlow> in the appropriate mode. Isolation-mode does not reset
// the persisted current_step_index; full re-run does (resetOnboardingState).
//
// Valid step names mirror OnboardingStepNameT:
//   preflight | theme | pipa-consent | ministry-scope | terminal-setup
//
// Reference: cc:commands/ (CC slash-command positional-arg pattern)
//            specs/1635-ui-l2-citizen-port/contracts/slash-commands.schema.json

import {
  ONBOARDING_STEP_ORDER,
  type OnboardingStepNameT,
} from '../schemas/ui-l2/onboarding.js'

// ---------------------------------------------------------------------------
// Command result type
// ---------------------------------------------------------------------------

export type OnboardingCommandResult =
  | { mode: 'full' }
  | { mode: 'isolated'; step: OnboardingStepNameT }
  | { mode: 'error'; message: string }

// ---------------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------------

/**
 * Parse the argument string from `/onboarding [step-name]`.
 *
 * Returns a typed descriptor so the caller can mount OnboardingFlow in the
 * correct mode without string-comparing elsewhere.
 */
export function parseOnboardingCommand(argStr: string): OnboardingCommandResult {
  const arg = argStr.trim()

  if (arg === '') {
    return { mode: 'full' }
  }

  // Validate against the canonical step order
  const stepNameSet = new Set<string>(ONBOARDING_STEP_ORDER)
  if (stepNameSet.has(arg)) {
    return { mode: 'isolated', step: arg as OnboardingStepNameT }
  }

  const validSteps = ONBOARDING_STEP_ORDER.join(' | ')
  return {
    mode: 'error',
    message: `Unknown onboarding step: "${arg}". Valid steps: ${validSteps}`,
  }
}

// ---------------------------------------------------------------------------
// Human-readable help text (consumed by /help catalog, FR-029)
// ---------------------------------------------------------------------------

export const ONBOARDING_COMMAND_HELP = {
  name: '/onboarding',
  group: 'session',
  description_ko: '온보딩 시퀀스를 처음부터 다시 진행하거나 특정 단계만 재실행합니다',
  description_en: 'Re-run the onboarding sequence or a single step in isolation',
  arg_signature: '[step-name]',
  step_names: ONBOARDING_STEP_ORDER as readonly OnboardingStepNameT[],
} as const
