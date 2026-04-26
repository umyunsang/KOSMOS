// SPDX-License-Identifier: Apache-2.0
// KOSMOS-1633 — context-collapse minimal stub.
//
// Original CC module instrumented Anthropic-internal token-budget collapse
// telemetry (TokenWarning component subscribes to a stats stream). KOSMOS
// uses Spec 027 mailbox + Spec 028 OTLP collector for budget tracking;
// the in-process subscriber is a no-op stream that satisfies the consumer's
// `getStats()` / `subscribe()` shape.

export interface ContextCollapseStats {
  readonly tokensUsed: number
  readonly budgetTokens: number
  readonly collapseCount: number
  readonly lastCollapseAt: number | null
}

const ZERO_STATS: ContextCollapseStats = Object.freeze({
  tokensUsed: 0,
  budgetTokens: 0,
  collapseCount: 0,
  lastCollapseAt: null,
})

export function getStats(): ContextCollapseStats {
  return ZERO_STATS
}

export function subscribe(_listener: (stats: ContextCollapseStats) => void): () => void {
  // No-op subscription — the listener will never fire because KOSMOS does
  // not run in-process token-budget collapse. Returns an idempotent
  // unsubscribe handle.
  return () => {}
}
