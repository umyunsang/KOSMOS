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

export type AgentToolProgress = any;
export const AgentToolProgress: any = __stub;
export type BashProgress = any;
export const BashProgress: any = __stub;
export type MCPProgress = any;
export const MCPProgress: any = __stub;
export type PowerShellProgress = any;
export const PowerShellProgress: any = __stub;
export type REPLToolProgress = any;
export const REPLToolProgress: any = __stub;
export type SdkWorkflowProgress = any;
export const SdkWorkflowProgress: any = __stub;
export type ShellProgress = any;
export const ShellProgress: any = __stub;
export type SkillToolProgress = any;
export const SkillToolProgress: any = __stub;
export type TaskOutputProgress = any;
export const TaskOutputProgress: any = __stub;
export type ToolProgressData = any;
export const ToolProgressData: any = __stub;
export type WebSearchProgress = any;
export const WebSearchProgress: any = __stub;

export default __stub;
