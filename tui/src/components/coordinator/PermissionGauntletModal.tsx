// Source: .references/claude-code-sourcemap/restored-src/src/components/permissions/WorkerPendingPermission.tsx (Claude Code 2.1.88, research-use)
// Source: .references/claude-code-sourcemap/restored-src/src/components/BypassPermissionsModeDialog.tsx (Claude Code 2.1.88, research-use)
// Note: Original attribution listed ToolPermission*.tsx wildcard which does not resolve in restored-src.
//       WorkerPendingPermission.tsx is the closest upstream analog for the worker-scoped permission modal pattern.
// KOSMOS adaptation: renders PermissionRequest from session-store; emits PermissionResponseFrame on y/n.

import React from 'react'
import { Box, Text, useInput } from 'ink'
import { useTheme } from '../../theme/provider'
import { useI18n } from '../../i18n'
import { useSessionStore, dispatchSessionAction } from '../../store/session-store'
import type { PermissionResponseFrame } from '../../ipc/frames.generated'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface PermissionGauntletModalProps {
  /** DI: never imports bridge directly. Caller provides sendFrame. */
  sendFrame: (frame: PermissionResponseFrame) => void
  /** Session ID needed to build the response frame header. */
  sessionId: string
}

// ---------------------------------------------------------------------------
// Risk level helpers (KOSMOS-original; no hex — uses theme tokens)
// ---------------------------------------------------------------------------

type RiskLevel = 'low' | 'medium' | 'high'

function riskColor(level: RiskLevel, theme: ReturnType<typeof useTheme>): string {
  switch (level) {
    case 'high':
      return theme.error
    case 'medium':
      return theme.warning
    case 'low':
    default:
      return theme.success
  }
}

// ---------------------------------------------------------------------------
// PermissionGauntletModal
// ---------------------------------------------------------------------------

/**
 * Modal-style permission dialog.
 *
 * Renders when pending_permission is set in the session store.
 * Blocks all other input by consuming y/n keystrokes exclusively.
 * Emits a PermissionResponseFrame via the injected sendFrame prop (FR-046).
 *
 * Component is selector-isolated: subscribes only to pending_permission.
 */
export function PermissionGauntletModal({
  sendFrame,
  sessionId,
}: PermissionGauntletModalProps): React.ReactElement | null {
  const theme = useTheme()
  const i18n = useI18n()
  // Subscribe directly to avoid hook-composition issues with useSyncExternalStore
  // across module boundaries in test environments.
  const pendingRequest = useSessionStore((s) => s.pending_permission)

  function grant(): void {
    dispatchSessionAction({ type: 'PERMISSION_RESPONSE' })
  }

  function deny(): void {
    dispatchSessionAction({ type: 'PERMISSION_RESPONSE' })
  }

  // useInput is registered on every render to preserve hook order, but active
  // only while the permission modal is open.
  // All keystrokes are swallowed here, blocking the outer input buffer.
  useInput((input, key) => {
    if (pendingRequest == null) return
    if (input === 'y' || input === 'Y') {
      grant()
      sendFrame({
        session_id: sessionId,
        correlation_id: pendingRequest.correlation_id,
        ts: new Date().toISOString(),
        role: 'tui',
        kind: 'permission_response',
        request_id: pendingRequest.request_id,
        decision: 'granted',
      })
    } else if (input === 'n' || input === 'N' || key.escape) {
      deny()
      sendFrame({
        session_id: sessionId,
        correlation_id: pendingRequest.correlation_id,
        ts: new Date().toISOString(),
        role: 'tui',
        kind: 'permission_response',
        request_id: pendingRequest.request_id,
        decision: 'denied',
      })
    }
    // All other keys are consumed (blocked) intentionally.
  }, { isActive: pendingRequest != null })

  // When no pending request, render nothing (modal closed).
  if (pendingRequest == null) return null

  const riskBorderColor = riskColor(pendingRequest.risk_level, theme)

  return (
    <Box
      borderStyle="round"
      borderColor={riskBorderColor}
      flexDirection="column"
      paddingX={2}
      paddingY={1}
      marginY={1}
    >
      {/* Title row */}
      <Box marginBottom={1}>
        <Text bold color={theme.permission}>
          {i18n.permissionPromptTitle}
        </Text>
        <Text color={theme.subtle}>{' — '}</Text>
        <Text color={riskBorderColor}>{pendingRequest.risk_level.toUpperCase()}</Text>
      </Box>

      {/* Bilingual description */}
      <Box flexDirection="column" marginBottom={1}>
        <Text color={theme.text}>{pendingRequest.description_ko}</Text>
        <Text color={theme.subtle}>{pendingRequest.description_en}</Text>
      </Box>

      {/* Primitive + worker context */}
      <Box marginBottom={1}>
        <Text color={theme.inactive}>primitive: </Text>
        <Text color={theme.text}>{pendingRequest.primitive_kind}</Text>
        <Text color={theme.inactive}>{'  worker: '}</Text>
        <Text color={theme.text}>{pendingRequest.worker_id}</Text>
      </Box>

      {/* y/n prompt */}
      <Box>
        <Text color={theme.permission}>
          {i18n.permissionPromptBody(pendingRequest.primitive_kind)}
        </Text>
        <Text color={theme.success}>{' [y] '}</Text>
        <Text color={theme.subtle}>{i18n.permissionApproved}</Text>
        <Text color={theme.inactive}>{'  '}</Text>
        <Text color={theme.error}>{' [n] '}</Text>
        <Text color={theme.subtle}>{i18n.permissionDenied}</Text>
      </Box>
    </Box>
  )
}
