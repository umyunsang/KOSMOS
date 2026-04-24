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

export type AttributionSnapshotMessage = any;
export const AttributionSnapshotMessage: any = __stub;
export type ContentReplacementEntry = any;
export const ContentReplacementEntry: any = __stub;
export type ContextCollapseCommitEntry = any;
export const ContextCollapseCommitEntry: any = __stub;
export type ContextCollapseSnapshotEntry = any;
export const ContextCollapseSnapshotEntry: any = __stub;
export type Entry = any;
export const Entry: any = __stub;
export type FileAttributionState = any;
export const FileAttributionState: any = __stub;
export type FileHistorySnapshotMessage = any;
export const FileHistorySnapshotMessage: any = __stub;
export type LogOption = any;
export const LogOption: any = __stub;
export type PersistedWorktreeSession = any;
export const PersistedWorktreeSession: any = __stub;
export type SerializedMessage = any;
export const SerializedMessage: any = __stub;
export type SpeculationAcceptMessage = any;
export const SpeculationAcceptMessage: any = __stub;
export type TranscriptMessage = any;
export const TranscriptMessage: any = __stub;
export const sortLogs: any = __noop;

export default __stub;
