// SPDX-License-Identifier: Apache-2.0
// Spec 033 T045 — dontAsk confirmation dialog.
//
// Mirror of BypassConfirmDialog for `/permissions dontAsk`.
// Triggered by `/permissions dontAsk` slash command.
//
// Invariant UI2: default focus MUST be "N" (reject).
// Users must explicitly press Y to activate dontAsk mode.

import React, { useState } from 'react'
import { Box, Text, useInput } from 'ink'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface DontAskConfirmDialogProps {
  /** Called when user confirms with Y */
  onConfirm: () => void
  /** Called when user rejects with N / ESC */
  onCancel: () => void
  /** Whether this dialog captures input */
  isActive?: boolean
}

// ---------------------------------------------------------------------------
// DontAskConfirmDialog component
// ---------------------------------------------------------------------------

/**
 * Warning dialog for `/permissions dontAsk` — activates dontAsk mode.
 *
 * Invariant UI2: default focus is N (cancel).
 * dontAsk auto-approves adapters in the pre-saved allow-list; anything not
 * in the list falls back to default (prompt-every-call).
 */
export function DontAskConfirmDialog({
  onConfirm,
  onCancel,
  isActive = true,
}: DontAskConfirmDialogProps): React.ReactElement {
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
    <Box flexDirection="column" borderStyle="single" borderColor="blue" paddingX={1} paddingY={0}>
      {/* Header */}
      <Box marginBottom={1}>
        <Text bold color="blueBright">
          dontAsk 모드로 전환
        </Text>
      </Box>

      {/* Description */}
      <Box marginBottom={1}>
        <Text>
          사전 저장된 허용 목록의 어댑터는 확인 없이 자동으로 실행됩니다.
        </Text>
        <Text>
          허용 목록에 없는 어댑터는 기본 모드(매 호출 확인)로 폴백됩니다.
        </Text>
      </Box>

      {/* Killswitch notes */}
      <Box flexDirection="column" marginBottom={1} paddingLeft={2}>
        <Text bold>다음은 허용 목록과 무관하게 항상 확인합니다:</Text>
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

      {/* Action buttons — UI2: default focus = N */}
      <Box>
        <Text
          bold={!focusYes}
          color={!focusYes ? 'blueBright' : 'gray'}
          underline={!focusYes}
        >
          {'[N] 취소 (기본)'}
        </Text>
        <Text>{'  '}</Text>
        <Text
          bold={focusYes}
          color={focusYes ? 'green' : 'gray'}
          underline={focusYes}
        >
          {'[Y] 사전허용 활성화'}
        </Text>
        <Text color="gray">{'  (←/→ Tab: 포커스 이동)'}</Text>
      </Box>
    </Box>
  )
}
