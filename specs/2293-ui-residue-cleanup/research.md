# Phase 0 Research — UI Residue Cleanup (Epic β · v2)

**Date**: 2026-04-29 (v2 revision) · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**Authority**: AGENTS.md § CORE THESIS · `.specify/memory/constitution.md § II` · cc-source-scope-audit § 1.2.1/1.2.2/1.3.4 · cc-parity-audit.md (Epic α) · **caller-graph.json + disposition.json (v2)**

---

## v1 → v2 변경

v1 의 R-1 (importer 추적 전략) 은 절차로 박제만 됐고 실제 추적 결과는 박제되지 않았음. v2 가 `scripts/build-caller-graph.py` 로 30 file × importer 그래프를 자동 박제 (`data/caller-graph.json`) — R-1 결론이 절차 기술 → 박제된 데이터 기반 결정.

v1 의 R-3 (Constitution II 평가) 가 caller graph 미검토로 utils/permissions 3 file 모두 DELETE 결론. v2 의 caller-graph 박제로 permissionSetup (11 imp) + permissions (14 imp) KOSMOS-needed 발견 → KEEP 으로 결론 정정.

v1 의 R-2 (callsite 매트릭스) + R-4 (6 Tool 평가) + R-5 (baseline 절차) 는 v2 에서도 유효 — 별도 정정 없음.

---

## Deferred Items 검증 (Constitution VI gate)

spec.md `Scope Boundaries & Deferred Items` 섹션 (v2):

