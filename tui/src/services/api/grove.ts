// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration · Epic #2077 surface preservation.
// Research use — adapted from Claude Code 2.1.88 src/services/api/grove.ts
// Anthropic's Grove (claude.ai pro-tier billing path) is upstream-only — KOSMOS
// has no claude.ai backend, so the eligibility check returns false and the
// non-interactive notice is silent. The exports remain so CC callers compile
// without conditional branching.

export async function isQualifiedForGrove(): Promise<boolean> {
  return false
}

export async function checkGroveForNonInteractive(): Promise<void> {
  return
}
