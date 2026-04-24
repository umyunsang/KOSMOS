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

export type AssistantMessage = any;
export const AssistantMessage: any = __stub;
export type AttachmentMessage = any;
export const AttachmentMessage: any = __stub;
export type CollapsedReadSearchGroup = any;
export const CollapsedReadSearchGroup: any = __stub;
export type CollapsibleMessage = any;
export const CollapsibleMessage: any = __stub;
export type CompactMetadata = any;
export const CompactMetadata: any = __stub;
export type GroupedToolUseMessage = any;
export const GroupedToolUseMessage: any = __stub;
export type HookResultMessage = any;
export const HookResultMessage: any = __stub;
export type Message = any;
export const Message: any = __stub;
export type MessageOrigin = any;
export const MessageOrigin: any = __stub;
export type NormalizedAssistantMessage = any;
export const NormalizedAssistantMessage: any = __stub;
export type NormalizedMessage = any;
export const NormalizedMessage: any = __stub;
export type NormalizedUserMessage = any;
export const NormalizedUserMessage: any = __stub;
export type PartialCompactDirection = any;
export const PartialCompactDirection: any = __stub;
export type ProgressMessage = any;
export const ProgressMessage: any = __stub;
export type RenderableMessage = any;
export const RenderableMessage: any = __stub;
export type RequestStartEvent = any;
export const RequestStartEvent: any = __stub;
export type StopHookInfo = any;
export const StopHookInfo: any = __stub;
export type StreamEvent = any;
export const StreamEvent: any = __stub;
export type SystemAPIErrorMessage = any;
export const SystemAPIErrorMessage: any = __stub;
export type SystemAgentsKilledMessage = any;
export const SystemAgentsKilledMessage: any = __stub;
export type SystemApiMetricsMessage = any;
export const SystemApiMetricsMessage: any = __stub;
export type SystemAwaySummaryMessage = any;
export const SystemAwaySummaryMessage: any = __stub;
export type SystemBridgeStatusMessage = any;
export const SystemBridgeStatusMessage: any = __stub;
export type SystemCompactBoundaryMessage = any;
export const SystemCompactBoundaryMessage: any = __stub;
export type SystemFileSnapshotMessage = any;
export const SystemFileSnapshotMessage: any = __stub;
export type SystemInformationalMessage = any;
export const SystemInformationalMessage: any = __stub;
export type SystemLocalCommandMessage = any;
export const SystemLocalCommandMessage: any = __stub;
export type SystemMemorySavedMessage = any;
export const SystemMemorySavedMessage: any = __stub;
export type SystemMessage = any;
export const SystemMessage: any = __stub;
export type SystemMessageLevel = any;
export const SystemMessageLevel: any = __stub;
export type SystemMicrocompactBoundaryMessage = any;
export const SystemMicrocompactBoundaryMessage: any = __stub;
export type SystemPermissionRetryMessage = any;
export const SystemPermissionRetryMessage: any = __stub;
export type SystemScheduledTaskFireMessage = any;
export const SystemScheduledTaskFireMessage: any = __stub;
export type SystemStopHookSummaryMessage = any;
export const SystemStopHookSummaryMessage: any = __stub;
export type SystemThinkingMessage = any;
export const SystemThinkingMessage: any = __stub;
export type SystemTurnDurationMessage = any;
export const SystemTurnDurationMessage: any = __stub;
export type TombstoneMessage = any;
export const TombstoneMessage: any = __stub;
export type ToolUseSummaryMessage = any;
export const ToolUseSummaryMessage: any = __stub;
export type UserMessage = any;
export const UserMessage: any = __stub;

export default __stub;
