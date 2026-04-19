// SPDX-License-Identifier: Apache-2.0
// Spec 033 T032 — bypassPermissions confirmation dialog.
//
// Triggered by `/permissions bypass` slash command.
// Shows 3-bullet killswitch reminder + timeout info.
//
// Invariant UI2: default focus MUST be "N" (reject).
// Users must explicitly press Y to activate bypassPermissions.

import React, { useState } from 'react'
import { Box, Text, useInput } from 'ink'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface BypassConfirmDialogProps {
  /** Called when user confirms with Y */
  onConfirm: () => void
  /** Called when user rejects with N / ESC */
  onCancel: () => void
  /**
   * Auto-expiry duration to display (e.g. "30분").
   * Defaults to "30분" per spec §FR-A05.
   */
  expiresInLabel?: string
  /** Whether this dialog captures input */
  isActive?: boolean
}

// ---------------------------------------------------------------------------
// BypassConfirmDialog component
// ---------------------------------------------------------------------------

/**
 * Warning dialog for `/permissions bypass` — activates bypassPermissions mode.
 *
 * Invariant UI2: default focus is N (cancel).
 * Three killswitch bullets per mode-transition.contract.md §6.
 */
export function BypassConfirmDialog({
  onConfirm,
  onCancel,
  expiresInLabel = '30분',
  isActive = true,
}: BypassConfirmDialogProps): React.ReactElement {
  // UI2: default focus = N (cancel)
  const [focusYes, setFocusYes] = useState<boolean>(false)

  useInput(
    (input, key) => {
      const ch = input.toLowerCase()
      if (ch === 'y') {
        onConfirm()
      } else if (ch === 'n' || key.escape) {
        onCancel()
      } else if (key.return) {
        // Enter executes focused button (default = N → cancel)
        if (focusYes) {
          onConfirm()
        } else {
          onCancel()
        }
      } else if (key.leftArrow || key.rightArrow || key.tab) {
        setFocusYes((prev) => !prev)
      }
    },
    { isActive },
  )

  return (
    <Box flexDirection="column" borderStyle="double" borderColor="red" paddingX={1} paddingY={0}>
      {/* Header */}
      <Box marginBottom={1}>
        <Text bold color="red">
          ⚠ 경고: bypassPermissions 모드로 전환
        </Text>
      </Box>

      {/* Description */}
      <Box marginBottom={1}>
        <Text>이 모드에서는 가역 호출이 확인 없이 실행됩니다.</Text>
      </Box>

      {/* Killswitch bullets — always active regardless of mode */}
      <Box flexDirection="column" marginBottom={1} paddingLeft={2}>
        <Text bold>단, 다음은 여전히 매번 확인합니다:</Text>
        <Box paddingLeft={2}>
          <Text>{'  - 되돌릴 수 없는 호출 (is_irreversible=True)'}</Text>
        </Box>
        <Box paddingLeft={2}>
          <Text>{'  - 특수 범주 (pipa_class=특수)'}</Text>
        </Box>
        <Box paddingLeft={2}>
          <Text>{'  - AAL3 인증 필요 호출'}</Text>
        </Box>
      </Box>

      {/* Auto-expiry notice */}
      <Box marginBottom={1}>
        <Text color="yellow">
          자동 만료: {expiresInLabel} 후 기본 모드로 복귀합니다.
        </Text>
      </Box>

      {/* Action buttons — UI2: default focus = N */}
      <Box>
        <Text
          bold={!focusYes}
          color={!focusYes ? 'red' : 'gray'}
          underline={!focusYes}
        >
          {'[N] 취소 (기본)'}
        </Text>
        <Text>{'  '}</Text>
        <Text
          bold={focusYes}
          color={focusYes ? 'yellow' : 'gray'}
          underline={focusYes}
        >
          {'[Y] 우회 활성화'}
        </Text>
        <Text color="gray">{'  (←/→ Tab: 포커스 이동)'}</Text>
      </Box>
    </Box>
  )
}
