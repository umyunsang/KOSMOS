// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.

export type BackgroundRemoteSessionPrecondition =
  | 'git_dirty'
  | 'no_auth'
  | 'unsupported_repo'
  | 'ok'

export async function checkBackgroundRemoteSessionEligibility(): Promise<BackgroundRemoteSessionPrecondition> {
  return 'no_auth'
}
