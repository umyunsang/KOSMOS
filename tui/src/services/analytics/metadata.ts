// SPDX-License-Identifier: Apache-2.0
// KOSMOS-1633 P2 / KOSMOS-1978 T003b — stub-noop replacement.
//
// Original CC module: .references/claude-code-sourcemap/restored-src/src/services/analytics/metadata.ts
// CC version: 2.1.88 (973 lines, EventMetadata enrichment + 1P proto serialization)
// KOSMOS deviation: KOSMOS-OTEL pipeline does not produce 1P events. The
// `EventMetadata` / `EnrichMetadataOptions` / `FirstPartyEventLoggingMetadata`
// types are preserved as opaque stubs so call sites compile; the helper
// functions (`isAnalyticsToolDetailsLoggingEnabled`, `getEventMetadata`,
// `to1PEventFormat`) return empty / sentinel values that downstream sinks
// drop silently.
//
// Function shapes preserved from CC; runtime effect is zero.

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS = any

// CC type re-exports (opaque stubs — downstream code only treats them as
// `Record<string, unknown>` after stubification).
export type EnvContext = Record<string, unknown>
export type ProcessMetrics = Record<string, unknown>
export type EventMetadata = Record<string, unknown>
export type EnrichMetadataOptions = Record<string, unknown>
export type FirstPartyEventLoggingCoreMetadata = Record<string, unknown>
export type FirstPartyEventLoggingMetadata = Record<string, unknown>

export function extractMcpToolDetails(_toolName: string): null {
  return null
}

export function extractSkillName(_toolName: string): string | null {
  return null
}

export function extractToolInputForTelemetry(
  _toolName: string,
  _input: unknown,
): Record<string, never> {
  return {}
}

export function getFileExtensionForAnalytics(_path: string): string {
  return ''
}

export function getFileExtensionsFromBashCommand(_command: string): string[] {
  return []
}

export function isToolDetailsLoggingEnabled(): boolean {
  return false
}

export function isAnalyticsToolDetailsLoggingEnabled(_toolName?: string): boolean {
  return false
}

export function mcpToolDetailsForAnalytics(
  _toolName: string,
): Record<string, never> {
  return {}
}

export function sanitizeToolNameForAnalytics(toolName: string): string {
  return toolName
}

/**
 * KOSMOS-1633 stub for CC's `getEventMetadata` (line 693 of the CC source).
 * Returns an empty enriched-metadata envelope so call sites that destructure
 * `envContext` / `processMetrics` etc. get safe defaults.
 */
export async function getEventMetadata(
  _options?: EnrichMetadataOptions,
): Promise<EventMetadata> {
  return {}
}

/**
 * KOSMOS-1633 stub for CC's `to1PEventFormat` (line 796 of the CC source).
 * Returns an empty envelope; the no-op `FirstPartyEventLoggingExporter` drops it.
 */
export function to1PEventFormat(
  _metadata: EventMetadata,
  _userMetadata: unknown,
  _additionalMetadata: Record<string, unknown> = {},
): FirstPartyEventLoggingMetadata {
  return {}
}
