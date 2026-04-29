# Quickstart — UI Residue Cleanup (Epic β · v2)

**Date**: 2026-04-29 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md) · **Data Model**: [data-model.md](./data-model.md)
**Authority**: caller-graph.json + disposition.json (이번 Epic 의 v2 입력)

본 quickstart 는 implement 단계의 reproducibility 박제. Sonnet teammate / 후속 reviewer 가 동일 절차로 cleanup 재실행 가능.

---

## 0. 사전 조건

- Worktree: `/Users/um-yunsang/KOSMOS-w-2293/` on branch `2293-ui-residue-cleanup`
- 시작점: `2f9663d` (Sonnet 1차 안전 commit — 6 KOSMOS-only Tool deletion + 5 callsite cleanup + claude.ts modify 일부)
- `cd tui && bun install` 완료
- 신규 dependency 0 (FR-008)

```bash
cd /Users/um-yunsang/KOSMOS-w-2293
git rev-parse HEAD  # → 2f9663d (또는 그 이후 v2 작업 commit)
git status --short
```

---

## 1. R1 단계 — caller-graph.json + disposition.json 박제

`scripts/build-caller-graph.py` 가 30 Cleanup-needed file 의 importer 그래프 + dependency token 매치를 JSON 으로 출력. v2 spec 의 disposition.json 은 그 출력을 기반으로 LEAD 가 결정.

```bash
cd /Users/um-yunsang/KOSMOS-w-2293
python3 specs/2293-ui-residue-cleanup/scripts/build-caller-graph.py
# → specs/2293-ui-residue-cleanup/data/caller-graph.json (30 row)
ls specs/2293-ui-residue-cleanup/data/
# caller-graph.json + disposition.json 있어야 함
```

검증:
- 30 row × { kosmos_path, importer_count, importers, internal_anthropic_tokens, dependency_hits }
- disposition.json 의 28 DELETE + 3 KEEP (permissionSetup / permissions / ui-l2/permission)

---

## 2. R2 단계 — bun test baseline 박제

`baseline-test.txt` 는 sonnet 1차 commit `2f9663d` 직후 측정값 (이미 박제됨). v2 cleanup 후 NEW failure 0 invariant 의 비교 기준.

```bash
cd /Users/um-yunsang/KOSMOS-w-2293/tui
bun typecheck 2>&1 | tee ../specs/2293-ui-residue-cleanup/baseline-typecheck.txt
bun test 2>&1 | tee ../specs/2293-ui-residue-cleanup/baseline-test.txt
```

(이미 박제되어 있으면 skip 가능)

---

## 3. R3 단계 — 28 DELETE target cleanup (US1)

### 3.1 0 importer + dead 확실 (12 file) — 단순 deletion

```bash
cd /Users/um-yunsang/KOSMOS-w-2293
git rm tui/src/services/api/claude.ts          # 1098 line, 0 imp, sdk-compat dispatcher
git rm tui/src/services/api/client.ts          # 40 line, 0 imp, Anthropic HTTP
git rm tui/src/cli/print.ts                    # 5601 line, 0 imp, claude-code CLI entry
git rm tui/src/commands/insights.ts            # 3164 line, 0 imp, /insights slash command
git rm tui/src/tools/WebFetchTool/utils.ts     # 522 line, 0 imp, queryHaiku WebFetch summary
git rm tui/src/utils/mcp/dateTimeParser.ts     # 38 line, 0 imp, queryHaiku date parser
git rm tui/src/utils/shell/prefix.ts           # 237 line, 0 imp, queryHaiku shell prefix
```

(7 file = 7 git rm)

### 3.2 N importer + caller cleanup 동시 (16 file) — git rm + Edit

각 file 의 `importers` (caller-graph.json 박제) 에서 import 라인 삭제 + caller block 정리. caller 가 dead 면 caller block 통째 삭제, alive 인 caller (`tokenEstimation` 의 11 importer 같은) 가 dead path 만 사용하면 그 path 만 삭제.

#### services/api/* 14 file (16 importer 합계)

```bash
git rm tui/src/services/api/{adminRequests,errorUtils,errors,filesApi,firstTokenDate,grove,logging,overageCreditGrant,promptCacheBreakDetection,referral,sessionIngress,ultrareviewQuota,usage,withRetry}.ts
```

각 file 의 importer 추적 + Edit:
- `errorUtils` (5 imp), `errors` (6 imp), `logging` (4 imp), `referral` (5 imp), `withRetry` (2 imp), `promptCacheBreakDetection` (3 imp), `usage` (3 imp), `sessionIngress` (2 imp), `filesApi` (2 imp), `overageCreditGrant` (2 imp), `firstTokenDate` (1 imp), `adminRequests` (1 imp), `grove` (1 imp), `ultrareviewQuota` (1 imp)

→ caller-graph.json 의 `importers` field 가 truth source. importer file 마다 import 라인 + 호출 코드 정리.

#### tokenEstimation.ts (11 importer — HIGH risk)

```bash
git rm tui/src/services/tokenEstimation.ts
```

