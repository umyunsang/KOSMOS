// [P0 reconstructed · rebuild-stubs.ts · symbol-complete stub]
// Aggregated from every consumer import across src/.
/* eslint-disable @typescript-eslint/no-explicit-any */

const __noop = (..._args: unknown[]): any => undefined as any;
const __stub: any = new Proxy(function () {} as any, {
  get: (_t, p) => (p === 'then' ? undefined : __stub),
  apply: () => __stub,
  construct: () => __stub,
});

export const formatGrantAmount: any = __noop;
export const getCachedOverageCreditGrant: any = __noop;
export const invalidateOverageCreditGrantCache: any = __noop;
export const refreshOverageCreditGrantCache: any = __noop;

export default __stub;
