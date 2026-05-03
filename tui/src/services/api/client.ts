// SPDX-License-Identifier: Apache-2.0
// Spec 2641 — api/client.ts duplicate-`getAnthropicClient` fix.
//
// Background: tui/src/services/api/claude.ts is a byte-copy of CC 2.1.88's
// streaming handler (Spec 2521) which imports `getAnthropicClient` from this
// module. KOSMOS routes all LLM traffic through the Spec 1978 stdio IPC
// bridge — no Anthropic SDK client is ever instantiated. Two prior stubs
// landed in this file (Spec 2077 async-throw + Spec 2521 sync-null) and
// coexisted as a duplicate symbol declaration. CC migration audit
// (specs/cc-migration-audit/scope-S6-services.md § swap-1 표 row 11) flagged
// this as a P1 risk.
//
// This file now exports a single `getAnthropicClient` per CC's contract
// shape (sync, returns null) plus the `CLIENT_REQUEST_ID_HEADER` constant.
// claude.ts is a zero-callers byte-copy after Spec 2293, so the stub return
// value is never dereferenced at runtime.
//
// SWAP/anti-anthropic-1p(2521): byte-copied tui/src/services/api/claude.ts
// imports `getAnthropicClient`. KOSMOS routes LLM calls via the Spec 1978
// stdio IPC bridge and never instantiates an Anthropic client directly. The
// stub returns null so the byte-copy's import resolves at link time; the
// zero-callers status (verified by callgraph audit Spec 2293) guarantees
// this null is never dereferenced.

export const CLIENT_REQUEST_ID_HEADER = 'x-client-request-id'

export function getAnthropicClient(..._args: unknown[]): null {
  return null
}
