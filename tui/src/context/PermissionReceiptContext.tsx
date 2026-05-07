// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — US2 T031
// PermissionReceiptContext — in-session receipt registry + revoke surface (FR-018/019).
//
// CC reference: .references/claude-code-sourcemap/restored-src/src/context/notifications.tsx (Claude Code 2.1.88, research-use)
// KOSMOS adaptation: manages append-only in-session PermissionReceipt array;
//   exposes addReceipt / revokeReceipt / listReceipts for /consent list + revoke.
//   The TUI NEVER writes the audit ledger directly — all writes go through the
//   existing IPC envelope to the Python permission service (Spec 033).
//   This context is the READ model for /consent list and the surface for receipt
//   ID toasting (FR-018).

import React, {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from 'react'
import {
  isReceiptRevoked,
  type PermissionReceiptT,
} from '../schemas/ui-l2/permission.js'

// ---------------------------------------------------------------------------
// Context shape
// ---------------------------------------------------------------------------

export interface PermissionReceiptContextValue {
  /** All receipts for the current session (append-only, reverse chronological). */
  receipts: readonly PermissionReceiptT[]

  /**
   * Append a new receipt.  Called after the backend IPC confirms the decision
   * and returns the receipt_id.  FR-018.
   */
  addReceipt: (receipt: PermissionReceiptT) => void

  /**
   * Mark a receipt as revoked (set revoked_at).
   *
   * Returns:
   *   'revoked'         — first-time revoke succeeded.
   *   'already_revoked' — receipt was already revoked (FR-021 idempotent).
   *   'not_found'       — receipt_id does not exist in the current session.
   *
   * The TUI never creates a new ledger entry on 'already_revoked'; it only
   * shows the "이미 철회됨" toast (FR-021).
   */
  revokeReceipt: (
    receiptId: string,
  ) => 'revoked' | 'already_revoked' | 'not_found'

  /**
   * Returns receipts in reverse chronological order by decided_at.
   * Used by /consent list (FR-019).
   */
  listReceipts: () => PermissionReceiptT[]
}

// ---------------------------------------------------------------------------
// Context + default value
// ---------------------------------------------------------------------------

const PermissionReceiptContext =
  createContext<PermissionReceiptContextValue | null>(null)

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export interface PermissionReceiptProviderProps {
  children: ReactNode
}

export function PermissionReceiptProvider({
  children,
}: PermissionReceiptProviderProps): React.ReactElement {
  const [receipts, setReceipts] = useState<PermissionReceiptT[]>([])

  const addReceipt = useCallback((receipt: PermissionReceiptT) => {
    setReceipts((prev) => [receipt, ...prev])
  }, [])

  const revokeReceipt = useCallback(
    (receiptId: string): 'revoked' | 'already_revoked' | 'not_found' => {
      let result: 'revoked' | 'already_revoked' | 'not_found' = 'not_found'

      setReceipts((prev) => {
        const idx = prev.findIndex((r) => r.receipt_id === receiptId)
        if (idx === -1) {
          result = 'not_found'
          return prev
        }
        const existing = prev[idx]!
        if (isReceiptRevoked(existing)) {
          result = 'already_revoked'
          return prev // no mutation, idempotent (FR-021)
        }
        result = 'revoked'
        const updated: PermissionReceiptT = {
          ...existing,
          revoked_at: new Date().toISOString(),
        }
        const next = [...prev]
        next[idx] = updated
        return next
      })

      return result
    },
    [],
  )

  const listReceipts = useCallback((): PermissionReceiptT[] => {
    // Return a copy sorted reverse chronological (newest first) by decided_at.
    return [...receipts].sort((a, b) =>
      b.decided_at.localeCompare(a.decided_at),
    )
  }, [receipts])

  const value: PermissionReceiptContextValue = {
    receipts,
    addReceipt,
    revokeReceipt,
    listReceipts,
  }

  return (
    <PermissionReceiptContext.Provider value={value}>
      {children}
    </PermissionReceiptContext.Provider>
  )
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Consume the PermissionReceiptContext.
 * Must be used inside a <PermissionReceiptProvider>.
 */
export function usePermissionReceipts(): PermissionReceiptContextValue {
  const ctx = useContext(PermissionReceiptContext)
  if (ctx === null) {
    throw new Error(
      'usePermissionReceipts must be used inside <PermissionReceiptProvider>',
    )
  }
  return ctx
}
