// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.
//
// Claude Code's session-tracing spans (Datadog-backed) have no counterpart
// in KOSMOS. OTEL emission happens inside `ipc/llmClient.ts` via the
// FriendliAI path; these legacy helpers remain as compile-time no-ops.

export interface Span {
  end(): void
}

const NOOP_SPAN: Span = {
  end() {
    /* no-op */
  },
}

export function startToolSpan(): Span {
  return NOOP_SPAN
}

export function endToolSpan(_span?: Span): void {
  /* no-op */
}

export function startToolExecutionSpan(): Span {
  return NOOP_SPAN
}

export function endToolExecutionSpan(_span?: Span): void {
  /* no-op */
}

export function startToolBlockedOnUserSpan(): Span {
  return NOOP_SPAN
}

export function endToolBlockedOnUserSpan(_span?: Span): void {
  /* no-op */
}

export function endLLMRequestSpan(_span?: Span): void {
  /* no-op */
}

export function startInteractionSpan(): Span {
  return NOOP_SPAN
}

export function endInteractionSpan(_span?: Span): void {
  /* no-op */
}

export function startHookSpan(): Span {
  return NOOP_SPAN
}

export function endHookSpan(_span?: Span): void {
  /* no-op */
}

export function addToolContentEvent(_name: string, _data?: unknown): void {
  /* no-op */
}

export function isBetaTracingEnabled(): boolean {
  return false
}
