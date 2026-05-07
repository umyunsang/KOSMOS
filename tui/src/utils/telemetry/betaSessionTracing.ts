// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — Epic #2637 cascade · stub-noop replacement.
// SWAP/anti-anthropic-1p(2637): Anthropic beta session tracing (1P telemetry)
// is permanently disabled in UMMAYA. instrumentation.ts byte-copy (R-5) references
// this module; UMMAYA uses Spec 021 OTEL pipeline directly.

export function isBetaTracingEnabled(): boolean {
  // Intentional no-op (Epic #2637 stub). Anthropic beta tracing is swap-1 dependent.
  return false
}
