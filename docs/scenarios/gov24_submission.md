# Scenario: Government 24 (정부24) Document Submission

**Why this is a scenario, not a mock**: The Government 24 (정부24) document submission API (민원 제출 및 처리 연계 API) is not publicly disclosed. The Ministry of the Interior and Safety (행정안전부) does not publish an OpenAPI specification, SDK documentation, or reference stack for the submission workflow. Access requires an inter-agency integration agreement (기관 연계 협약) and credentials issued by the Government 24 operations center, neither of which is available to KOSMOS as a public integration. The request signing protocol and session management details are withheld from public disclosure.

## Journey overview

A citizen uses KOSMOS to submit a civil petition (민원) — for example, a residency certificate request (주민등록등본) or a business license application. The journey proceeds as follows:

1. The citizen describes their petition type in natural language via the KOSMOS TUI.
2. KOSMOS resolves the petition type to a Government 24 service code (민원코드) using the `lookup` primitive against the public data.go.kr civil-service catalogue (공공데이터포털 민원정보 API — this part IS mockable via `docs/mock/data_go_kr`).
3. KOSMOS presents the resolved service to the citizen and requests confirmation.
4. Upon confirmation, KOSMOS assembles the submission payload: petition type, citizen identity (obtained via the OmniOne DID VP flow — mockable via `docs/mock/omnione`), required documents, and contact information.
5. KOSMOS invokes the `delegate` primitive to hand off the assembled payload to the real Government 24 submission endpoint.
6. The Government 24 system processes the submission, issues a receipt number (접수번호), and returns a status callback.
7. KOSMOS records the receipt number and handoff result in the `ToolCallAuditRecord` (Spec 024) and presents the outcome to the citizen.

## KOSMOS ↔ real system handoff point

The handoff occurs at step 5: when KOSMOS calls `delegate(tool_id="gov24_submit", params={"service_code": ..., "payload": ..., "identity_vp": ...})`.

At this point:
- KOSMOS has fully assembled the submission payload and verified citizen identity via OmniOne VP.
- KOSMOS emits a `ToolCallAuditRecord` with `is_irreversible=True` and `pipa_class="sensitive"` before invoking the delegate.
- The delegate hands control to the Government 24 submission endpoint over an HTTPS connection secured with a KISA-issued client certificate (details of this channel are part of the withheld protocol).
- If the submission endpoint is unreachable or returns an error, KOSMOS records the structured error (`{ code, message, receipt_number: null }`) in the audit record and presents a human-readable failure message to the citizen.
- If the submission succeeds, the receipt number is recorded and the audit record is closed with `outcome: "submitted"`.

KOSMOS does NOT retry a failed submission automatically — the `is_irreversible=True` flag requires explicit citizen reconfirmation before any retry.

## What KOSMOS does on our side

- Resolves petition types and required fields from the public data.go.kr civil-service catalogue (fully mockable).
- Assembles the submission payload in a Pydantic v2 model (`Gov24SubmissionPayload`) with PIPA class annotations.
- Verifies citizen identity via the OmniOne VP exchange before payload assembly (fully mockable).
- Emits a `ToolCallAuditRecord` with `is_irreversible=True` before the handoff.
- Records the structured handoff result (success receipt number or structured error) in the audit record.
- Presents the outcome to the citizen in Korean.

## What KOSMOS deliberately does NOT do (harness discipline)

- KOSMOS does not implement the Government 24 submission protocol — it treats the submission endpoint as an opaque external system.
- KOSMOS does not cache or store the submission payload beyond the session lifetime — citizen data is not persisted.
- KOSMOS does not attempt to reverse a submitted petition — reversal is the citizen's responsibility via the Government 24 portal.
- KOSMOS does not expose the Government 24 inter-agency credentials anywhere in source code, configuration, or logs.

---

*Promoted to mock on <date>, tracked by #<issue>* — replace this line when the Government 24 submission API becomes publicly available and a byte/shape-axis mock can be built.
