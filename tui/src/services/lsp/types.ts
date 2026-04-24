// [P0 reconstructed · rebuild-stubs.ts · symbol-complete stub]
// Aggregated from every consumer import across src/.
/* eslint-disable @typescript-eslint/no-explicit-any */

const __noop = (..._args: unknown[]): any => undefined as any;
const __stub: any = new Proxy(function () {} as any, {
  get: (_t, p) => (p === 'then' ? undefined : __stub),
  apply: () => __stub,
  construct: () => __stub,
});

export type LspServerConfig = any;
export const LspServerConfig: any = __stub;
export type LspServerState = any;
export const LspServerState: any = __stub;
export type ScopedLspServerConfig = any;
export const ScopedLspServerConfig: any = __stub;

export default __stub;
