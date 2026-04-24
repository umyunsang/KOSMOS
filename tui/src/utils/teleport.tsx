// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.
//
// Claude Code's "teleport to remote session" feature (cloud-backed worktree
// handoff) has no counterpart in KOSMOS. All exports are inert — callers
// receive empty payloads and no background work is kicked off.

export interface TeleportResult {
  readonly success: boolean
  readonly reason?: string
}

export type TeleportProgressStep =
  | 'init'
  | 'bundling'
  | 'uploading'
  | 'routing'
  | 'done'

export interface PollRemoteSessionResponse {
  readonly messages: readonly never[]
  readonly done: boolean
}

export async function teleportToRemote(): Promise<TeleportResult> {
  return { success: false, reason: 'KOSMOS: teleport disabled' }
}

export async function teleportResumeCodeSession(): Promise<TeleportResult> {
  return { success: false, reason: 'KOSMOS: teleport disabled' }
}

export async function pollRemoteSessionEvents(): Promise<PollRemoteSessionResponse> {
  return { messages: [], done: true }
}

export async function processMessagesForTeleportResume(): Promise<readonly never[]> {
  return []
}

export async function archiveRemoteSession(): Promise<void> {
  /* no-op */
}

export async function checkOutTeleportedSessionBranch(): Promise<boolean> {
  return false
}
