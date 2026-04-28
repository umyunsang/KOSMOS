# Quickstart — UI Residue Cleanup (Epic β)

**Date**: 2026-04-29 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md) · **Data Model**: [data-model.md](./data-model.md)

본 quickstart 는 implement 단계의 reproducibility 박제. Sonnet teammate / 후속 reviewer 가 동일 절차로 cleanup 재실행 가능.

---

## 0. 사전 조건

- Worktree: `/Users/um-yunsang/KOSMOS-w-2293/` on branch `2293-ui-residue-cleanup`
- main 의 `bc523b7` (Epic α merged) 베이스
- `cd tui && bun install` 완료
- 신규 dependency 0 (FR-008)

```bash
cd /Users/um-yunsang/KOSMOS-w-2293
git rev-parse HEAD  # → bc523b7 (또는 그 이후 Epic β 작업 commit)
git status --short
```

---

## 1. R1 단계 — bun test baseline 박제

cleanup 시작 직전 결과를 박제 — NEW failure 0 invariant 의 비교 기준.

```bash
cd /Users/um-yunsang/KOSMOS-w-2293/tui
bun install        # 처음 한 번
bun typecheck 2>&1 | tee ../specs/2293-ui-residue-cleanup/baseline-typecheck.txt
bun test 2>&1 | tee ../specs/2293-ui-residue-cleanup/baseline-test.txt
```

검증:
```bash
grep -cE '^(pass|fail|✓|✗) ' /Users/um-yunsang/KOSMOS-w-2293/specs/2293-ui-residue-cleanup/baseline-test.txt
```

---

## 2. R2 단계 — services/api 17 잔재 + 1 tokenEstimation 삭제 (US1)

### 2.1 importer 추적

```bash
cd /Users/um-yunsang/KOSMOS-w-2293
TARGETS="adminRequests|claude|client|errorUtils|errors|filesApi|firstTokenDate|grove|logging|overageCreditGrant|promptCacheBreakDetection|referral|sessionIngress|ultrareviewQuota|usage|withRetry|tokenEstimation"
grep -rE "from\s+['\"][./~@]*services/api/(${TARGETS})['\"]" tui/src/ | sort -u
grep -rE "from\s+['\"][./~@]*services/(${TARGETS})['\"]" tui/src/ | sort -u
```

각 importer 의 호출부를 평가:
- (a) Dead → caller 함수/블록 통째 삭제
- (b) Live + 대체 가능 → KOSMOS 등가물로 호출 교체 (FriendliAI / IPC / memdir / i18n)
- (c) Type-only re-export → Epic γ #2294 transfer (Decision Log 에 기록)

### 2.2 17 + 1 파일 deletion

```bash
cd /Users/um-yunsang/KOSMOS-w-2293
git rm tui/src/services/api/{adminRequests,claude,client,errorUtils,errors,filesApi,firstTokenDate,grove,logging,overageCreditGrant,promptCacheBreakDetection,referral,sessionIngress,ultrareviewQuota,usage,withRetry}.ts
git rm tui/src/services/tokenEstimation.ts
```

### 2.3 8 callsite migration

각 callsite 별로 (research.md § R-2 매트릭스 적용):
- `cli/print.ts` → DELETE caller block
- `commands/insights.ts` → DELETE caller block
- `commands/rename/generateSessionName.ts` → MIGRATE to FriendliAI 한국어 자동 명명 OR DELETE if dead
- `components/Feedback.tsx` → DELETE
- `services/toolUseSummary/toolUseSummaryGenerator.ts` → EVALUATE and decide
- `tools/WebFetchTool/utils.ts` → EVALUATE and decide
- `utils/mcp/dateTimeParser.ts` → DELETE (Spec 022 DateParser 보조 도구로 대체됨)
- `utils/sessionTitle.ts` → DELETE (generateSessionName 와 중복)
- `utils/shell/prefix.ts` → DELETE

각 결정을 `decision-log.md § Callsite Migrations` 표에 박제.

### 2.4 grep gate

```bash
grep -rE 'queryHaiku|queryWithModel|verifyApiKey' tui/src/
# → 0 행이어야 함
```

---

## 3. R3 단계 — utils/permissions/ 3 잔재 + ui-l2/permission.ts 평가 (US2)

### 3.1 3 잔재 deletion

```bash
cd /Users/um-yunsang/KOSMOS-w-2293
grep -rE "from\s+['\"][./~@]*utils/permissions/(permissionSetup|permissions|yoloClassifier)['\"]" tui/src/
git rm tui/src/utils/permissions/permissionSetup.ts
git rm tui/src/utils/permissions/permissions.ts
git rm tui/src/utils/permissions/yoloClassifier.ts
```

caller 가 발견되면 caller 도 같이 cleanup (Constitution II 강제).

### 3.2 ui-l2/permission.ts 평가 + (대부분) deletion

```bash
grep -rE 'PermissionDecisionT|PermissionLayerT' tui/src/
# 사용처 0 또는 dead caller 만 → DELETE
git rm tui/src/schemas/ui-l2/permission.ts
```

