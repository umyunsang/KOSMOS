// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.

export interface RateLimit {
  readonly remaining: number
  readonly limit: number
  readonly resetAt: number
}

export interface ExtraUsage {
  readonly [key: string]: unknown
}

export interface Utilization {
  readonly rateLimits: readonly RateLimit[]
  readonly extra: ExtraUsage
}

const EMPTY_UTILIZATION: Utilization = {
  rateLimits: [],
  extra: {},
}

export async function fetchUtilization(): Promise<Utilization> {
  return EMPTY_UTILIZATION
}