11 importer (LocalMainSessionTask / FileReadTool / contextAnalysis / analyzeContext / tokens / statusNoticeHelpers / api / mcpValidation / doctorContextWarnings / loadSkillsDir / SessionMemory/prompts) 에서 token-estimation 호출 정리. 본 Epic 영역에서 단순 deletion 후 caller 깨지면 typecheck 실패 → 추가 caller cleanup.

#### 기타 8 file (callsite cleanup)

```bash
git rm tui/src/commands/rename/generateSessionName.ts  # 1 imp
git rm tui/src/components/Feedback.tsx                 # 1 imp
git rm tui/src/services/toolUseSummary/toolUseSummaryGenerator.ts  # 1 imp
git rm tui/src/utils/permissions/yoloClassifier.ts     # 2 imp
git rm tui/src/utils/plugins/mcpbHandler.ts            # 2 imp (@anthropic-ai/)
git rm tui/src/utils/sessionTitle.ts                   # 4 imp
```

각 importer 의 import 라인 + dead block 삭제.

### 3.3 grep gate (FR-002 + FR-008 + FR-010)

```bash
grep -rE 'queryHaiku|queryWithModel|verifyApiKey' tui/src/ --include='*.ts' --include='*.tsx'
# → 0 행

grep -rE '@anthropic-ai/' tui/src/ --include='*.ts' --include='*.tsx'
# → 0 행 (FR-010)

grep -rE 'verifyApiKey|queryHaiku|queryWithModel|@anthropic-ai/' tui/src/ --include='*.ts' --include='*.tsx'
# → 0 행 (FR-008 종합)
```

---

## 4. R4 단계 — 3 KEEP target 박제 (US2 + US3)

### 4.1 utils/permissions/permissionSetup.ts + permissions.ts (US2)

작업 없음. caller-graph.json 의 11 + 14 importer 가 KOSMOS-needed 박제. decision-log.md § Cleanup Targets 표에 KEEP 행 추가:

```markdown
| utils/permissions/permissionSetup.ts | 11 (main.tsx, REPL, Config, plan.tsx, etc.) | KEEP | KOSMOS-needed CC permissions setup; Anthropic-token = 0; in-file `feature()` cleanup deferred to follow-up | caller-graph.json #25, disposition.json |
| utils/permissions/permissions.ts | 14 (tools.ts, AgentTool, BashTool, REPL, etc.) | KEEP | KOSMOS-needed CC permissions core; only sdk-compat APIUserAbortError import + 7 feature() removable | caller-graph.json #26, disposition.json |
```

### 4.2 schemas/ui-l2/permission.ts (US3)

작업 없음. caller-graph 5 importer (PermissionReceiptContext, ExportPdfDialog, export, consent, i18n/uiL2) — Spec 035 receipt UX. decision-log.md § ui-l2/permission Decision 섹션 갱신:

```markdown
| schemas/ui-l2/permission.ts | 5 (PermissionReceiptContext, ExportPdfDialog, export, consent, i18n/uiL2) | KEEP | Spec 035 UI L2 receipt UX schema (PermissionLayerT/PermissionDecisionT receipt-rendering enums, NOT Spec 033 5-mode spectrum residue) | caller-graph 별도 검증 (30 list 외), disposition.json |
```

---

## 5. R5 단계 — 6 KOSMOS-only Tool 결정 박제 (US3 보조)

이미 sonnet 1차 commit `2f9663d` 에서 6 디렉토리 deletion 완료. decision-log.md § KOSMOS-only Tool Decisions 섹션은 v1 의 6 entry 그대로 유지 (research.md § R-4 인용).

검증:
```bash
cd /Users/um-yunsang/KOSMOS-w-2293
ls tui/src/tools/ | grep -E '^(MonitorTool|ReviewArtifactTool|SuggestBackgroundPRTool|TungstenTool|VerifyPlanExecutionTool|WorkflowTool)$'
# → (none)
```

---

## 6. R6 단계 — 검증 (typecheck + test + grep gate)

### 6.1 typecheck (FR-006 / SC-005)

```bash
cd /Users/um-yunsang/KOSMOS-w-2293/tui
bun typecheck 2>&1 | tee ../specs/2293-ui-residue-cleanup/after-typecheck.txt
# exit 0 + 0 errors 필수
```

### 6.2 bun test (FR-007 / SC-006)

```bash
bun test 2>&1 | tee ../specs/2293-ui-residue-cleanup/after-test.txt
diff <(grep -E 'fail' ../specs/2293-ui-residue-cleanup/baseline-test.txt | sort -u) \
     <(grep -E 'fail' ../specs/2293-ui-residue-cleanup/after-test.txt | sort -u)
# after only 행 = NEW failure (0 이어야 PASS)
```

### 6.3 종합 grep gate (FR-008 / SC-007)

```bash
cd /Users/um-yunsang/KOSMOS-w-2293
grep -rE 'verifyApiKey|queryHaiku|queryWithModel|@anthropic-ai/' tui/src/ --include='*.ts' --include='*.tsx'
# → 0 행 (Spec 1633 closure invariant)
```