만약 살아있는 caller 발견 시 `decision-log.md` 에 keep + 사유 + Spec 인용. (Constitution II 강제 — bar 매우 높음)

### 3.3 grep gate

```bash
grep -rE 'PermissionDecisionT|PermissionLayerT|pipa_class|auth_level|permission_tier|is_personal_data|is_irreversible|requires_auth|dpa_reference' tui/src/
# → 0 행이어야 함
```

---

## 4. R4 단계 — 6 KOSMOS-only Tool 평가 + deletion (US3)

### 4.1 각 Tool 평가 (research.md § R-4 매트릭스)

6 도구 모두 시민 use case 0 으로 판정 → 6 모두 DELETE 권장.

```bash
cd /Users/um-yunsang/KOSMOS-w-2293
git rm -rf tui/src/tools/MonitorTool/
git rm -rf tui/src/tools/ReviewArtifactTool/
git rm -rf tui/src/tools/SuggestBackgroundPRTool/
git rm -rf tui/src/tools/TungstenTool/
git rm -rf tui/src/tools/VerifyPlanExecutionTool/
git rm -rf tui/src/tools/WorkflowTool/
```

### 4.2 tools.ts registry 갱신

```bash
$EDITOR tui/src/tools.ts
# import 줄 6 개 + array entry 6 개 제거
```

### 4.3 Decision Log 박제

`decision-log.md § KOSMOS-only Tool Decisions` 표에 6 entries (모두 `delete` + 사유 + research.md § R-4 인용).

---

## 5. R5 단계 — @anthropic-ai/ import 제거

```bash
cd /Users/um-yunsang/KOSMOS-w-2293
grep -rE "@anthropic-ai/" tui/src/
# 발견된 import 줄 모두 제거 또는 KOSMOS 등가 import 로 교체
```

`tui/src/utils/plugins/mcpbHandler.ts` 가 가장 가능성 높음 — caller 확인 후 import 제거 또는 caller 함께 cleanup.

---

## 6. R6 단계 — 검증 (typecheck + test + grep gate)

### 6.1 typecheck

```bash
cd /Users/um-yunsang/KOSMOS-w-2293/tui
bun typecheck 2>&1 | tee ../specs/2293-ui-residue-cleanup/after-typecheck.txt
# exit 0 + 0 errors 필수
```

### 6.2 bun test

```bash
bun test 2>&1 | tee ../specs/2293-ui-residue-cleanup/after-test.txt
diff <(grep -E 'fail' ../specs/2293-ui-residue-cleanup/baseline-test.txt | sort -u) \
     <(grep -E 'fail' ../specs/2293-ui-residue-cleanup/after-test.txt | sort -u)
# after only 행 = NEW failure (0 이어야 PASS)
```

### 6.3 종합 grep gate (FR-008)

```bash
cd /Users/um-yunsang/KOSMOS-w-2293
grep -rE 'PermissionDecisionT|PermissionLayerT|pipa_class|auth_level|permission_tier|is_personal_data|is_irreversible|requires_auth|dpa_reference|verifyApiKey|queryHaiku|queryWithModel|@anthropic-ai/' tui/src/
# → 0 행이어야 함 (Constitution II + Spec 1633 closure 동시 검증)
```

---

## 7. R7 단계 — commit + push + PR

```bash
cd /Users/um-yunsang/KOSMOS-w-2293
git add -A specs/2293-ui-residue-cleanup/
git commit -m "$(cat <<'EOF'
feat(2293): kosmos-original ui residue cleanup

- 17 services/api Anthropic dispatcher 잔재 + 1 tokenEstimation 삭제
- 8 callsite (queryHaiku/queryWithModel/verifyApiKey) cleanup — N migrate / N delete
- 3 utils/permissions Spec 033 잔재 삭제
- 1 schemas/ui-l2/permission.ts 삭제 (Constitution II)
- 6 KOSMOS-only Tool 삭제 (시민 use case 0)
- @anthropic-ai/ import 제거

Authority:
- AGENTS.md § CORE THESIS
- .specify/memory/constitution.md § II Fail-Closed Security (NON-NEGOTIABLE)
- specs/1979-plugin-dx-tui-integration/cc-source-scope-audit.md § 1.2.1, § 1.2.2, § 1.3.4
- specs/2292-cc-parity-audit/cc-parity-audit.md (Epic α 직접 입력)

Closes #2293
EOF
)"

git push -u origin 2293-ui-residue-cleanup
gh pr create --title "feat(2293): kosmos-original ui residue cleanup" --body "Closes #2293"
```

### CI monitoring

```bash
gh pr checks <PR#> --watch --interval 15
```

### Codex review handling

```bash
gh api repos/umyunsang/KOSMOS/pulls/<PR#>/comments \
  --jq '.[] | select(.user.login == "chatgpt-codex-connector[bot]") | "\(.path):\(.line) \(.body)"'
# P1 모두 해소 (commit + reply)
```
