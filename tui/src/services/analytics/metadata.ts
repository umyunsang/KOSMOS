// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.
//
// Analytics metadata helpers — all return empty payloads or `false` flags so
// the downstream logEvent stubs receive nothing from the TUI layer.

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type AnalyticsMetadata_I_VERIFIED_THIS_IS_NOT_CODE_OR_FILEPATHS = any

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

export function mcpToolDetailsForAnalytics(
  _toolName: string,
): Record<string, never> {
  return {}
}

export function sanitizeToolNameForAnalytics(toolName: string): string {
  return toolName
}
