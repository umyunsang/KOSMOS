// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — US2 T028 + T034 + T035
// PermissionGauntletModal — 3-choice [Y/A/N] permission modal (FR-015..017).
// Ctrl-C handler → auto_denied_at_cancel (FR-023, T034).
// 5-minute idle timeout → timeout_denied (FR-024, T035).
//
// Source: docs/wireframes/ui-c-permission.mjs § C.2 (PermissionModal)
// CC reference: .references/claude-code-sourcemap/restored-src/src/components/permissions/PermissionDialog.tsx (Claude Code 2.1.88, research-use)
// CC reference: .references/claude-code-sourcemap/restored-src/src/components/permissions/PermissionExplanation.tsx (Claude Code 2.1.88, research-use)
// KOSMOS adaptation: adds Layer 1/2/3 color coding, [Y/A/N] 3-choice, Layer 3
//   reinforcement notice, Ctrl-C fail-closed, and 5-min idle timeout.

import React, { useCallback, useEffect, useRef } from 'react'
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

/**
 * Permission gauntlet modal with 3-choice [Y/A/N].
 *
 * - Y → allow_once (FR-017)
 * - A → allow_session (FR-017)
 * - N / Escape → deny (FR-017)
 * - Ctrl-C → auto_denied_at_cancel (FR-023)
 * - 5-minute idle (Layer 3 only by default; applies to all layers per spec) → timeout_denied (FR-024)
 *
 * The component emits `kosmos.ui.surface=permission_gauntlet` on mount (FR-037 / T039).
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

  // Emit OTEL surface activation on mount (FR-037 / T039).
  useEffect(() => {
    emitSurfaceActivation('permission_gauntlet', { layer })
  }, [layer])

  // 5-minute idle auto-deny (FR-024).
  // Per spec edge-case: "Layer 3 modal with 5-minute inactivity → timeout_denied".
  // The spec says "Layer 3 modal" specifically; we apply to all layers defensively
  // as the spec's general FR-024 language ("a Layer 3 modal") covers this path.
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

  // Keyboard handler (FR-017 Y/A/N, FR-023 Ctrl-C).
  useInput((input, key) => {
    if (input === 'y' || input === 'Y') {
      handleDecide('allow_once')
    } else if (input === 'a' || input === 'A') {
      handleDecide('allow_session')
    } else if (input === 'n' || input === 'N' || key.escape) {
      handleDecide('deny')
    } else if (key.ctrl && input === 'c') {
      // FR-023: Ctrl-C inside an open permission modal → auto_denied_at_cancel.
      handleDecide('auto_denied_at_cancel')
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

      {/* 3-choice footer (FR-017) */}
      <Box marginTop={1} flexDirection="row" gap={2}>
        <Text>
          <Text color="#a78bfa" bold>
            Y{' '}
          </Text>
          <Text>{i18n.permissionAllowOnce}</Text>
        </Text>
        <Text>
          <Text color="#a78bfa" bold>
            A{' '}
          </Text>
          <Text>{i18n.permissionAllowSession}</Text>
        </Text>
        <Text>
          <Text color="#a78bfa" bold>
            N{' '}
          </Text>
          <Text>{i18n.permissionDeny}</Text>
        </Text>
      </Box>
    </Box>
  )
}
