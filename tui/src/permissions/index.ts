// SPDX-License-Identifier: Apache-2.0
// Spec 033 T003 — Permission v2 TUI package public exports.
//
// WS1 (T018–T047) implementation by Frontend Developer Teammate.
//
// Reference: specs/033-permission-v2-spectrum/plan.md § Project Structure

// Types
export type {
  ConsentDecision,
  ModeDisplay,
  PermissionMode,
  PermissionRule,
  RuleDecision,
  RuleScope,
  ToolPermissionContext,
} from './types'

// StatusBar (T033 + T044)
export { StatusBar, MODE_DISPLAY_MAP } from './StatusBar'
export type { StatusBarProps } from './StatusBar'

// ModeCycle (T042)
export { ModeCycle, getNextModeCycle } from './ModeCycle'
export type { ModeCycleProps } from './ModeCycle'

// ConsentPrompt (T018)
export { ConsentPrompt, validateConsentDecision, ConsentValidationError } from './ConsentPrompt'
export type { ConsentPromptProps } from './ConsentPrompt'

// ConsentBridge (T019)
export {
  awaitConsentRequest,
  CONSENT_REQUEST_KIND,
  CONSENT_DECISION_KIND,
} from './consentBridge'
export type {
  ConsentBridgeOptions,
  ConsentBridgeResult,
  ConsentRequestPayload,
  ConsentDecisionPayload,
} from './consentBridge'

// BypassConfirmDialog (T032)
export { BypassConfirmDialog } from './BypassConfirmDialog'
export type { BypassConfirmDialogProps } from './BypassConfirmDialog'

// DontAskConfirmDialog (T045)
export { DontAskConfirmDialog } from './DontAskConfirmDialog'
export type { DontAskConfirmDialogProps } from './DontAskConfirmDialog'

// RuleListView (T039)
export { RuleListView } from './RuleListView'
export type { RuleListViewProps } from './RuleListView'

// CommandRouter (T043)
export {
  buildPermissionCommands,
  parsePermissionsSubCommand,
  routePermissionsCommand,
} from './commandRouter'
export type { PermissionCommandCallbacks } from './commandRouter'

// OTEL emitter (T046)
export { emitModeChangedOtel } from './otelEmit'
export type { ModeChangedOtelParams, ModeTrigger } from './otelEmit'
