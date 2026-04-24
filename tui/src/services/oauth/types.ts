// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.

export type BillingType = 'free' | 'pro' | 'enterprise' | 'unknown'
export type SubscriptionType = 'free' | 'pro' | 'max' | 'team' | 'enterprise'

export interface OAuthTokens {
  readonly accessToken: string
  readonly refreshToken?: string
}

export interface ReferrerRewardInfo {
  readonly amountCents: number
}

export interface ReferralEligibilityResponse {
  readonly eligible: boolean
}

export interface ReferralRedemptionsResponse {
  readonly redemptions: readonly ReferrerRewardInfo[]
}
