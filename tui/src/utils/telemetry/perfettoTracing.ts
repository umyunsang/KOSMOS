// SPDX-License-Identifier: Apache-2.0
// KOSAX-original — Epic #2637 cascade · stub-noop replacement.
// SWAP/anti-anthropic-1p(2637): Perfetto tracing (Anthropic 1P performance
// profiling) is permanently disabled in KOSAX. instrumentation.ts byte-copy (R-5)
// references this module; KOSAX uses Spec 021 OTEL trace pipeline instead.

export async function initializePerfettoTracing(): Promise<void> {
  // Intentional no-op (Epic #2637 stub). Anthropic Perfetto integration is swap-1 dependent.
}
