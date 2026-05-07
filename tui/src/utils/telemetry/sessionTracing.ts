// SPDX-License-Identifier: Apache-2.0
// KOSAX-original — Spec 2521 byte-copy bridge stub (no live caller in KOSAX).
// SWAP/anti-anthropic-1p(2521): minimal stub for the byte-copied
// services/api/claude.ts which references CC's per-request telemetry-tracing
// span helpers. KOSAX uses Spec 021 OTEL spans emitted from llmClient.ts
// directly, not from this code path. Stub returns inert no-ops; the byte-copy
// has zero callers in KOSAX so no live tracing surface depends on this file.
//
// Epic #2637: endInteractionSpan + isEnhancedTelemetryEnabled added as no-op
// exports required by instrumentation.ts byte-copy (R-5). Both are Anthropic 1P
// session-tracing helpers (swap-1 dependent) — KOSAX no-op is correct.

export function isBetaTracingEnabled(): boolean {
  return false
}

export type LLMRequestNewContext = Record<string, unknown>

export function startLLMRequestSpan(..._args: unknown[]): {
  setAttribute: (..._a: unknown[]) => void
  end: () => void
} {
  return {
    setAttribute: () => {},
    end: () => {},
  }
}

export function endInteractionSpan(..._args: unknown[]): void {
  // Intentional no-op (Epic #2637 stub). Anthropic 1P session span tracking
  // is swap-1 dependent — KOSAX uses Spec 021 OTEL span pipeline instead.
}

export function isEnhancedTelemetryEnabled(): boolean {
  // Intentional no-op (Epic #2637 stub). Anthropic enhanced telemetry consent
  // is swap-1 dependent — KOSAX telemetry consent follows Spec 033 permission model.
  return false
}
