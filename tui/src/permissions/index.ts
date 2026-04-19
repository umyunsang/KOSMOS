// SPDX-License-Identifier: Apache-2.0
// Spec 033 T003 — Permission v2 TUI package public exports skeleton.
//
// This index re-exports all public types and will re-export components and
// utilities as they are implemented by WS1 and WS4 Teammates (Phases 3-7).
//
// Current state: type-only exports (no runtime logic yet).
// Component stubs (ModeStatusBar, ConsentPrompt, etc.) will be added
// by the Frontend Developer Teammate at WS1/WS4 implementation.
//
// Reference: specs/033-permission-v2-spectrum/plan.md § Project Structure

export type {
  ConsentDecision,
  ModeDisplay,
  PermissionMode,
  PermissionRule,
  RuleDecision,
  RuleScope,
  ToolPermissionContext,
} from './types'
