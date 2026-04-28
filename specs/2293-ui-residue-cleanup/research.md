# Phase 0 Research — UI Residue Cleanup (Epic β)

**Date**: 2026-04-29 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**Authority**: AGENTS.md § CORE THESIS · `.specify/memory/constitution.md § II` · cc-source-scope-audit § 1.2.1/1.2.2/1.3.4 · cc-parity-audit.md (Epic α)

---

## Deferred Items 검증 (Constitution VI gate)

spec.md `Scope Boundaries & Deferred Items` 섹션:

| 항목 | Tracking | State |
|---|---|---|
| 6 KOSMOS-only Tool 보존 결정 도구 i18n | NEEDS TRACKING | 조건부 — 보존 도구 0 이면 자연 close |
| `claude.ts` type-only export 의 KOSMOS i18n / 라벨링 | #2294 (Epic γ) | OPEN ✅ |

`grep -niE '(future epic|future phase|separate epic|deferred to|out of scope for v1|later release)' spec.md plan.md`: Deferred 표 외부 매치 0 건. ✅ Principle VI 통과.

---

## R-1 — services/api 17 잔재 importer 추적 전략

**Q**: 17 services/api 파일을 안전하게 삭제하려면 importer 를 모두 추적해야 한다. 어떤 절차?

**Decision**: `grep -rE "from\s+'[./~@]*services/api/(adminRequests|claude|client|...)|import.*from\s+'[./~@]*services/api/(...)"` 로 importer 파일 list. 각 importer 에서 import 라인 + 호출부 분석:
- (a) 호출이 dead — 호출부 코드 블록 통째 삭제
- (b) 호출이 KOSMOS 등가물 (FriendliAI / IPC / memdir) 으로 대체 가능 — 호출부 교체
- (c) type-only re-export 인 경우 — Epic γ #2294 로 transfer (Deferred Items 항목)

**Rationale**: memory `feedback_no_stubs_remove_or_migrate` 강제 — 스텁 X. memory `project_tui_anthropic_residue` 가 명시한 4 alive callsite (verifyApiKey, queryHaiku ×2, queryWithModel) 가 본 cleanup 의 주 타겟.

**Alternatives**:
- (rejected) 잔재 파일만 삭제 후 import 에러 fix: typecheck 가 깨질 뿐 본질적 cleanup 아님.
- (rejected) 17 파일 모두 stub 으로 남기기: feedback_no_stubs_remove_or_migrate 위반.

---

## R-2 — 8 callsite (queryHaiku / queryWithModel / verifyApiKey) 결정 매트릭스

**Q**: 각 callsite 가 KOSMOS 시민 use case 에서 살아있는가?

**Decision matrix**:
| Callsite | 기능 | KOSMOS 결정 |
|---|---|---|
| `cli/print.ts` (verifyApiKey + queryHaiku) | Anthropic API key 검증 + 한 줄 응답 출력 | DELETE — KOSMOS는 FriendliAI 단일 provider, API key 검증 흐름 다름 |
| `commands/insights.ts` (queryWithModel) | claude-code 사용 통계 인사이트 | DELETE — 시민 use case 아님 |
| `commands/rename/generateSessionName.ts` (queryHaiku) | 세션 자동 명명 | MIGRATE — KOSMOS i18n 한국어 자동 명명으로 교체 (이미 i18n 인프라 있음, FriendliAI 호출로 swap) 또는 DELETE if dead |
| `components/Feedback.tsx` (queryHaiku) | 피드백 자동 분류 | DELETE — claude.ai 결제 / 1P 텔레메트리 (Spec 1633) |
| `services/toolUseSummary/toolUseSummaryGenerator.ts` (queryHaiku) | 도구 사용 요약 자동 생성 | EVALUATE — KOSMOS 시민 use case 가능 (한국어 요약). MIGRATE if alive, DELETE if dead. |
| `tools/WebFetchTool/utils.ts` (queryHaiku) | WebFetch 결과 요약 | EVALUATE — WebFetch 자체가 KOSMOS 보조 도구 (MVP 7), 요약 기능 살아있는지 caller 확인 |
| `utils/mcp/dateTimeParser.ts` (queryHaiku) | 자연어 → datetime 파싱 | EVALUATE — KOSMOS DateParser 보조 도구 (MVP 7) 와 별개; dead 가능성 높음 |
| `utils/sessionTitle.ts` (queryHaiku) | 세션 제목 자동 추출 | DELETE — generateSessionName.ts 와 중복 |
| `utils/shell/prefix.ts` (queryHaiku) | shell prompt prefix 자동 짓기 | DELETE — 시민 use case 아님 |

**Rationale**: KOSMOS는 시민 use case 만 보존. claude-code 의 개발자-중심 자동 요약 / 분석 도구는 대부분 dead. 단 KOROAD / KMA / HIRA 어댑터 결과의 한국어 요약은 KOSMOS-needed 일 수 있음 → 보조 도구 (Spec 022 main-tool 의 `lookup` 출력 후 요약) 로 별도 spec 영역.

