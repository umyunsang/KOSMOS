// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/components/wizard/types.ts (Claude Code 2.1.88, research-use)
import type { ComponentType, ReactNode } from 'react'

export type WizardStepComponent = ComponentType<Record<string, never>>

export interface WizardContextValue<
  T extends Record<string, unknown> = Record<string, unknown>,
> {
  currentStepIndex: number
  totalSteps: number
  wizardData: T
  setWizardData: React.Dispatch<React.SetStateAction<T>>
  updateWizardData: (updates: Partial<T>) => void
  goNext: () => void
  goBack: () => void
  goToStep: (index: number) => void
  cancel: () => void
  title?: string
  showStepCounter?: boolean
}

export interface WizardProviderProps<
  T extends Record<string, unknown> = Record<string, unknown>,
> {
  steps: WizardStepComponent[]
  initialData?: T
  onComplete: (data: T) => void | Promise<void>
  onCancel?: () => void
  children?: ReactNode
  title?: string
  showStepCounter?: boolean
}
