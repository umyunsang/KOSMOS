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

export type AnyZodRawShape = any;
export const AnyZodRawShape: any = __stub;
export type EffortLevel = any;
export const EffortLevel: any = __stub;
export type ForkSessionOptions = any;
export const ForkSessionOptions: any = __stub;
export type ForkSessionResult = any;
export const ForkSessionResult: any = __stub;
export type GetSessionInfoOptions = any;
export const GetSessionInfoOptions: any = __stub;
export type GetSessionMessagesOptions = any;
export const GetSessionMessagesOptions: any = __stub;
export type InferShape = any;
export const InferShape: any = __stub;
export type InternalOptions = any;
export const InternalOptions: any = __stub;
export type InternalQuery = any;
export const InternalQuery: any = __stub;
export type ListSessionsOptions = any;
export const ListSessionsOptions: any = __stub;
export type McpSdkServerConfigWithInstance = any;
export const McpSdkServerConfigWithInstance: any = __stub;
export type Options = any;
export const Options: any = __stub;
export type Query = any;
export const Query: any = __stub;
export type SDKSession = any;
export const SDKSession: any = __stub;
export type SDKSessionOptions = any;
export const SDKSessionOptions: any = __stub;
export type SdkMcpToolDefinition = any;
export const SdkMcpToolDefinition: any = __stub;
export type SessionMessage = any;
export const SessionMessage: any = __stub;
export type SessionMutationOptions = any;
export const SessionMutationOptions: any = __stub;

export default __stub;
