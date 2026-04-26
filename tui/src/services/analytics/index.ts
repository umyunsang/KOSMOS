// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 P2 · stub-noop replacement for CC analytics.
//
// The original Anthropic analytics surface (GrowthBook + Datadog + FirstParty
// event logger + sinks) has been removed. KOSMOS emits all runtime telemetry
// via the Spec 021 OTEL pipeline (local Langfuse, zero external egress —
// docs/vision.md § L1-A A7).
//
// This file preserves the original export surface so call sites compile
// without mass-editing 300+ files; every function is a no-op at runtime.
// KOSMOS OTEL span emission is orthogonal to these stubs — see
// tui/src/ipc/llmClient.ts for the real observability path.

// ---------------------------------------------------------------------------
// Type aliases (preserve the strange CC identifier used across the codebase)
// ---------------------------------------------------------------------------

export type AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS = Record<
  string,
  string | number | boolean | null | undefined
>

// ---------------------------------------------------------------------------
// Event logging — no-op (callers retained for code-review auditability;
// runtime effect is zero).
// ---------------------------------------------------------------------------

export function logEvent(
  _eventName: string,
  _metadata?: AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS,
): void {
  // Intentional no-op (Epic #1633 stub). Do not add behaviour here.
}

export function profileCheckpoint(
  _name: string,
  _metadata?: AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS,
): void {
  // Intentional no-op.
}

// ---------------------------------------------------------------------------
// Sink lifecycle — no-op (there is no KOSMOS analytics sink; Spec 021 OTEL
// Collector is the sole telemetry destination).
// ---------------------------------------------------------------------------

export function initializeAnalyticsSink(): void {
  // Intentional no-op.
}

export function flushAnalyticsSink(): Promise<void> {
  return Promise.resolve()
}

export function shutdownAnalyticsSink(): Promise<void> {
  return Promise.resolve()
}

// ---------------------------------------------------------------------------
// CC migration — `stripProtoFields` lifted verbatim from
// `.references/claude-code-sourcemap/restored-src/src/services/analytics/index.ts:45`
// (CC 2.1.88, research-use). Used by sink.ts:14 + firstPartyEventLoggingExporter.ts:33.
// KOSMOS keeps the function shape so existing call sites compile; in the KOSMOS
// stub-noop pipeline the helper still does the right thing — _PROTO_ keys are
// dropped before any (currently disabled) sink could see them.
//
// `AnalyticsSink` is a structural type imported by analytics/sink.ts. CC ships
// a richer interface with logEvent + logEventAsync; KOSMOS exposes the same
// shape so import-link succeeds and the `attachAnalyticsSink` no-op accepts it.
// ---------------------------------------------------------------------------

export type AnalyticsSink = {
  logEvent: (eventName: string, metadata: Record<string, unknown>) => void
  logEventAsync: (
    eventName: string,
    metadata: Record<string, unknown>,
  ) => Promise<void>
}

export function stripProtoFields<V>(
  metadata: Record<string, V>,
): Record<string, V> {
  // Lifted from CC restored-src services/analytics/index.ts:45 (verbatim).
  // Returns the same reference when no _PROTO_ keys present.
  let result: Record<string, V> | undefined
  for (const key in metadata) {
    if (key.startsWith('_PROTO_')) {
      if (result === undefined) {
        result = { ...metadata }
      }
      delete result[key]
    }
  }
  return result ?? metadata
}

export function attachAnalyticsSink(_sink: AnalyticsSink): void {
  // KOSMOS-1633 P2 stub-noop — there is no Datadog / 1P sink to attach to.
  // Matches CC's `attachAnalyticsSink` signature (idempotent, side-effect free).
  // OTEL pipeline is wired separately via tui/src/ipc/llmClient.ts.
}

// ---------------------------------------------------------------------------
// Default export safety net — some callers may import the module namespace.
// ---------------------------------------------------------------------------

export default {
  logEvent,
  profileCheckpoint,
  initializeAnalyticsSink,
  flushAnalyticsSink,
  shutdownAnalyticsSink,
  stripProtoFields,
  attachAnalyticsSink,
}
