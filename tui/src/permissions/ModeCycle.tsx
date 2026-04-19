// SPDX-License-Identifier: Apache-2.0
// Spec 033 T042 — Shift+Tab mode cycle handler.
//
// Cycles low/mid-risk modes: default → plan → acceptEdits → default → ...
//
// Invariant S1 (escape hatch): from bypassPermissions/dontAsk, Shift+Tab
// returns directly to `default` (does NOT enter the cycle).
//
// Emits IPC permission.mode.changed envelope via the provided callback.
// OTEL span emission is delegated to otelEmit.ts (T046).

import React from 'react'
import { useInput } from 'ink'
import type { PermissionMode } from './types'
import { emitModeChangedOtel } from './otelEmit'

// ---------------------------------------------------------------------------
// Cycle definition
// ---------------------------------------------------------------------------

/** Low-risk Shift+Tab cycle. bypassPermissions and dontAsk are excluded (FR-A02). */
const FAST_CYCLE: readonly PermissionMode[] = ['default', 'plan', 'acceptEdits']

/** High-risk modes that are excluded from the fast cycle. */
const HIGH_RISK_MODES: ReadonlySet<PermissionMode> = new Set<PermissionMode>([
  'bypassPermissions',
  'dontAsk',
])

/**
 * Compute the next mode for a Shift+Tab press.
 *
 * - High-risk modes (bypassPermissions, dontAsk) → `default` (S1 escape hatch)
 * - Low/mid modes → advance in FAST_CYCLE (wraps)
 */
export function getNextModeCycle(current: PermissionMode): PermissionMode {
  if (HIGH_RISK_MODES.has(current)) {
    // S1: escape hatch — always return to default
    return 'default'
  }
  const idx = FAST_CYCLE.indexOf(current)
  const nextIdx = idx === -1 ? 0 : (idx + 1) % FAST_CYCLE.length
  return FAST_CYCLE[nextIdx]!
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ModeCycleProps {
  /** Current permission mode (controlled) */
  mode: PermissionMode
  /** Called when the mode should change — caller updates state */
  onModeChange: (next: PermissionMode) => void
  /**
   * Session ID for IPC envelope. May be empty string before handshake.
   * Used by otelEmit to populate the span request envelope.
   */
  sessionId: string
  /** Whether this component is active / should capture input */
  isActive?: boolean
}

// ---------------------------------------------------------------------------
// ModeCycle component
// ---------------------------------------------------------------------------

/**
 * Invisible input handler that intercepts Shift+Tab to cycle permission modes.
 *
 * Renders nothing — consumers place this alongside visible UI.
 * Keyboard handling is done here; visual output is in StatusBar.
 */
export function ModeCycle({
  mode,
  onModeChange,
  sessionId,
  isActive = true,
}: ModeCycleProps): React.ReactElement | null {
  useInput(
    (_input, key) => {
      if (key.shift && key.tab) {
        const next = getNextModeCycle(mode)
        onModeChange(next)
        emitModeChangedOtel({
          fromMode: mode,
          toMode: next,
          trigger: 'shift_tab',
          confirmed: true,  // Shift+Tab requires no confirmation dialog
          sessionId,
        })
      }
    },
    { isActive },
  )

  return null
}
