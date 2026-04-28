// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — US2 T028 + T034 + T035
// Spec 1979 — KOSMOS Y/A/N direct-keystroke pattern replaced with CC arrow+Enter
//             selection pattern for parity with the rest of the TUI.
//
// PermissionGauntletModal — 3-choice permission modal (FR-015..017).
// Ctrl-C handler → auto_denied_at_cancel (FR-023, T034).
// 5-minute idle timeout → timeout_denied (FR-024, T035).
//
// Source pattern:
//   .references/claude-code-sourcemap/restored-src/src/components/permissions/PermissionPrompt.tsx
//   (Claude Code 2.1.88, research-use)
//
// CC's PermissionPrompt uses arrow+Enter selection (NOT direct Y/A/N
// keystrokes).  We adopt that pattern here while preserving KOSMOS's
// Layer 1/2/3 color coding, Layer 3 reinforcement notice, Ctrl-C →
// auto_denied_at_cancel, and 5-min idle timeout invariants from Spec 1635
// FR-017/FR-023/FR-024.
//
// Implementation note: we drive arrow navigation via raw `useInput`
// (the same approach the OnboardingFlow ThemeStep uses) instead of the
// `<Select>` component, because `<Select>` routes Up/Down/Enter through
// `useKeybindings`, which ink-testing-library's stdin emulator cannot
// drive in unit tests.  The interaction model is identical to CC's Select
// from the citizen's perspective.

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Box, Text, useInput } from 'ink'
import { PermissionLayerHeader } from './PermissionLayerHeader.js'
import { useUiL2I18n } from '../../i18n/uiL2.js'
import { emitSurfaceActivation } from '../../observability/surface.js'
import type { PermissionDecisionT, PermissionLayerT } from '../../schemas/ui-l2/permission.js'

// Layer-specific hex colors (mirrors PermissionLayerHeader.tsx)
const LAYER_HEX: Record<PermissionLayerT, string> = {
  1: '#34d399',
  2: '#fb923c',
  3: '#f87171',
}

/** Milliseconds before a Layer 3 modal auto-denies with `timeout_denied`. FR-024. */
const LAYER3_TIMEOUT_MS = 5 * 60 * 1000 // 5 minutes

export interface PermissionGauntletModalProps {
  /** Layer number for the tool (1=low, 2=medium, 3=high). */
  layer: PermissionLayerT
  /** Tool name to display in the modal. */
  toolName: string
  /** Brief description of what the tool will do. */
  description: string
  /** Called when the citizen makes a decision (or auto-denial fires). */
  onDecide: (decision: PermissionDecisionT) => void
}

type ChoiceValue = Extract<PermissionDecisionT, 'allow_once' | 'allow_session' | 'deny'>

/**
 * Permission gauntlet modal with 3-choice arrow+Enter selection.
 *
 * - allow_once    → grant for this single call (FR-017)
 * - allow_session → grant for the current session (FR-017)
 * - deny          → reject (FR-017); also fires on Esc
 * - Ctrl-C        → auto_denied_at_cancel (FR-023)
 * - 5-minute idle → timeout_denied (FR-024)
 *
 * Emits `kosmos.ui.surface=permission_gauntlet` on mount (FR-037 / T039).
 */
export function PermissionGauntletModal({
  layer,
  toolName,
  description,
  onDecide,
}: PermissionGauntletModalProps): React.ReactElement {
  const i18n = useUiL2I18n()
  const color = LAYER_HEX[layer]
  const decidedRef = useRef(false)
  const [focusedIdx, setFocusedIdx] = useState(0)

  const choices: { label: string; value: ChoiceValue }[] = useMemo(
    () => [
      { label: i18n.permissionAllowOnce, value: 'allow_once' },
      { label: i18n.permissionAllowSession, value: 'allow_session' },
      { label: i18n.permissionDeny, value: 'deny' },
    ],
    [i18n],
  )

  // Emit OTEL surface activation on mount (FR-037 / T039).
  useEffect(() => {
    emitSurfaceActivation('permission_gauntlet', { layer })
  }, [layer])

  // 5-minute idle auto-deny (FR-024).
  useEffect(() => {
    const id = setTimeout(() => {
      if (!decidedRef.current) {
        decidedRef.current = true
        onDecide('timeout_denied')
      }
    }, LAYER3_TIMEOUT_MS)
    return () => clearTimeout(id)
  }, [onDecide])

  const handleDecide = useCallback(
    (decision: PermissionDecisionT) => {
      if (decidedRef.current) return
      decidedRef.current = true
      onDecide(decision)
    },
    [onDecide],
  )

  // CC arrow+Enter pattern (replaces previous Y/A/N direct-keystroke pattern).
  // FR-017: 3-choice selection.  FR-023: Ctrl-C → auto_denied_at_cancel.  Esc → deny.
  useInput((input, key) => {
    if (key.ctrl && input === 'c') {
      handleDecide('auto_denied_at_cancel')
      return
    }
    if (key.escape) {
      handleDecide('deny')
      return
    }
    if (key.upArrow) {
      setFocusedIdx((i) => (i - 1 + choices.length) % choices.length)
      return
    }
    if (key.downArrow) {
      setFocusedIdx((i) => (i + 1) % choices.length)
      return
    }
    if (key.return) {
      const choice = choices[focusedIdx]
      if (choice) handleDecide(choice.value)
    }
  })

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={color}
      paddingX={2}
      paddingY={1}
      width={70}
    >
      {/* Header row: layer glyph + tool name (FR-016) */}
      <PermissionLayerHeader layer={layer} toolName={toolName} />

      {/* Tool description */}
      <Box marginTop={1}>
        <Text dimColor>요청: </Text>
        <Text>{description}</Text>
      </Box>

      {/* Layer 3 reinforcement notice (FR-017 + migration tree C.2) */}
      {layer === 3 && (
        <Box marginTop={1}>
          <Text color="#f87171">{i18n.permissionLayer3Reinforcement}</Text>
        </Box>
      )}

      {/* Arrow+Enter choice list (CC pattern; replaces Y/A/N keystrokes) */}
      <Box marginTop={1} flexDirection="column">
        {choices.map((c, i) => {
          const focused = i === focusedIdx
          return (
            <Box key={c.value}>
              <Text color={focused ? '#a78bfa' : undefined} bold={focused}>
                {focused ? '› ' : '  '}
                {c.label}
              </Text>
            </Box>
          )
        })}
      </Box>

      {/* Hint footer */}
      <Box marginTop={1}>
        <Text dimColor>{'↑↓ 선택 · Enter 확정 · Esc 거부 (Ctrl-C 취소)'}</Text>
      </Box>
    </Box>
  )
}
