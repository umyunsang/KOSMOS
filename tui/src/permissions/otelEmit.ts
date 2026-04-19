// SPDX-License-Identifier: Apache-2.0
// Spec 033 T046 — OTEL span request envelope emitter (TUI side).
//
// The TUI does NOT hold the opentelemetry-sdk dependency (AGENTS.md hard rule;
// FR-054 from bridge.ts).  Instead it emits a structured log record to stderr
// using the agreed OTEL-proxy format that the Python backend picks up and turns
// into a real span (Spec 021 §3).
//
// Format: one JSON line on stderr prefixed with "[KOSMOS OTEL] "
// The backend's stderr reader filters on this prefix.
//
// Span: permission.mode.changed
// Attrs: from_mode, to_mode, trigger ∈ {shift_tab, slash_command}, confirmed: bool

import type { PermissionMode } from './types'

// ---------------------------------------------------------------------------
// Span attribute types
// ---------------------------------------------------------------------------

export type ModeTrigger = 'shift_tab' | 'slash_command'

export interface ModeChangedOtelParams {
  fromMode: PermissionMode
  toMode: PermissionMode
  trigger: ModeTrigger
  /** Whether a confirmation dialog was accepted (Y). Always true for shift_tab. */
  confirmed: boolean
  sessionId: string
}

// ---------------------------------------------------------------------------
// Emit helper
// ---------------------------------------------------------------------------

/**
 * Emit a `permission.mode.changed` OTEL span request to stderr.
 *
 * The Python backend reads this prefix-tagged JSON line from stderr and
 * emits the real OTel span (Spec 021 §3).  The TUI never calls the
 * opentelemetry-sdk directly (no new JS dep rule — SC-008).
 *
 * This function MUST be synchronous and MUST NOT throw.
 */
export function emitModeChangedOtel(params: ModeChangedOtelParams): void {
  try {
    const record = {
      span_name: 'permission.mode.changed',
      attrs: {
        'kosmos.permission.from_mode': params.fromMode,
        'kosmos.permission.to_mode': params.toMode,
        'kosmos.permission.trigger': params.trigger,
        'kosmos.permission.confirmed': params.confirmed,
        'session.id': params.sessionId,
      },
      ts: new Date().toISOString(),
    }
    process.stderr.write(`[KOSMOS OTEL] ${JSON.stringify(record)}\n`)
  } catch {
    // swallow — telemetry must never crash the TUI
  }
}