**Alternatives**:
- (rejected) 모두 MIGRATE: 시민 use case 0 인 기능까지 K-EXAONE 호출로 마이그레이션 = dead code 유지.
- (rejected) 모두 DELETE without evaluation: dead 가 아닌 알이 작은 기능 (`generateSessionName` 같은) 의 회귀 가능.

---

## R-3 — Constitution II 잔재 매트릭스

**Q**: `tui/src/utils/permissions/` 와 `tui/src/schemas/ui-l2/permission.ts` 의 caller 가 누구인가?

**Decision**: 사전 grep 결과 (`grep -rE "from\s+.*['\"][./~@]*(utils/permissions|schemas/ui-l2/permission)['\"]" tui/src/`) 의 caller 모두 Spec 033 잔재 또는 Spec 035 receipt UX 의 미통합 배선. 본 Epic 은:
1. 3 utils/permissions 파일 + ui-l2/permission.ts 모두 DELETE 기본 결정
2. 비주류 caller 가 발견되면 Decision Log 에 단별로 기록 + Constitution II 와 충돌 시 caller 도 cleanup
3. Spec 035 receipt UX 통합은 Deferred Items #2297 (Epic ζ) territory — 본 Epic 에서 stub 추가 0

**Rationale**: Constitution II 가 NON-NEGOTIABLE 이므로 keep with rationale 의 bar 가 매우 높음. KOSMOS-invented enum 이 살아있는 caller 가 있다는 것은 곧 Constitution 위반.

**Alternatives**:
- (rejected) 보존 + sealed comment 처리: codebase 에 KOSMOS-invented enum 이 살아있는 한 Constitution II 위반.

---

## R-4 — 6 KOSMOS-only Tool 시민 use case 평가

**Q**: 6 도구 (MonitorTool / ReviewArtifactTool / SuggestBackgroundPRTool / TungstenTool / VerifyPlanExecutionTool / WorkflowTool) 가 시민 use case 에 사용 가능?

**Decision matrix**:
| Tool | claude-code original purpose | KOSMOS 시민 use case 평가 |
|---|---|---|
| MonitorTool | 백그라운드 작업 모니터링 | DELETE — 시민이 모니터링할 백그라운드 작업 없음 (KOSMOS는 동기 lookup/submit 흐름) |
| ReviewArtifactTool | PR 산출물 리뷰 | DELETE — 시민이 PR 리뷰할 일 없음 |
| SuggestBackgroundPRTool | 백그라운드 PR 제안 | DELETE — 동상 |
| TungstenTool | (미상 / claude-code 내부 도구) | DELETE — 도구 README/주석 검토 후 시민 use case 확인 불가 |
| VerifyPlanExecutionTool | 계획 실행 검증 | DELETE — claude-code dev workflow tool |
| WorkflowTool | 다단계 워크플로 도구 | EVALUATE — KOSMOS 의 multi-step submit 시나리오 (예: 정부24 제출) 에 활용 가능? 단 KOSMOS 의 multi-step 은 system prompt + primitive chain 으로 처리하므로 별도 도구 불필요. DELETE 권장. |

**Rationale**: 6 도구 모두 claude-code 의 dev-workflow tool 잔재. KOSMOS = 시민 도구 하네스 thesis 와 부합 안 함.

**Alternatives**:
- (rejected) WorkflowTool 보존 후 KOSMOS multi-step submit 시나리오 향후 통합: Spec 022 main-tool 의 4 primitive chain 으로 충분, 별도 WorkflowTool 추상화 중복.

---

## R-5 — bun test baseline 측정 절차

**Q**: NEW failure 0 invariant 검증의 baseline 시점은?

**Decision**:
1. cleanup 시작 직전: `cd tui && bun install && bun test 2>&1 | tee specs/2293-ui-residue-cleanup/baseline-test.txt`
2. cleanup 완료 후: `cd tui && bun test 2>&1 | tee specs/2293-ui-residue-cleanup/after-test.txt`
3. Diff: `diff <(grep -E "fail" baseline-test.txt | sort -u) <(grep -E "fail" after-test.txt | sort -u)` — after only 행이 NEW failure.

기존 baseline 의 pre-existing failure (예: snapshot 1 건) 는 그대로 유지. cleanup 으로 인한 import 누락 등 추가 failure 가 0 이어야 acceptance.

**Rationale**: KOSMOS bun test 는 약 983 pass / 1 fail (snapshot) 이 baseline. cleanup 후 테스트 코드도 같이 삭제되면 일부 failure 가 자연 사라질 수도 있고 (good), pass 수가 줄어들 수도 있음 (also acceptable, "no NEW failure" gate 는 통과).

---

## Constitution Re-check (post-research)

R-1~R-5 모두 신규 dependency 0 / 신규 추상화 0 / Constitution II 잔재 0 회 잔존 invariant 보존. PASS 유지. Phase 1 진입 가능.
