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

export type SDKControlCancelRequest = any;
export const SDKControlCancelRequest: any = __stub;
export type SDKControlInitializeRequest = any;
export const SDKControlInitializeRequest: any = __stub;
export type SDKControlInitializeResponse = any;
export const SDKControlInitializeResponse: any = __stub;
export type SDKControlMcpSetServersResponse = any;
export const SDKControlMcpSetServersResponse: any = __stub;
export type SDKControlPermissionRequest = any;
export const SDKControlPermissionRequest: any = __stub;
export type SDKControlReloadPluginsResponse = any;
export const SDKControlReloadPluginsResponse: any = __stub;
export type SDKControlRequest = any;
export const SDKControlRequest: any = __stub;
export type SDKControlRequestInner = any;
export const SDKControlRequestInner: any = __stub;
export type SDKControlResponse = any;
export const SDKControlResponse: any = __stub;
export type SDKPartialAssistantMessage = any;
export const SDKPartialAssistantMessage: any = __stub;
export type StdinMessage = any;
export const StdinMessage: any = __stub;
export type StdoutMessage = any;
export const StdoutMessage: any = __stub;

export default __stub;
