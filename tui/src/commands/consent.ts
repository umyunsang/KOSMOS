// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — US2 T032 + T033
// /consent list — reverse-chronological receipt table (FR-019).
// /consent revoke <rcpt-id> — idempotent revoke with confirmation (FR-020/021).
//
// CC reference: .references/claude-code-sourcemap/restored-src/src/components/HistorySearchDialog.tsx (table layout, Claude Code 2.1.88, research-use)
// KOSMOS adaptation: reads from PermissionReceiptContext (in-session read model);
//   revoke triggers a confirmation flow before calling revokeReceipt.
//   The TUI never writes the audit ledger directly — revoke goes through IPC
//   to the Spec 033 Python permission service (data flow described in consentBridge.ts).

import type { PermissionReceiptT } from '../schemas/ui-l2/permission.js'
import type { PermissionReceiptContextValue } from '../context/PermissionReceiptContext.js'
import { getUiL2I18n } from '../i18n/uiL2.js'

// ---------------------------------------------------------------------------
// /consent list (FR-019)
// ---------------------------------------------------------------------------

export interface ConsentListRow {
  receipt_id: string
  layer: 1 | 2 | 3
  tool_name: string
  decision: string
  decided_at: string
  revoked_at: string | null
}

/**
 * Build the table rows for `/consent list` output.
 *
 * Returns receipts in reverse chronological order (newest first) per FR-019.
 * Caller renders the rows (as a table or plain text list).
 */
export function buildConsentListRows(
  receipts: readonly PermissionReceiptT[],
): ConsentListRow[] {
  return [...receipts]
    .sort((a, b) => b.decided_at.localeCompare(a.decided_at))
    .map((r) => ({
      receipt_id: r.receipt_id,
      layer: r.layer,
      tool_name: r.tool_name,
      decision: r.decision,
      decided_at: r.decided_at,
      revoked_at: r.revoked_at,
    }))
}

/**
 * Format a single ConsentListRow as a human-readable line.
 * Used when rendering to plain terminal output.
 * Matches the ui-c-permission.mjs § C.3 ConsentHistory table columns:
 *   rcpt-<id> | layer | tool | decision | timestamp
 */
export function formatConsentListRow(row: ConsentListRow): string {
  const revoked = row.revoked_at ? ' [REVOKED]' : ''
  const ts = row.decided_at.slice(0, 19).replace('T', ' ') // "YYYY-MM-DD HH:MM:SS"
  return `${row.receipt_id}  L${row.layer}  ${row.tool_name}  ${row.decision}${revoked}  ${ts}`
}

// ---------------------------------------------------------------------------
// /consent revoke (FR-020 + FR-021)
// ---------------------------------------------------------------------------

export type RevokeResult =
  | { kind: 'revoked'; receiptId: string }
  | { kind: 'already_revoked'; receiptId: string }
  | { kind: 'not_found'; receiptId: string }
  | { kind: 'invalid_id' }

/**
 * Execute the `/consent revoke rcpt-<id>` command.
 *
 * Validates the receipt ID format, then calls `ctx.revokeReceipt()`.
 * The caller is responsible for the confirmation modal step; this function
 * is called AFTER the citizen has confirmed.
 *
 * FR-020: prompts confirmation modal → on Y calls this function.
 * FR-021: if receipt already revoked, returns `already_revoked` and the
 *         caller shows "이미 철회됨" toast (no new ledger entry).
 *
 * The actual ledger write happens asynchronously via IPC (consentBridge.ts);
 * the `revoked_at` field is set optimistically in-memory here for display.
 */
export function executeConsentRevoke(
  receiptId: string,
  ctx: Pick<PermissionReceiptContextValue, 'revokeReceipt'>,
): RevokeResult {
  // Validate format.
  if (!/^rcpt-[A-Za-z0-9_-]{8,}$/.test(receiptId)) {
    return { kind: 'invalid_id' }
  }

  const outcome = ctx.revokeReceipt(receiptId)
  return { kind: outcome, receiptId }
}

// ---------------------------------------------------------------------------
// Helper: build confirmation prompt text for revoke (FR-020)
// ---------------------------------------------------------------------------

/**
 * Returns the confirmation prompt text shown to the citizen before
 * executing a revoke.  Locale-aware via uiL2I18n.
 */
export function buildRevokeConfirmText(
  receiptId: string,
  locale: 'ko' | 'en' = 'ko',
): string {
  const i18n = getUiL2I18n(locale)
  // Use the consentRevoked string with a "confirm?" suffix appropriate for the locale.
  const base = i18n.consentRevoked(receiptId)
  return locale === 'ko'
    ? `${receiptId} 을(를) 철회하시겠습니까? (Y/N)`
    : `Revoke ${receiptId}? (Y/N)`
}

// ---------------------------------------------------------------------------
// Helper: /consent subcommand router
// ---------------------------------------------------------------------------

export type ConsentSubcommand =
  | { sub: 'list' }
  | { sub: 'revoke'; receiptId: string }
  | { sub: 'unknown'; raw: string }

/**
 * Parse `/consent <args>` into a typed subcommand discriminated union.
 */
export function parseConsentArgs(args: string): ConsentSubcommand {
  const trimmed = args.trim()
  if (trimmed === 'list') return { sub: 'list' }
  const revokeMatch = /^revoke\s+(rcpt-[A-Za-z0-9_-]+)$/.exec(trimmed)
  if (revokeMatch?.[1]) return { sub: 'revoke', receiptId: revokeMatch[1] }
  return { sub: 'unknown', raw: trimmed }
}
