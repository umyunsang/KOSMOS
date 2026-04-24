// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.
//
// Anthropic `anthropic-beta` header manipulation has no counterpart in the
// FriendliAI path. Callers read this module to decide which betas to surface
// on outbound requests; KOSMOS returns empty sets + `false` flags so no
// Anthropic-specific beta tokens ever leak into a FriendliAI call.

export function getModelBetas(_model: string): string[] {
  return []
}

export function getMergedBetas(
  _model: string,
  _additional?: readonly string[],
): string[] {
  return []
}

export function modelSupportsStructuredOutputs(_model: string): boolean {
  return false
}

export function modelSupportsAutoMode(_model: string): boolean {
  return false
}

export function shouldIncludeFirstPartyOnlyBetas(): boolean {
  return false
}

export function shouldUseGlobalCacheScope(): boolean {
  return false
}
