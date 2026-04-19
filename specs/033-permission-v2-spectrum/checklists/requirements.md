# Requirements Quality Checklist — Permission v2 (Epic #1297)

**Feature**: 033-permission-v2-spectrum
**Date**: 2026-04-20
**Owner**: Lead (Opus)

## 1. Clarity

- [x] All functional requirements are uniquely numbered (FR-A01..F03) and grouped by concern.
- [x] No `[NEEDS CLARIFICATION: ...]` markers remain in spec.md.
- [x] All placeholder bracketed template text has been replaced with concrete content.
- [x] Every user story has priority, Why/Independent Test/Acceptance Scenarios fields filled.
- [x] Each FR is atomic (single capability) and testable (observable outcome).

## 2. Constitution Alignment

- [x] §I Reference-Driven Development — spec explicitly cites Claude Code 2.1.88 PermissionMode.ts (primary) and Kantara CR / ISO 29184 / Continue.dev / Codex CLI / OpenAI Agents SDK (secondary). Full mapping will be re-verified in plan.md Phase 0.
- [x] §II Fail-Closed Security (NON-NEGOTIABLE) — FR-B01..B04 encode bypass-immune checks. FR-C02/D05/edge cases encode fail-closed behavior for missing stores/keys.
- [x] §III Pydantic v2 Strict Typing — spec is design-level; code-level enforcement is plan/tasks responsibility. Spec describes schemas only abstractly (no `Any`).
- [x] §IV Government API Compliance — no new adapters introduced; existing Spec 024 `GovAPITool` extensions are reused (`is_irreversible`, `auth_level`, `pipa_class`).
- [x] §V Policy Alignment — PIPA §15(2)/§18/§22/§26 and AI 기본법 §27 cited in FR-D03/D07/D08/E01/E02.
- [x] §VI Deferred Work Accountability — 7 deferred items tracked in Scope Boundaries table; all marked NEEDS TRACKING to be resolved by `/speckit-taskstoissues`.

## 3. Scope Boundaries

- [x] `Out of Scope (Permanent)` — 4 items with brief reasons.
- [x] `Deferred to Future Work` — 7 items with reason + target Epic + NEEDS TRACKING marker.
- [x] No "separate epic" / "future phase" / "v2" free-text references in spec prose without a table entry.

## 4. Independent Testability

- [x] US1 (P1): mock HIRA 어댑터 + `default` 모드로 1회 프롬프트 → 2회 무프롬프트 실행 + ledger 1건 = 완전 검증.
- [x] US2 (P1): ledger 5건 기록 → 외부 1바이트 변조 → 검증 CLI 오류 출력 = 완전 검증.
- [x] US3 (P1): `is_irreversible=True` 어댑터를 `bypassPermissions` 모드에서 2회 호출 → 2회 프롬프트 + 2건 독립 action_digest 레코드 = 완전 검증.
- [x] US4 (P2): 3개 어댑터 tri-state 저장 → 세션 재시작 → 각 어댑터 호출 시 대응 동작 = 완전 검증.
- [x] US5 (P2): Shift+Tab 4회 순환 + `/permissions bypass` 확인 프롬프트 + 상태바 색상 변경 = 완전 검증.

## 5. Measurable Success Criteria

- [x] SC-001..SC-009 are all measurable (숫자, 비율, 정밀도, 존재성 기준).
- [x] No technology-coupled metric leaked (e.g., "Python 3.12 latency" — instead "p50 ≤ 5ms").
- [x] Each SC maps to at least one FR group.

## 6. Dependencies & Assumptions

- [x] 7 assumptions declared (Agent Swarm IPC, Spec 024/025 stability, TUI 287 readiness, filesystem write access, AAL claim provenance, AI 기본법 §31 범위, Kantara CR license 전제).
- [x] All assumptions are re-verifiable in plan.md Phase 0.

## 7. Cross-References

- [x] Epic #1297 cited in header.
- [x] Spec 024 (ToolCallAuditRecord) cited in FR-F01.
- [x] Spec 025 V6 AAL backstop cited in FR-F02 + Edge Case "AAL 다운그레이드".
- [x] Spec 021 OTEL cited in FR-F03.
- [x] Spec 027 mailbox cited in FR-B03 assumption.
- [x] Spec 287 TUI cited in FR-A02/A03 assumption.
- [x] MEMORY `project_pipa_role` cited in FR-E01 (수탁자 기본 + LLM carve-out).

## Result

All 7 sections pass. Spec is ready for `/speckit-plan` Phase 0 Research.

**Next step**: Run `/speckit-plan`; Phase 0 Research must:
1. Validate Kantara Consent Receipt v1.1.0 JSON schema licensing for KOSMOS use.
2. Confirm Continue.dev permissions.yaml schema compatibility for tri-state encoding.
3. Select exact hash-chain canonical JSON encoding (recommend RFC 8785 JCS).
4. Select HMAC key rotation policy (recommend single key + yearly manual rotation for single-user MVP).
5. Enumerate deferred issue placeholders (7 items) to be created at `/speckit-taskstoissues`.
