// [P0 reconstructed · rebuild-stubs.ts · symbol-complete stub]
// Aggregated from every consumer import across src/.
/* eslint-disable @typescript-eslint/no-explicit-any */

const __noop = (..._args: unknown[]): any => undefined as any;
const __stub: any = new Proxy(function () {} as any, {
  get(_t, p) {
    if (p === Symbol.toPrimitive) return () => ""
    if (p === Symbol.iterator) return function* () {}
    if (p === Symbol.asyncIterator) return async function* () {}
    if (p === Symbol.toStringTag) return "Stub"
    if (p === Symbol.for("nodejs.util.inspect.custom")) return () => "<Stub>"
    if (p === "inspect") return () => "<Stub>"
    if (p === "then") return undefined
    if (p === "toString") return () => ""
    if (p === "valueOf") return () => undefined
    if (p === "toJSON") return () => null
    if (p === "length") return 0
    if (p === "name") return "Stub"
    if (p === "message") return ""
    if (p === "stack") return ""
    if (p === "constructor") return Object
    return __stub
  },
  apply() { return __stub },
  construct() { return __stub },
});

export type BillingType = any;
export const BillingType: any = __stub;
export type OAuthProfileResponse = any;
export const OAuthProfileResponse: any = __stub;
export type OAuthTokenExchangeResponse = any;
export const OAuthTokenExchangeResponse: any = __stub;
export type OAuthTokens = any;
export const OAuthTokens: any = __stub;
export type RateLimitTier = any;
export const RateLimitTier: any = __stub;
export type ReferralEligibilityResponse = any;
export const ReferralEligibilityResponse: any = __stub;
export type ReferralRedemptionsResponse = any;
export const ReferralRedemptionsResponse: any = __stub;
export type ReferrerRewardInfo = any;
export const ReferrerRewardInfo: any = __stub;
export type SubscriptionType = any;
export const SubscriptionType: any = __stub;
export type UserRolesResponse = any;
export const UserRolesResponse: any = __stub;

export default __stub;
