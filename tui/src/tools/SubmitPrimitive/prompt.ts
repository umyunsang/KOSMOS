// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — SendPrimitive prompt strings.
// Contract: specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 3

export const SEND_TOOL_NAME = 'send'

/** One-line English description (<= 240 chars). */
export const DESCRIPTION =
  'Send a citizen action such as an application, report, or submission to a public-service adapter. This can have side effects; choose an adapter from <available_adapters>.'

/** Extended prompt included in the system-prompt tool-use section. */
export const SEND_TOOL_PROMPT = `Send a side-effecting citizen action to a registered UMMAYA adapter.

Input: { tool_id: string, params: object }
  - tool_id: the adapter identifier from <available_adapters>
  - params: adapter-defined Pydantic-validated parameter body

Output: { transaction_id: string, status: string, adapter_receipt: object }
  - transaction_id: deterministically derived identifier for idempotency reasoning
  - status: "accepted" | "rejected" | "pending"
  - adapter_receipt: adapter-specific confirmation payload

Rules:
- Pick the send adapter from <available_adapters>; BM25 discovery is backend-internal.
- send is IRREVERSIBLE — confirm intent clearly before calling.
- The permission gauntlet (Layer 2 orange ⓶) executes before adapter dispatch.
- Use transaction_id to reason about idempotency (same input → same ID).
- Do NOT send on behalf of the user without explicit confirmation.`
