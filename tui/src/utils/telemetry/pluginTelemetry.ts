// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.

export function buildPluginTelemetryFields(
  _plugin: unknown,
): Record<string, never> {
  return {}
}

export function buildPluginCommandTelemetryFields(
  _plugin: unknown,
  _command: unknown,
): Record<string, never> {
  return {}
}

export function classifyPluginCommandError(_err: unknown): string {
  return 'unknown'
}

export function logPluginLoadErrors(_errors: readonly unknown[]): void {
  /* no-op */
}

export function logPluginsEnabledForSession(
  _plugins: readonly unknown[],
): void {
  /* no-op */
}
