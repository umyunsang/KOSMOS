// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 FR-009 stub.
//
// The original Anthropic Files API client has been removed. KOSMOS has no
// Files API surface in P1+P2 scope. If / when file handling is introduced
// in Epic #1634 (P3 tool system), the real implementation replaces this
// stub. Until then, any call through the old exports throws a descriptive
// error rather than silently no-op'ing.

const REMOVED_MSG =
  'Files API removed in Epic #1633; replacement handled in P3 tool system (Epic #1634).'

// Type stubs — preserved so callers compile without changes.
export type File = Record<string, unknown>
export type FilesApiConfig = Record<string, unknown>
export type DownloadResult = Record<string, unknown>
export type UploadResult = Record<string, unknown>
export type FileMetadata = Record<string, unknown>

export async function downloadFile(..._args: unknown[]): Promise<never> {
  throw new Error(REMOVED_MSG)
}

export function buildDownloadPath(..._args: unknown[]): never {
  throw new Error(REMOVED_MSG)
}

export async function downloadAndSaveFile(..._args: unknown[]): Promise<never> {
  throw new Error(REMOVED_MSG)
}

export async function downloadSessionFiles(..._args: unknown[]): Promise<never> {
  throw new Error(REMOVED_MSG)
}

export async function uploadFile(..._args: unknown[]): Promise<never> {
  throw new Error(REMOVED_MSG)
}

export async function uploadSessionFiles(..._args: unknown[]): Promise<never> {
  throw new Error(REMOVED_MSG)
}

export async function listFilesCreatedAfter(..._args: unknown[]): Promise<never> {
  throw new Error(REMOVED_MSG)
}

export function parseFileSpecs(..._args: unknown[]): never {
  throw new Error(REMOVED_MSG)
}
