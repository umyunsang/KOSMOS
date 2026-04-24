// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1634 P3 · SubmitPrimitive prompt strings.
// Contract: specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 3

export const SUBMIT_TOOL_NAME = 'submit'

/** One-line bilingual description shown to the LLM. */
export const DESCRIPTION =
  'Submit a side-effecting citizen action (e.g., application, report). 시민 행위 제출 (신청, 신고).'

/** Extended prompt included in the system-prompt tool-use section. */
export const SUBMIT_TOOL_PROMPT = `Submit a side-effecting citizen action to a registered KOSMOS adapter.

Input: { tool_id: string, params: object }
  - tool_id: the adapter identifier (obtain via lookup mode=search first)
  - params: adapter-defined Pydantic-validated parameter body

Output: { transaction_id: string, status: string, adapter_receipt: object }
  - transaction_id: deterministically derived identifier for idempotency reasoning
  - status: "accepted" | "rejected" | "pending"
  - adapter_receipt: adapter-specific confirmation payload

Rules:
- ALWAYS run lookup(mode=search) first to identify the correct adapter.
- submit is IRREVERSIBLE — confirm intent clearly before calling.
- The permission gauntlet (Layer 2 orange ⓶) executes before adapter dispatch.
- Use transaction_id to reason about idempotency (same input → same ID).
- Do NOT submit on behalf of the user without explicit confirmation.`
