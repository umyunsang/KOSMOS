// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #2637 cascade · stub-noop replacement.
// SWAP/anti-anthropic-1p(2637): Anthropic BigQuery metrics exporter (1P telemetry
// backend) is permanently disabled in KOSMOS. instrumentation.ts byte-copy (R-5)
// references this module; KOSMOS exports to local Langfuse via OTLP (Spec 021/028).

import type { MetricReader } from '@opentelemetry/sdk-metrics'

export class BigQueryMetricsExporter implements Partial<MetricReader> {
  // Intentional no-op (Epic #2637 stub). Anthropic BigQuery is swap-1 dependent.
  // KOSMOS routes metrics via @opentelemetry/exporter-metrics-otlp-http to local
  // Langfuse collector (Spec 028).
  async shutdown(): Promise<void> {}
  async forceFlush(): Promise<void> {}
}
