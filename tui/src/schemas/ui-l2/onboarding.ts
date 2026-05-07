// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — OnboardingState entity (data-model.md §1, FR-001/002).
//
// Persisted at ~/.kosmos/memdir/user/onboarding/state.json. Owned by Epic #1635.
// Five-step sequence is canonical: preflight → theme → pipa-consent →
// ministry-scope → terminal-setup. Reordering requires a migration tree ADR.
import { z } from 'zod';

export const OnboardingStepName = z.enum([
  'preflight',
  'theme',
  'pipa-consent',
  'ministry-scope',
  'terminal-setup',
]);
export type OnboardingStepNameT = z.infer<typeof OnboardingStepName>;

export const ONBOARDING_STEP_ORDER: readonly OnboardingStepNameT[] = [
  'preflight',
  'theme',
  'pipa-consent',
  'ministry-scope',
  'terminal-setup',
] as const;

export const OnboardingStep = z.object({
  name: OnboardingStepName,
  completed_at: z.string().datetime().nullable(),
  values: z.record(z.string(), z.unknown()),
});
export type OnboardingStepT = z.infer<typeof OnboardingStep>;

export const OnboardingState = z.object({
  schema_version: z.literal(1),
  started_at: z.string().datetime(),
  language: z.enum(['ko', 'en']).default('ko'),
  steps: z.array(OnboardingStep).length(5),
  current_step_index: z.number().int().min(0).max(5),
});
export type OnboardingStateT = z.infer<typeof OnboardingState>;

export function freshOnboardingState(): OnboardingStateT {
  return {
    schema_version: 1,
    started_at: new Date().toISOString(),
    language: 'ko',
    steps: ONBOARDING_STEP_ORDER.map((name) => ({
      name,
      completed_at: null,
      values: {},
    })),
    current_step_index: 0,
  };
}

export function isOnboardingComplete(state: OnboardingStateT): boolean {
  return state.current_step_index === 5;
}
