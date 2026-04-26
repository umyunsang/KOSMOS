// SPDX-License-Identifier: Apache-2.0
// KOSMOS-1633 P2 / KOSMOS-1978 T003b — stub-noop replacement.
//
// Original CC module: .references/claude-code-sourcemap/restored-src/src/services/analytics/firstPartyEventLoggingExporter.ts
// CC version: 2.1.88 (806 lines, batch HTTP exporter to api.anthropic.com/api/event_logging/batch)
// KOSMOS deviation: CC's 1P logger ships ClaudeCodeInternalEvent + Growthbook
// experiment events to Anthropic's BigQuery sink. KOSMOS routes telemetry
// through the Spec 021 OTEL pipeline → local Langfuse only (vision.md
// § L1-A A7, zero external egress to *.anthropic.com — see Epic #1978 SC-004
// FR-004). This module therefore exports a no-op `LogRecordExporter` shape so
// `services/analytics/sink.ts` and other call sites compile, but the runtime
// effect is zero — log records are dropped silently and the OTEL pipeline
// owns the real export path.
//
// Function shapes preserved from CC's `LogRecordExporter` interface so any
// `BatchLogRecordProcessor.addLogRecordProcessor(exporter)` glue still
// resolves at link time.

import type { ExportResult } from '@opentelemetry/core'
import { ExportResultCode } from '@opentelemetry/core'
import type {
  LogRecordExporter,
  ReadableLogRecord,
} from '@opentelemetry/sdk-logs'
import { logForDebugging } from '../../utils/debug.js'

export class FirstPartyEventLoggingExporter implements LogRecordExporter {
  // CC original constructor took ~10 options (timeout / maxBatchSize / skipAuth /
  // batchDelayMs / baseBackoffDelayMs / maxBackoffDelayMs / maxAttempts / path /
  // baseUrl / isKilled / schedule). KOSMOS no-op accepts and ignores them so
  // existing instantiation sites compile without churn.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  constructor(_options: Record<string, any> = {}) {
    logForDebugging('FirstPartyEventLoggingExporter: stub-noop (KOSMOS-1633)')
  }

  export(
    _logs: ReadableLogRecord[],
    resultCallback: (result: ExportResult) => void,
  ): void {
    // KOSMOS sink — drop everything; report success so OTEL batch processors do
    // not retry. The real export path is the Spec 021 OTEL pipeline.
    resultCallback({ code: ExportResultCode.SUCCESS })
  }

  async shutdown(): Promise<void> {
    // No state to flush.
  }

  async forceFlush(): Promise<void> {
    // No buffered records.
  }

  // Method retained from the CC original surface for compatibility with any
  // diagnostic glue. Always returns 0 — KOSMOS does not buffer.
  async getQueuedEventCount(): Promise<number> {
    return 0
  }
}
