// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — US2 T029
// ReceiptToast — displays `rcpt-<id>` after every permission decision (FR-018).
//
// CC reference: .references/claude-code-sourcemap/restored-src/src/context/notifications.tsx (Claude Code 2.1.88, research-use)
// KOSMOS adaptation: renders receipt ID using the i18n bundle's receiptIssued/
//   consentRevoked/consentAlreadyRevoked strings; uses Ink Text with a subtle
//   dimColor envelope matching the CC toast visual style.

import React from 'react'
import { Box, Text } from 'ink'
import { useUiL2I18n } from '../../i18n/uiL2.js'

export type ReceiptToastVariant = 'issued' | 'revoked' | 'already_revoked'

export interface ReceiptToastProps {
  variant: ReceiptToastVariant
  /** Receipt ID to display (e.g. `rcpt-01943af2`). Required for `issued` and `revoked`. */
  receiptId?: string
}

/**
 * Toast message surfacing permission receipt events to the citizen.
 *
 * Variants:
 *   issued       — "발급됨 rcpt-<id>" (FR-018 after Y or A decision)
 *   revoked      — "철회 완료 rcpt-<id>" (FR-020 after confirmed revoke)
 *   already_revoked — "이미 철회됨" (FR-021 idempotent revoke)
 *
 * The component is intentionally stateless; the parent (PermissionReceiptContext)
 * drives the lifecycle (add/remove from notification queue).
 */
export function ReceiptToast({
  variant,
  receiptId,
}: ReceiptToastProps): React.ReactElement {
  const i18n = useUiL2I18n()

  let message: string
  switch (variant) {
    case 'issued':
      message = i18n.receiptIssued(receiptId ?? '')
      break
    case 'revoked':
      message = i18n.consentRevoked(receiptId ?? '')
      break
    case 'already_revoked':
      message = i18n.consentAlreadyRevoked
      break
    default:
      message = ''
  }

  return (
    <Box paddingX={1}>
      <Text color="#a78bfa" dimColor>
        {'✻ '}
      </Text>
      <Text>{message}</Text>
    </Box>
  )
}