| 항목 | Tracking | State |
|---|---|---|
| utils/permissions/{permissionSetup, permissions} 안의 dead `feature()` 제거 | NEEDS TRACKING | 본 Epic merge 후 issue 생성 (Spec 1633 후속 또는 Epic ζ #2297) |
| K-EXAONE 한국어 자동 명명 | NEEDS TRACKING | Future Epic |
| K-EXAONE 한국어 도구 사용 요약 | NEEDS TRACKING | Future Epic |
| K-EXAONE WebFetch 결과 한국어 요약 | NEEDS TRACKING | Future Epic |
| Constitution II audit (`tui/src/` 전체 274 KOSMOS-only ADDITIONS) | NEEDS TRACKING | Spec 1979 후속 또는 Epic ζ |

`grep -niE '(future epic|future phase|separate epic|deferred to|out of scope for v1|later release)' spec.md plan.md`: Deferred 표 외부 매치 0 건. ✅ Principle VI 통과.

---

## R-1 — Caller-graph 자동 박제 (v2)

**Q**: 30 Cleanup-needed 파일을 안전하게 deletion 하려면 importer 를 모두 추적해야 한다. v1 의 수동 grep 절차 대신 자동화로 정확도 보장.

**Decision (v2)**: `specs/2293-ui-residue-cleanup/scripts/build-caller-graph.py` 가 30 file 의 importer + dependency-token 매치를 자동 추출 → `data/caller-graph.json` 박제. Lead 가 그 출력을 입력으로 `data/disposition.json` (DELETE/KEEP + risk + rationale) 결정.

**산출 결과** (caller-graph.json):
- 7 file: 0 importer (claude / client / cli/print / commands/insights / WebFetchTool/utils / dateTimeParser / shell/prefix)
- 1 file: 1 importer × 7 (generateSessionName / Feedback / adminRequests / firstTokenDate / grove / ultrareviewQuota / toolUseSummaryGenerator)
- 5 file: 2 importer (filesApi / overageCreditGrant / sessionIngress / withRetry / yoloClassifier / mcpbHandler 등)
- 4 file: 4-6 importer (logging 4 / errors 6 / referral 5 / errorUtils 5 / sessionTitle 4)
- 3 file: ≥ 11 importer (tokenEstimation 11 / permissionSetup 11 / permissions 14)

**Rationale**: 자동 추출 + 박제로 (a) 후속 reviewer 가 동일 결정 재현 가능, (b) caller cleanup 의 truth source 가 명확, (c) v1 의 추정성 결정 (claude.ts/client.ts modify vs delete 등) 의 결함 차단.

**Alternatives**:
- (rejected) v1 의 수동 grep + 추측 결정: KOSMOS-needed file 까지 deletion 결정에 포함된 결함 발생 (이번 v2 가 보정).
- (rejected) deletion 후 typecheck 깨지면 caller cleanup: 비효율 + caller 가 transitive 면 어디까지 삭제할지 불명확.

---

## R-2 — 8 callsite (queryHaiku / queryWithModel / verifyApiKey) 결정 매트릭스 (v1 유지)

**Q**: 각 callsite 가 KOSMOS 시민 use case 에서 살아있는가?

**Decision matrix** (v1 그대로):
| Callsite | 기능 | KOSMOS 결정 |
|---|---|---|
| `cli/print.ts` (verifyApiKey + queryHaiku) | Anthropic API key 검증 + 한 줄 응답 출력 | DELETE — KOSMOS는 FriendliAI 단일 provider, API key 검증 흐름 다름 |
| `commands/insights.ts` (queryWithModel) | claude-code 사용 통계 인사이트 | DELETE — 시민 use case 아님 |
| `commands/rename/generateSessionName.ts` (queryHaiku) | 세션 자동 명명 | DELETE — 본 Epic 은 deletion 만; K-EXAONE 한국어 자동 명명 별도 spec (Deferred) |
| `components/Feedback.tsx` (queryHaiku) | 피드백 자동 분류 | DELETE — claude.ai 결제 / 1P 텔레메트리 (Spec 1633) |
| `services/toolUseSummary/toolUseSummaryGenerator.ts` (queryHaiku) | 도구 사용 요약 자동 생성 | DELETE — K-EXAONE 한국어 요약 별도 spec (Deferred) |
| `tools/WebFetchTool/utils.ts` (queryHaiku) | WebFetch 결과 요약 | DELETE — WebFetch tool 은 보존 (MVP7), summary 기능만 dead. 0 importer |
| `utils/mcp/dateTimeParser.ts` (queryHaiku) | 자연어 → datetime 파싱 | DELETE — KOSMOS DateParser 보조 도구 (MVP7) 와 별개; 0 importer |
| `utils/sessionTitle.ts` (queryHaiku) | 세션 제목 자동 추출 | DELETE — generateSessionName.ts 와 중복 |
| `utils/shell/prefix.ts` (queryHaiku) | shell prompt prefix 자동 짓기 | DELETE — 시민 use case 아님; 0 importer |

**Rationale**: KOSMOS는 시민 use case 만 보존. claude-code 의 개발자-중심 자동 요약 / 분석 도구는 대부분 dead. K-EXAONE migration 은 별도 spec.

---

## R-3 — Constitution II 잔재 평가 (v2 — caller-graph 박제로 결론 정정)

**Q**: `tui/src/utils/permissions/` 와 `tui/src/schemas/ui-l2/permission.ts` 의 caller 가 누구인가?

**v1 결론** (caller-graph 미검토): "사전 grep 결과 caller 모두 Spec 033 잔재 또는 Spec 035 receipt UX 의 미통합 배선" — **미검증 추정**.

**v2 결정 (caller-graph.json 박제 후)**:

1. **`utils/permissions/permissionSetup.ts`** (11 importer):
   - `main.tsx`, `EnterPlanModeTool`, `markdownConfigLoader`, `forkedAgent`, `applySettingsChange`, `processSlashCommand`, `cli/print`, `AppState`, `REPL`, `Config`, `ExitPlanModePermissionRequest`, `PromptInput`, `useReplBridge`, `useAutoModeUnavailableNotification`, `plan/plan`
   - 모두 KOSMOS TUI 의 정상 사용 (Plan mode / Settings / REPL / Permission setup UX)
   - Anthropic-token = 0 / sdk-compat = 0 / growthbook = 0 / `feature()` 만 12회 (in-file dead-flag, 별도 정리 영역)
   - **결론: KEEP** (Constitution II 비충돌 — KOSMOS-invented 권한 분류 토큰 0)

2. **`utils/permissions/permissions.ts`** (14 importer):
   - `tools.ts` (registry), `WebFetchTool`, `AgentTool`, `BashTool`, `PowerShellTool`, `SkillTool`, `promptShellExecution`, `attachments`, `processSlashCommand`, `inProcessRunner`, `execAgentHook`, `structuredIO`, `cli/print`, `applySettingsChange`, `PermissionRuleList`, `interactiveHandler`, `mcp` entry, `useCanUseTool`, `toolHooks`
   - KOSMOS Tool registry + 모든 Tool 의 permission 검사 인프라
   - Anthropic-token = 0 / sdk-compat = 1 (`APIUserAbortError`) / growthbook = 1 / `feature()` = 7 회
   - sdk-compat APIUserAbortError import 1건 + growthbook 1건은 in-file 정리 영역 (file 자체 KEEP)
   - **결론: KEEP**

3. **`utils/permissions/yoloClassifier.ts`** (2 importer):
   - `AgentTool/agentToolUtils`, `cli/handlers/autoMode`
   - sdk-compat = 2 / growthbook = 1 / `feature()` = 6 / Anthropic 타입 의존
   - KOSMOS 는 growthbook A/B testing 안 씀 + Anthropic 의존
   - **결론: DELETE** + 2 caller cleanup

4. **`schemas/ui-l2/permission.ts`** (5 importer; 30 list 외):
   - `PermissionReceiptContext`, `ExportPdfDialog`, `commands/export`, `commands/consent`, `i18n/uiL2`
   - 모두 Spec 035 UI L2 receipt UX 의 출력 측 (PermissionLayerT/PermissionDecisionT receipt-rendering enums)
   - Anthropic-token = 0 / sdk-compat = 0
   - PermissionLayerT/PermissionDecisionT 는 Spec 033 5-mode spectrum (mode_state / aal_level / pipa_class 등 KOSMOS-invented 권한 분류) 와 별개 — receipt 출력용
   - **결론: KEEP** + decision-log.md 박제

**Rationale**: Constitution II 가 NON-NEGOTIABLE 하게 금지하는 것은 "KOSMOS-invented 권한 분류 (5-mode spectrum / pipa_class / auth_level / permission_tier / is_personal_data / is_irreversible / requires_auth / dpa_reference)". CC-restored 의 정상 permissions 인프라 (PermissionMode / PermissionRule / classifierShared / yoloClassifier 등) 와 Spec 035 의 receipt UX schema 는 별개. v1 가 그 구별 부재로 KOSMOS-needed 를 포함했고, v2 가 caller-graph 박제로 정정.

**Alternatives**:
- (rejected) v1 의 보수적 일괄 deletion: KOSMOS TUI 의 11+14 importer 광범위 회귀.
- (rejected) Constitution II 의 token list 를 grep gate 에 그대로 적용: plugin-init.ts (Spec 1636) + VerifyPrimitive.ts (Spec 031) 의 합법 사용 (auth_level / pipa_class / is_irreversible / dpa_reference / is_personal_data) 까지 0 행 invariant 로 잡혀 grep gate 통과 불가능. v2 의 FR-008 grep gate 가 Spec 1633 closure 토큰 (verifyApiKey / queryHaiku / queryWithModel / @anthropic-ai/) 만 0 행 invariant 로 좁힘.

---

## R-4 — 6 KOSMOS-only Tool 시민 use case 평가 (v1 유지)

**Q**: 6 도구 (MonitorTool / ReviewArtifactTool / SuggestBackgroundPRTool / TungstenTool / VerifyPlanExecutionTool / WorkflowTool) 가 시민 use case 에 사용 가능?

**Decision matrix** (v1 그대로):
| Tool | claude-code original purpose | KOSMOS 시민 use case 평가 |
|---|---|---|
| MonitorTool | 백그라운드 작업 모니터링 | DELETE — 시민이 모니터링할 백그라운드 작업 없음 (KOSMOS는 동기 lookup/submit 흐름) |
| ReviewArtifactTool | PR 산출물 리뷰 | DELETE — 시민이 PR 리뷰할 일 없음 |
| SuggestBackgroundPRTool | 백그라운드 PR 제안 | DELETE — 동상 |
| TungstenTool | (미상 / claude-code 내부 도구) | DELETE — 도구 README/주석 검토 후 시민 use case 확인 불가 |
| VerifyPlanExecutionTool | 계획 실행 검증 | DELETE — claude-code dev workflow tool |
| WorkflowTool | 다단계 워크플로 도구 | DELETE — KOSMOS multi-step submit 시나리오는 system prompt + primitive chain (Spec 022) 으로 처리, 별도 도구 불필요 |

**v2 박제 상태**: sonnet 1차 commit `2f9663d` 에서 6 디렉토리 모두 deletion 완료. 본 Epic 에서 추가 작업 없음.

---

## R-5 — bun test baseline 측정 절차 (v1 유지)

**Q**: NEW failure 0 invariant 검증의 baseline 시점은?

**Decision**:
1. cleanup 시작 직전: sonnet 1차 commit `2f9663d` 직후 baseline-test.txt 박제 (이미 박제됨)
2. cleanup 완료 후: `bun test 2>&1 | tee after-test.txt`
3. Diff: `diff <(grep -E "fail" baseline-test.txt | sort -u) <(grep -E "fail" after-test.txt | sort -u)` — after only 행이 NEW failure.

기존 baseline 의 pre-existing failure (snapshot 1 건) 는 그대로 유지. cleanup 으로 인한 import 누락 등 추가 failure 가 0 이어야 acceptance.

**Rationale**: KOSMOS bun test 는 약 983 pass / 1 fail (snapshot) 이 baseline. cleanup 으로 테스트 코드도 같이 삭제되면 일부 failure 가 자연 사라질 수도 있고 (good), pass 수가 줄어들 수도 있음 (also acceptable, "no NEW failure" gate 는 통과).

---

## Constitution Re-check (post-research v2)

R-1 (자동 박제) ~ R-5 (baseline) 모두 신규 dependency 0 / 신규 추상화 0 / Spec 1633 closure 토큰 (verifyApiKey / queryHaiku / queryWithModel / @anthropic-ai/) 잔존 0 invariant 보존. PASS 유지. Phase 1 진입 가능.

caller-graph + disposition 박제로 v1 의 결함 (KOSMOS-needed file 까지 deletion 포함) 차단. Constitution II 의 "KOSMOS-invented 권한 분류" 금지는 Spec 1633 closure 토큰 list 와 분리되어 별도 audit 영역으로 명시.
