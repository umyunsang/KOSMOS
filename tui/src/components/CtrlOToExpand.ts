// [P0 reconstructed · rebuild-stubs.ts · symbol-complete stub]
// Aggregated from every consumer import across src/.
/* eslint-disable @typescript-eslint/no-explicit-any */

const __noop = (..._args: unknown[]): any => undefined as any;
const __stub: any = new Proxy(function () {} as any, {
  get: (_t, p) => (p === 'then' ? undefined : __stub),
  apply: () => __stub,
  construct: () => __stub,
});

export type CtrlOToExpand = any;
export const CtrlOToExpand: any = __stub;
export type SubAgentProvider = any;
export const SubAgentProvider: any = __stub;
export const ctrlOToExpand: any = __noop;

export default __stub;
