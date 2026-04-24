// [P0 reconstructed · rebuild-stubs.ts · symbol-complete stub]
// Aggregated from every consumer import across src/.
/* eslint-disable @typescript-eslint/no-explicit-any */

const __noop = (..._args: unknown[]): any => undefined as any;
const __stub: any = new Proxy(function () {} as any, {
  get: (_t, p) => (p === 'then' ? undefined : __stub),
  apply: () => __stub,
  construct: () => __stub,
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
