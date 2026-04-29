// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — SubmitPrimitive prompt strings.
// Contract: specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 3

export const SUBMIT_TOOL_NAME = 'submit'

/** One-line Korean-primary description (≤ 240 chars). */
export const DESCRIPTION =
  '공공 서비스에 시민 행위(신청·신고·제출)를 전송합니다. 부작용이 발생하며 되돌릴 수 없을 수 있습니다. 호출 전 반드시 lookup(mode=search)로 어댑터를 확인하세요.'

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
