// [P0 reconstructed · Pass 3 · referral / guest-passes]
// Original CC module: referral API (guest passes, referrer rewards).
// KOSMOS disables this entirely — no referral, no passes — but functions
// must return SHAPED objects because consumers destructure them.
// (Destructuring `null` → runtime TypeError → Ink error boundary.)
/* eslint-disable @typescript-eslint/no-explicit-any */

/** Eligibility check result — consumer destructures `{ eligible, hasCache }`. */
export interface PassesEligibility {
  eligible: boolean
  hasCache: boolean
}

export function checkCachedPassesEligibility(): PassesEligibility {
  return { eligible: false, hasCache: false }
}

export async function getCachedOrFetchPassesEligibility(): Promise<PassesEligibility> {
  return { eligible: false, hasCache: false }
}

export async function prefetchPassesEligibility(): Promise<void> {
  // No-op: FR-008 bootstrap egress 0
}

export async function fetchReferralRedemptions(): Promise<unknown[]> {
  return []
}

export function formatCreditAmount(cents: number): string {
  const dollars = Math.abs(cents) / 100
  return `$${dollars.toFixed(2)}`
}

export function getCachedReferrerReward(): { cents: number } | null {
  return null
}

export function getCachedRemainingPasses(): number {
  return 0
}

export default undefined as any
