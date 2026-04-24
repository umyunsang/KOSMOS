// [P0 reconstructed · rebuild-stubs.ts · symbol-complete stub]
// Aggregated from every consumer import across src/.
/* eslint-disable @typescript-eslint/no-explicit-any */

const __noop = (..._args: unknown[]): any => undefined as any;
const __stub: any = new Proxy(function () {} as any, {
  get: (_t, p) => (p === 'then' ? undefined : __stub),
  apply: () => __stub,
  construct: () => __stub,
});

export const getNativeCSIuTerminalDisplayName: any = __noop;
export const hasUsedBackslashReturn: any = __noop;
export const isShiftEnterKeyBindingInstalled: any = __noop;
export const markBackslashReturnUsed: any = __noop;
export const setupTerminal: any = __noop;
export const shouldOfferTerminalSetup: any = __noop;

export default __stub;
