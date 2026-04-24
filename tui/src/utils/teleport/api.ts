// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.

export interface RemoteMessageContent {
  readonly text?: string
}

export interface CodeSession {
  readonly id: string
  readonly title?: string
}

export async function fetchCodeSessionsFromSessionsAPI(): Promise<readonly CodeSession[]> {
  return []
}

export async function fetchSession(_id: string): Promise<CodeSession | null> {
  return null
}

export function getOAuthHeaders(): Record<string, string> {
  return {}
}

export function isTransientNetworkError(_err: unknown): boolean {
  return false
}

export function prepareApiRequest(): null {
  return null
}

export async function updateSessionTitle(
  _id: string,
  _title: string,
): Promise<void> {
  /* no-op */
}