### 6.4 caller-graph + disposition 박제 commit 확인

```bash
git status specs/2293-ui-residue-cleanup/data/
# caller-graph.json + disposition.json 모두 staged 또는 committed
```

---

## 7. R7 단계 — commit + push + PR

### 7.1 Commit

```bash
cd /Users/um-yunsang/KOSMOS-w-2293
git add -A specs/2293-ui-residue-cleanup/
git commit -m "$(cat <<'EOF'
feat(2293): kosmos-original ui residue cleanup (v2 caller-graph based)

- 28 Anthropic dispatcher residue files DELETED (caller-graph + disposition.json driven)
  - 14 services/api/* (adminRequests, claude, client, errorUtils, errors, filesApi,
    firstTokenDate, grove, logging, overageCreditGrant, promptCacheBreakDetection,
    referral, sessionIngress, ultrareviewQuota, usage, withRetry)
  - tokenEstimation.ts (11 importer caller cleanup)
  - cli/print.ts + commands/insights.ts (claude-code 내부 entry/command)
  - commands/rename/generateSessionName.ts + components/Feedback.tsx
  - services/toolUseSummary/toolUseSummaryGenerator.ts + tools/WebFetchTool/utils.ts
  - utils/mcp/dateTimeParser.ts + utils/shell/prefix.ts
  - utils/permissions/yoloClassifier.ts (sdk-compat + growthbook)
  - utils/plugins/mcpbHandler.ts (@anthropic-ai/)
  - utils/sessionTitle.ts
- 3 KOSMOS-needed files KEPT (caller-graph 검증 박제)
  - utils/permissions/permissionSetup.ts (11 importer; main.tsx/REPL/Config/plan.tsx 핵심)
  - utils/permissions/permissions.ts (14 importer; tools.ts/AgentTool/BashTool 핵심)
  - schemas/ui-l2/permission.ts (5 importer; Spec 035 receipt UX, Spec 033 spectrum 잔재 X)
- 6 KOSMOS-only Tool deletion = sonnet 1차 commit 2f9663d 에서 이미 완료
- v2 spec / quickstart / decision-log / data-model / tasks 전면 재작성
  (v1 의 30 file 일괄 deletion 가설이 caller-graph 미검토라 KOSMOS-needed file 까지
   광범위 회귀 위험이었던 결함 보정)
- caller-graph.json + disposition.json 박제 (specs/2293-ui-residue-cleanup/data/)

Authority:
- AGENTS.md § CORE THESIS — KOSMOS = AX-infrastructure callable-channel client
- .specify/memory/constitution.md § II Fail-Closed Security (NON-NEGOTIABLE)
- specs/1979-plugin-dx-tui-integration/cc-source-scope-audit.md § 1.2.1, § 1.2.2, § 1.3.4
- specs/2292-cc-parity-audit/cc-parity-audit.md (Epic α 직접 입력)
- specs/2293-ui-residue-cleanup/data/caller-graph.json (v2 박제)
- specs/2293-ui-residue-cleanup/data/disposition.json (v2 박제)

Closes #2293
EOF
)"

git push -u origin 2293-ui-residue-cleanup
```

### 7.2 PR

```bash
gh pr create --title "feat(2293): kosmos-original ui residue cleanup (v2 caller-graph based)" --body "$(cat <<'EOF'
## Summary
- 28 Anthropic dispatcher residue files deleted (caller-graph + disposition.json 기반)
- 3 KOSMOS-needed files kept (permissionSetup / permissions / ui-l2/permission) — caller graph 검증 박제
- 6 KOSMOS-only Tool deletion 은 sonnet 1차 commit `2f9663d` 에서 완료
- v1 의 30 file 일괄 deletion 가설 결함을 caller graph 박제로 보정 (v2)

## Test plan
- [x] `bun typecheck` exit 0 + 0 errors (after-typecheck.txt 박제)
- [x] `bun test` NEW failure 0 (after-test.txt + diff 박제)
- [x] FR-008 grep gate 0 행 (`verifyApiKey|queryHaiku|queryWithModel|@anthropic-ai/`)
- [x] caller-graph.json + disposition.json + decision-log.md 박제

Closes #2293
EOF
)"
```

### 7.3 CI monitoring

```bash
gh pr checks <PR#> --watch --interval 15
```

### 7.4 Codex review handling

```bash
gh api repos/umyunsang/KOSMOS/pulls/<PR#>/comments \
  --jq '.[] | select(.user.login == "chatgpt-codex-connector[bot]") | "\(.path):\(.line) \(.body)"'
# P1 모두 해소 (commit + reply)
```

### 7.5 Copilot review gate (AGENTS.md § Copilot Review Gate)

```bash
# push 후 2분 대기 후 gate 상태 확인
gh api graphql -f query='...' \
  --jq '.data.repository.pullRequest.reviewRequests'
# in_progress 2분 이상 시 GraphQL requestReviewsByLogin 재요청
# 안 풀리면 사용자에게 copilot-review-bypass label 요청
```
