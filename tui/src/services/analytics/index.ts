// [P0 reconstructed · Pass 3 · Analytics NO-OP aggregator]
// Reference: consumer imports across tui/src/ + KOSMOS FR-008
//            (bootstrap egress 0) + PIPA §17 external-egress ban.
// Original CC 2.1.88 source was not captured in the sourcemap. KOSMOS
// strategy: provide real types for consumer type-safety, but route all
// data sinks to /dev/null. Operational telemetry goes to local Langfuse
// via OTEL (Spec 028), not to external analytics.
/* eslint-disable @typescript-eslint/no-explicit-any */

// ───── Metadata tag types (PII hygiene) ─────────────────────────────────
// The upstream uses nominal tagging (`_I_VERIFIED_THIS_IS_*`) to force
// callers to explicitly declare PII status at the type layer. KOSMOS
// preserves these nominal names so legacy callsites type-check.

export type AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS =
  Record<string, unknown>

export type AnalyticsMetadata_I_VERIFIED_THIS_IS_PII_TAGGED =
  Record<string, unknown>

// ───── Event API ────────────────────────────────────────────────────────

/**
 * Fire a telemetry event. No-op in KOSMOS baseline — all events are
 * dropped to honour FR-008 (zero bootstrap egress). Real KOSMOS telemetry
 * goes through `src/utils/telemetry/` (OTEL exporter to local Langfuse).
 */
export function logEvent(
  _name?: string,
  _metadata?: unknown,
  _opts?: unknown,
): void {
  return
}

/**
 * Async variant. Returns immediately — no queueing, no promise chain.
 */
export async function logEventAsync(
  _name?: string,
  _metadata?: unknown,
  _opts?: unknown,
): Promise<void> {
  return
}

/**
 * Attach a sink for analytics events. Ignored in KOSMOS — sinks are wired
 * at Epic #1633 when OTEL integration lands.
 */
export function attachAnalyticsSink(_sink: unknown): void {
  return
}

/**
 * Strip Protobuf-only fields from a metadata object before sending.
 * CC does this so internal proto-generated keys (leading underscore etc.)
 * don't leak into the analytics sink. For KOSMOS (analytics disabled) we
 * still implement the transform honestly — returns a shallow copy with
 * leading-underscore keys removed. Callers thus stay idempotent whether
 * analytics is on or off.
 */
export function stripProtoFields(
  obj: Record<string, unknown>,
): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(obj)) {
    if (k.startsWith('_')) continue
    out[k] = v
  }
  return out
}

export default undefined as any
