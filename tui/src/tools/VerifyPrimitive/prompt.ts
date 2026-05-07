// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1634 P3 · VerifyPrimitive prompt strings.
// Epic γ #2294 · T015: Korean description tightened to ≤ 240 chars.
// Contract: specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 4

export const VERIFY_TOOL_NAME = 'verify'

/** One-line citizen-facing Korean description shown to the LLM (≤ 240 chars). */
export const DESCRIPTION =
  '인증 어댑터에 자격증명 검증을 위임합니다. 공인인증서·간편인증·모바일신분증 등 등록된 인증 수단을 tool_id로 지정하세요. 인증 결과(auth_family·auth_level)를 반환하며 자격증명을 직접 발급하거나 저장하지 않습니다.'

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
