// SPDX-License-Identifier: Apache-2.0
// Spec 033 T003 — Permission v2 TypeScript type stubs.
//
// This file defines the TypeScript types for the Permission v2 mode spectrum,
// rule store, and consent ledger surface.  Logic will be added by WS1 (mode
// engine + TUI keychord) and WS4 (consent prompt UI) Teammates.
//
// Reference: specs/033-permission-v2-spectrum/data-model.md § 1

/**
 * 5-mode external permission spectrum.
 *
 * Mirror of Python ``PermissionMode`` Literal in
 * ``src/kosmos/permissions/modes.py``.
 *
 * | Mode               | Description                                           |
 * |--------------------|-------------------------------------------------------|
 * | default            | Ask on every call unless a persistent allow rule.     |
 * | plan               | Dry-run — no side effects (observationally pure).     |
 * | acceptEdits        | Auto-approve reversible AAL1/public reads.            |
 * | bypassPermissions  | Auto-approve all except killswitch gates.             |
 * | dontAsk            | Auto-approve pre-saved allow-list; fallback to default. |
 */
export type PermissionMode =
  | 'default'
  | 'plan'
  | 'acceptEdits'
  | 'bypassPermissions'
  | 'dontAsk'

/** Tri-state rule verdict. */
export type RuleDecision = 'allow' | 'ask' | 'deny'

/** Rule scope levels (narrower scope wins — R2). */
export type RuleScope = 'session' | 'project' | 'user'

/**
 * Persistent permission rule for a single adapter.
 *
 * Mirror of Python ``PermissionRule`` in
 * ``src/kosmos/permissions/models.py``.
 */
export interface PermissionRule {
  tool_id: string
  decision: RuleDecision
  scope: RuleScope
  created_at: string  // ISO 8601 UTC datetime
  created_by_mode: PermissionMode
  expires_at: string | null
}

/**
 * Per-invocation context for the v2 permission pipeline.
 *
 * Mirror of Python ``ToolPermissionContext`` in
 * ``src/kosmos/permissions/models.py``.
 */
export interface ToolPermissionContext {
  tool_id: string
  mode: PermissionMode
  is_irreversible: boolean
  auth_level: 'public' | 'AAL1' | 'AAL2' | 'AAL3'
  pipa_class: '일반' | '민감' | '고유식별' | '특수'
  session_id: string
  correlation_id: string
}

/**
 * PIPA §15(2) 4-tuple consent decision.
 *
 * Mirror of Python ``ConsentDecision`` in
 * ``src/kosmos/permissions/models.py``.
 */
export interface ConsentDecision {
  purpose: string         // 목적
  data_items: string[]    // 항목
  retention_period: string  // 보유기간
  refusal_right: string   // 거부권 + 불이익 고지문
  granted: boolean
  tool_id: string
  pipa_class: '일반' | '민감' | '고유식별' | '특수'
  auth_level: 'public' | 'AAL1' | 'AAL2' | 'AAL3'
  decided_at: string      // ISO 8601 UTC datetime
  action_digest: string   // SHA-256 hex, 64 chars
  scope: 'one-shot' | 'session' | 'user'
}

/** TUI status bar mode display metadata. */
export interface ModeDisplay {
  mode: PermissionMode
  label: string
  color: 'neutral' | 'cyan' | 'green' | 'red' | 'blue'
  flashing: boolean
}
