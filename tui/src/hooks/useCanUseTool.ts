// Source: .references/claude-code-sourcemap/restored-src/src/hooks/useCanUseTool.tsx (Claude Code 2.1.88, research-use)
// KOSMOS adaptation: returns { pendingRequest, grant, deny } against KOSMOS session-store
// instead of Anthropic tool-use approval flow. Hook is consumed by PermissionGauntletModal.

import { useSessionStore, dispatchSessionAction } from '../store/session-store'
import type { PermissionRequest } from '../store/session-store'

export interface CanUseToolResult {
  /** The currently pending permission request, or null if none. */
  pendingRequest: PermissionRequest | null
  /** Grant the pending permission. Clears pending_permission in the store. */
  grant: () => void
  /** Deny the pending permission. Clears pending_permission in the store. */
  deny: () => void
}

/**
 * Lifted from restored-src/src/hooks/useCanUseTool.tsx pattern.
 *
 * Returns the current pending permission request from the session store
 * and stable grant/deny callbacks that dispatch PERMISSION_RESPONSE.
 *
 * Note: The actual reducer side-effect (clearing pending_permission) is
 * already handled by the PERMISSION_RESPONSE case in session-store.ts.
 * The IPC send of PermissionResponseFrame is done by PermissionGauntletModal
 * via its sendFrame prop (DI pattern — this hook does not touch the bridge).
 */
export function useCanUseTool(): CanUseToolResult {
  const pendingRequest = useSessionStore((s) => s.pending_permission)

  function grant(): void {
    dispatchSessionAction({ type: 'PERMISSION_RESPONSE' })
  }

  function deny(): void {
    dispatchSessionAction({ type: 'PERMISSION_RESPONSE' })
  }

  return { pendingRequest, grant, deny }
}
