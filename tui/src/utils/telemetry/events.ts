// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.

export function logOTelEvent(_name: string, _attrs?: unknown): void {
  /* no-op */
}

export function redactIfDisabled<T>(value: T): T | '[REDACTED]' {
  return value
}
