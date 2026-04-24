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
