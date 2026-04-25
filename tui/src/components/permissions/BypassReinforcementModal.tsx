// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — US2 T030
// BypassReinforcementModal — additional confirmation before entering bypassPermissions (FR-022).
//
// Source: docs/wireframes/ui-c-permission.mjs § C.5 (ModeSwitch / BorderedNotice)
// CC reference: .references/claude-code-sourcemap/restored-src/src/components/BypassPermissionsModeDialog.tsx (Claude Code 2.1.88, research-use)
// KOSMOS adaptation: displays the Korean reinforcement text from i18n bundle;
//   consumes Y/N keybinding from the Confirmation context (matching CC bypass dialog);
//   onConfirm / onCancel props let the caller (REPL.tsx) apply or revert the mode change.

import React from 'react'
import { Box, Text, useInput } from 'ink'
import { useUiL2I18n } from '../../i18n/uiL2.js'

export interface BypassReinforcementModalProps {
  /** Called when the citizen presses Y to confirm bypass mode. */
  onConfirm: () => void
  /** Called when the citizen presses N or Escape to cancel. */
  onCancel: () => void
}

/**
 * Reinforcement confirmation modal for bypassPermissions mode entry.
 *
 * Matches ui-c-permission.mjs § C.5 BorderedNotice visual:
 *   - Red border + "⚠ bypassPermissions 전환 확인" label
 *   - Warning body text (from i18n bundle)
 *   - [Y] 확정 / [N] 취소
 *
 * FR-022: "bypassPermissions mode requires an additional reinforcement-confirmation
 * modal when the citizen attempts to enter bypassPermissions mode."
 */
export function BypassReinforcementModal({
  onConfirm,
  onCancel,
}: BypassReinforcementModalProps): React.ReactElement {
  const i18n = useUiL2I18n()

  useInput((input, key) => {
    if (input === 'y' || input === 'Y' || key.return) {
      onConfirm()
    } else if (input === 'n' || input === 'N' || key.escape) {
      onCancel()
    }
  })

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor="#f87171"
      paddingX={2}
      paddingY={1}
      width={60}
    >
      {/* Header */}
      <Box flexDirection="row" gap={1}>
        <Text color="#f87171" bold>
          ⚠
        </Text>
        <Text bold>bypassPermissions 전환 확인</Text>
      </Box>

      {/* Warning body */}
      <Box marginTop={1}>
        <Text>{i18n.bypassReinforcement}</Text>
      </Box>

      {/* Y / N choice (FR-022) */}
      <Box marginTop={1} flexDirection="row" gap={2}>
        <Text>
          <Text color="#a78bfa" bold>
            Y{' '}
          </Text>
          <Text>확정</Text>
        </Text>
        <Text>
          <Text color="#a78bfa" bold>
            N{' '}
          </Text>
          <Text>취소</Text>
        </Text>
      </Box>
    </Box>
  )
}
