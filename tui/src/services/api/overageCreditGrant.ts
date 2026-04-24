// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.

export function formatGrantAmount(_cents: number): string {
  return '$0.00'
}

export function getCachedOverageCreditGrant(): null {
  return null
}

export function invalidateOverageCreditGrantCache(): void {
  /* no-op */
}

export async function refreshOverageCreditGrantCache(): Promise<void> {
  /* no-op */
}
