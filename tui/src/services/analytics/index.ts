// [P0 reconstructed · rebuild-stubs.ts · symbol-complete stub]
// Aggregated from every consumer import across src/.
/* eslint-disable @typescript-eslint/no-explicit-any */

const __noop = (..._args: unknown[]): any => undefined as any;
const __stub: any = new Proxy(function () {} as any, {
  get: (_t, p) => (p === 'then' ? undefined : __stub),
  apply: () => __stub,
  construct: () => __stub,
});

export type AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS = any;
export const AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS: any = __stub;
export type AnalyticsMetadata_I_VERIFIED_THIS_IS_PII_TAGGED = any;
export const AnalyticsMetadata_I_VERIFIED_THIS_IS_PII_TAGGED: any = __stub;
export const attachAnalyticsSink: any = __noop;
export const logEvent: any = __noop;
export const logEventAsync: any = __noop;
export const stripProtoFields: any = __noop;

export default __stub;
