// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1634 P3 · SubscribePrimitive prompt strings.
// Contract: specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 5

export const SUBSCRIBE_TOOL_NAME = 'subscribe'

/** One-line bilingual description shown to the LLM. */
export const DESCRIPTION =
  'Subscribe to a streaming adapter with session-lifetime handle. 세션 기반 스트리밍 구독.'

/** Extended prompt included in the system-prompt tool-use section. */
export const SUBSCRIBE_TOOL_PROMPT = `Subscribe to a streaming KOSMOS adapter and receive a session-lifetime handle.

Input: { tool_id: string, params: object, lifetime_hint?: "session"|"short"|"long" }
  - tool_id: the streaming adapter identifier (obtain via lookup mode=search first)
  - params: adapter-defined Pydantic-validated subscription parameter body
  - lifetime_hint: requested handle lifetime — "session" (default), "short" (≤5 min), "long" (≤24 h)

Output: { handle_id: string, lifetime: string, kind: string }
  - handle_id: opaque subscription handle recorded in the audit ledger (Spec 024)
  - lifetime: actual granted lifetime (may differ from hint)
  - kind: adapter stream kind, e.g. "cbs_disaster_alert", "rss_feed"
  NOTE: The stream itself is delivered out-of-band via TUI ⎿ multi-turn citation prefix.
        The LLM receives only the handle — not the stream data directly.

Rules:
- subscribe is session-scoped and side-effecting — not concurrency safe.
- Use handle_id to reference the subscription in follow-up lookup or subscribe calls.
- Layer 2 orange ⓶ permission gauntlet executes before adapter dispatch.
- prefer "session" lifetime_hint unless the user explicitly requests longer.`
