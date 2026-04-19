// SPDX-License-Identifier: Apache-2.0
// Spec 033 T033 + T044 — Permission mode status bar.
//
// T033: initial scaffold — red/yellow flashing when mode=bypassPermissions.
// T044: full color map per mode-transition.contract.md §4.
//
// Invariant UI1: bypassPermissions MUST flash red/yellow (Constitution §II).

import React, { useState, useEffect } from 'react'
import { Box, Text } from 'ink'
import type { PermissionMode, ModeDisplay } from './types'

// ---------------------------------------------------------------------------
// Mode display metadata — contract §4
// ---------------------------------------------------------------------------

/** Mode → display metadata. Source of truth: mode-transition.contract.md §4 */
const MODE_DISPLAY_MAP: Record<PermissionMode, ModeDisplay> = {
  default: {
    mode: 'default',
    label: '모드: 기본 (매 호출 확인)',
    color: 'neutral',
    flashing: false,
  },
  plan: {
    mode: 'plan',
    label: '모드: 계획 (실행 없음)',
    color: 'cyan',
    flashing: false,
  },
  acceptEdits: {
    mode: 'acceptEdits',
    label: '모드: 자동허용 (가역·공용)',
    color: 'green',
    flashing: false,
  },
  bypassPermissions: {
    mode: 'bypassPermissions',
    label: '⚠ 모드: 우회 (되돌릴 수 없는 호출 계속 확인)',
    color: 'red',
    flashing: true,  // UI1: MUST flash red/yellow
  },
  dontAsk: {
    mode: 'dontAsk',
    label: '모드: 사전허용 (목록만 자동)',
    color: 'blue',
    flashing: false,
  },
}

// ---------------------------------------------------------------------------
// Color → Ink color string
// ---------------------------------------------------------------------------

/** Resolve Ink-compatible color string from ModeDisplay.color */
function resolveColor(
  display: ModeDisplay,
  flashPhase: boolean,
): string {
  if (display.flashing) {
    // UI1: bypassPermissions alternates red ↔ yellow
    return flashPhase ? 'red' : 'yellow'
  }
  switch (display.color) {
    case 'cyan':    return 'cyan'
    case 'green':   return 'green'
    case 'blue':    return 'blueBright'
    case 'neutral':
    default:        return 'gray'
  }
}

// ---------------------------------------------------------------------------
// StatusBar props
// ---------------------------------------------------------------------------

export interface StatusBarProps {
  /** Current permission mode */
  mode: PermissionMode
  /**
   * Flash interval in milliseconds for bypassPermissions mode (default: 600).
   * Exposed for test overrides.
   */
  flashIntervalMs?: number
}

// ---------------------------------------------------------------------------
// StatusBar component
// ---------------------------------------------------------------------------

/**
 * Persistent status bar showing the current permission mode.
 *
 * Invariant UI1: When mode=bypassPermissions, the bar flashes red/yellow so
 * the citizen can never miss that bypass is active.
 */
export function StatusBar({ mode, flashIntervalMs = 600 }: StatusBarProps): React.ReactElement {
  const display = MODE_DISPLAY_MAP[mode]
  const [flashPhase, setFlashPhase] = useState<boolean>(false)

  // Flashing timer — only active for bypassPermissions (UI1)
  useEffect(() => {
    if (!display.flashing) {
      setFlashPhase(false)
      return
    }
    const id = setInterval(() => {
      setFlashPhase((prev) => !prev)
    }, flashIntervalMs)
    return () => clearInterval(id)
  }, [display.flashing, flashIntervalMs])

  const color = resolveColor(display, flashPhase)

  return (
    <Box>
      <Text color={color} bold={display.flashing}>
        {display.label}
      </Text>
    </Box>
  )
}

/** Re-export display map for use by tests and other components */
export { MODE_DISPLAY_MAP }
