// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1634 P3 · VerifyPrimitive prompt strings.
// Contract: specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 4

export const VERIFY_TOOL_NAME = 'verify'

/** One-line bilingual description shown to the LLM. */
export const DESCRIPTION =
  'Delegate credential verification to an auth vendor. 인증 수단 검증 위임.'

/** Extended prompt included in the system-prompt tool-use section. */
export const VERIFY_TOOL_PROMPT = `Delegate credential verification to a registered KOSMOS auth adapter.

Input: { tool_id: string, params: object }
  - tool_id: the auth adapter identifier (e.g. "gongdong_injeungseo", "mobile_id")
  - params: adapter-defined credential parameter body

Output (discriminated by auth_family):
  - auth_family: "gongdong_injeungseo" | "geumyung_injeungseo" | "ganpyeon_injeung" | "digital_onepass" | "mobile_id" | "mydata"
  - The LLM uses auth_family to determine the resulting auth level (AAL1/AAL2/AAL3)
    and to decide subsequent calls (e.g., "now I have AAL2, I can call this submit adapter")

Rules:
- verify NEVER mints credentials — it only delegates verification.
- Use the auth_family in the output to plan subsequent submit or lookup calls.
- Do NOT store or log credential values in params.
- Layer 1 green ⓵ permission applies; no user confirmation modal for read-only verify.`
