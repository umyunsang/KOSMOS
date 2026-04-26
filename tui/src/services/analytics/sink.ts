// SPDX-License-Identifier: Apache-2.0
// KOSMOS-1633 P2 / KOSMOS-1978 T003b — stub-noop replacement.
//
// Original CC module: .references/claude-code-sourcemap/restored-src/src/services/analytics/sink.ts
// CC version: 2.1.88
// KOSMOS deviation: CC sink fans out events to Datadog + Anthropic 1P logger.
// KOSMOS sends all telemetry through the Spec 021 OTEL pipeline (vision.md
// § L1-A A7, zero external egress to Anthropic 1P or Datadog). The CC
// `attachAnalyticsSink` glue is therefore a no-op in KOSMOS.
//
// Function shapes preserved so existing call sites compile. Runtime effect
// is zero — `tui/src/ipc/llmClient.ts` + `kosmos.observability.*` (Python
// backend) own the real telemetry path.

import { logForDebugging } from '../../utils/log.js'

export function initializeAnalyticsGates(): void {
  // KOSMOS-1633 P2 stub-noop. CC initialised Datadog + 1P kill-switch gates
  // here; KOSMOS has no equivalent — OTEL pipeline owns its own enable/disable
  // semantics via `OTEL_SDK_DISABLED` env (Spec 021).
  logForDebugging('analytics:initializeAnalyticsGates noop (KOSMOS-1633)')
}

export function initializeAnalyticsSink(): void {
  // KOSMOS-1633 P2 stub-noop. CC attached the AnalyticsSink that drains the
  // queued events from `services/analytics/index.ts`; KOSMOS-OTEL has no
  // equivalent sink — events queued by the noop `logEvent`/`profileCheckpoint`
  // in index.ts are discarded by design.
  logForDebugging('analytics:initializeAnalyticsSink noop (KOSMOS-1633)')
}
