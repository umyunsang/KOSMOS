// [P0 reconstructed · rebuild-stubs.ts · symbol-complete stub]
// Aggregated from every consumer import across src/.
/* eslint-disable @typescript-eslint/no-explicit-any */

const __noop = (..._args: unknown[]): any => undefined as any;
const __stub: any = new Proxy(function () {} as any, {
  get: (_t, p) => (p === 'then' ? undefined : __stub),
  apply: () => __stub,
  construct: () => __stub,
});

export type Diagnostic = any;
export const Diagnostic: any = __stub;
export type Property = any;
export const Property: any = __stub;
export const buildAPIProviderProperties: any = __noop;
export const buildAccountProperties: any = __noop;
export const buildIDEProperties: any = __noop;
export const buildInstallationDiagnostics: any = __noop;
export const buildInstallationHealthDiagnostics: any = __noop;
export const buildMcpProperties: any = __noop;
export const buildMemoryDiagnostics: any = __noop;
export const buildSandboxProperties: any = __noop;
export const buildSettingSourcesProperties: any = __noop;
export const getModelDisplayLabel: any = __noop;

export default __stub;
