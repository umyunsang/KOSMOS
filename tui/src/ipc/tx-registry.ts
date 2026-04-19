// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Spec 032 WS3 T044
//
// Client-side transaction registry for TUI-side idempotency (FR-026, FR-032).
//
// Responsibilities:
//   - getOrMint(submitKey): return existing transaction_id for this submitKey,
//     or mint a fresh UUIDv7 and store it (no re-mint on duplicate click).
//   - onResponseReceived(transactionId): clear the entry once the backend has
//     confirmed or rejected the submission, freeing memory.
//   - peek(submitKey): read-only lookup — returns undefined on miss.
//
// Submit key convention (callers decide):
//   `${sessionId}:${toolId}:${stableParamsHash}` — ensures that a user
//   double-clicking "submit" for the same action and the same parameters gets
//   the same transaction_id. A genuinely different action must use a fresh key.
//
// Security properties:
//   - UUIDv7 minted with crypto.randomUUID() base + ms-precision timestamp
//     prepend (envelope.ts makeUUIDv7) — unpredictable, monotonic, sortable.
//   - The registry is session-scoped (in-memory); no cross-session correlation.
//   - Entries survive until explicitly cleared by onResponseReceived — this
//     is intentional: a network timeout should not cause a re-mint that would
//     bypass the backend's idempotency check.
//
// Usage:
//   const reg = new TxRegistry()
//   const txId = reg.getOrMint(`${sessionId}:submit:${hash}`)
//   // ... send IPC frame with transaction_id = txId
//   // on response:
//   reg.onResponseReceived(txId)

import { makeUUIDv7 } from './envelope'

// ---------------------------------------------------------------------------
// TxRegistryEntry
// ---------------------------------------------------------------------------

export interface TxRegistryEntry {
  /** The UUIDv7 minted for this submit key. */
  transactionId: string
  /** Wall-clock ms when the entry was first created. */
  mintedAtMs: number
}

// ---------------------------------------------------------------------------
// TxRegistry
// ---------------------------------------------------------------------------

/**
 * Client-side idempotency registry: mint once per unique submit key,
 * return the same transaction_id on duplicate clicks.
 *
 * Thread-safety: Single-threaded JS — no locking required.
 */
export class TxRegistry {
  /** submitKey → TxRegistryEntry */
  private readonly _byKey: Map<string, TxRegistryEntry> = new Map()
  /** transactionId → submitKey (reverse index for onResponseReceived) */
  private readonly _byTxId: Map<string, string> = new Map()

  /**
   * Return the existing transaction_id for *submitKey*, or mint a new UUIDv7
   * and store it.
   *
   * Idempotency guarantee: multiple calls with the same *submitKey* return the
   * same ``transactionId`` until ``onResponseReceived`` clears it.
   *
   * @param submitKey - Caller-chosen stable key (e.g. `${sessionId}:${toolId}:${paramsHash}`)
   * @returns The transaction_id to embed in the IPC frame.
   */
  getOrMint(submitKey: string): string {
    const existing = this._byKey.get(submitKey)
    if (existing !== undefined) {
      return existing.transactionId
    }

    const transactionId = makeUUIDv7()
    const entry: TxRegistryEntry = {
      transactionId,
      mintedAtMs: Date.now(),
    }
    this._byKey.set(submitKey, entry)
    this._byTxId.set(transactionId, submitKey)
    return transactionId
  }

  /**
   * Read-only lookup.  Returns ``undefined`` on miss.
   *
   * Does NOT mint a new entry.  Use for inspection only.
   */
  peek(submitKey: string): TxRegistryEntry | undefined {
    return this._byKey.get(submitKey)
  }

  /**
   * Clear the entry once the backend confirms or rejects the submission.
   *
   * After this call, the next ``getOrMint(submitKey)`` will mint a fresh
   * UUIDv7 — allowing legitimate re-submission after a confirmed outcome.
   *
   * If *transactionId* is unknown (already cleared or never minted here),
   * this is a no-op.
   *
   * @param transactionId - The UUIDv7 from the backend's tool_result frame.
   */
  onResponseReceived(transactionId: string): void {
    const submitKey = this._byTxId.get(transactionId)
    if (submitKey === undefined) {
      return // already cleared or never registered here
    }
    this._byKey.delete(submitKey)
    this._byTxId.delete(transactionId)
  }

  /**
   * Number of pending (unconfirmed) transactions currently tracked.
   * Useful for test assertions and debug rendering.
   */
  get pendingCount(): number {
    return this._byKey.size
  }

  /**
   * Drain all pending entries.  Use only in tests or on session teardown.
   */
  clear(): void {
    this._byKey.clear()
    this._byTxId.clear()
  }
}
