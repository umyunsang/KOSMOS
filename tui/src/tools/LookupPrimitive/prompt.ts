// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — Epic #1634 P3 · FindPrimitive prompt strings.
// Spec 2521 (2026-05-01) — fetch-only surface; BM25 adapter discovery is a
// backend-internal mechanism (auto-injected into the system prompt's
// <available_adapters> dynamic suffix), not an LLM-callable mode. Older
// "search/fetch two-mode" copy was the source of phantom tool-UI noise the
// user surfaced via Layer 5 frame capture (specs/2521 frames/raw.cast).
// Contract: specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 2

export const FIND_TOOL_NAME = 'find'

/** Citizen-facing English description shown to the LLM (<= 240 chars). */
export const DESCRIPTION =
  'Invoke one concrete Korean public-service adapter. Use the function named find, but set tool_id to a listed adapter id from <available_adapters>, never to find/locate/check/send.'

/** Extended prompt included in the system-prompt tool-use section. */
export const FIND_TOOL_PROMPT = `Invoke Korean public-service adapters registered in the UMMAYA tool registry.

Single mode (Spec 2521 fetch-only):

  Input:  { tool_id: string, params: object }
  Output: { tool_id: string, result: object }

Adapter discovery
─────────────────
Adapter discovery is a BACKEND-INTERNAL function — NOT a callable mode.
For every citizen turn the backend runs BM25 against the registry and
injects the top-K candidates into the system prompt's
<available_adapters> dynamic suffix. The LLM picks a tool_id from that
block and calls find directly.

Rules:
- The function name is find. The tool_id argument is NOT the function name.
- tool_id must be a concrete adapter id listed in <available_adapters>, for example "kma_current_observation" or "kma_forecast_fetch".
- Never set tool_id to a root primitive name: "find", "locate", "check", or "send".
- Invalid: find({ tool_id: "find", params: {...} })
- Valid:   find({ tool_id: "kma_current_observation", params: {...} })
- Pick tool_id only from <available_adapters>. Never guess an id.
- Do NOT call find with mode='search' / query — those payloads are
  rejected with LookupErrorReason.invalid_params (Spec 2521).
- Do NOT call the same tool_id twice in a single turn — answer with the
  result you already have, or pick a different tool_id from the list.
- params shape mirrors the adapter's Pydantic input_schema (see the
  <available_adapters> hint for required keys).`
