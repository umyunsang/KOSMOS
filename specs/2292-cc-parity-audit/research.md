# Phase 0 Research — CC Parity Audit (Epic α)

**Date**: 2026-04-29
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)
**Authority** (`docs/vision.md § Reference materials` 매핑):
- Layer = "Reference Audit" (constitution table 외 — 본 Epic 은 audit, source layer 가 아님)
- Primary reference: `.references/claude-code-sourcemap/restored-src/src/` — 1,884 .ts/.tsx (CC 2.1.88) — Constitution Principle I 의 project-wide 1차 reference
- Secondary references: `cc-source-scope-audit.md § 1.1, § 1.2, § 3` 의 분류 숫자 (1,531 / 73 / 212 / 274 / 68), `delegation-flow-design.md § 12` 의 final canonical architecture (audit 의 분류 기준 일부)
- Constitution `§ I. Reference-Driven Development` 의 reference mapping 표는 본 Epic 에는 직접 적용되지 않음 — 본 Epic 은 신규 layer 를 만들지 않고 existing parity 를 검증함.

---

## Deferred Items 검증 (Constitution VI gate)

`spec.md § Scope Boundaries & Deferred Items` 섹션에서 추출:

| 항목 | Tracking Issue | GitHub state (2026-04-29 시점) |
|---|---|---|
| Suspicious 파일 실제 수정 | #2293 (Epic β) | OPEN ✅ |
| 백엔드 `permissions/` 정리 + AdapterRealDomainPolicy | #2295 (Epic δ) | OPEN ✅ |
| 5-primitive 를 CC `Tool.ts` 에 align | #2294 (Epic γ) | OPEN ✅ |
| AX-infrastructure mock 어댑터 신설 | #2296 (Epic ε) | OPEN ✅ |
| End-to-end smoke + 정책 매핑 | #2297 (Epic ζ) | OPEN ✅ |
| System prompt rewrite | #2298 (Epic η) | OPEN ✅ |
| 표본 50 → 100 개 확장 (조건부) | NEEDS TRACKING | `/speckit-taskstoissues` 단계에서 placeholder issue 생성 또는 조건 미충족시 본문 삭제 |

**Unregistered deferral pattern scan** (`grep -niE '(future epic|future phase|separate epic|deferred to|out of scope for v1|later release|v2)' specs/2292-cc-parity-audit/spec.md`): Deferred Items 표 외부 매치 0 건. ✅ Principle VI 통과.

**Active Epic state note**: Epic α #2292 자체는 2026-04-28 에 사용자가 일시 close (`stateReason=COMPLETED`) — Initiative #2290 sub-issue 트리 재구성 commit `0bb17f3` 와 동시기. 사용자가 next-session-prompt v3 에서 #2292 를 active Epic 으로 재지정했으므로 PR `Closes #2292` 는 그대로 유효 (이슈 closed/open 무관 trace 유지). 자동 reopen 시도는 권한 부족으로 차단됨 — 사용자 머지 단계에서 수동 reopen 가능.

---

## R-1 — 1,604 KEEP / 73 SDK-import-only-diff / 212 modified file list 재계측

**Question**: `cc-source-scope-audit.md § 1.1, § 1.2` 가 주장하는 분류 숫자 (1,531 / 73 / 212 / 274 / 68) 가 audit 시점 (2026-04-29) 에서도 유효한가? 그리고 분류 list 를 어떻게 deterministic 하게 추출하나?

**Decision**: `find` + `diff -rq` 조합으로 두 디렉토리 (`tui/src/`, `.references/claude-code-sourcemap/restored-src/src/`) 의 매칭/비매칭 파일을 산출하고 `sort` 로 deterministic 순서 강제. 결과 list 를 `data/enumerated-{keep-1531|import-73|modified-212|kosmos-only-274|cc-only-68}.txt` 로 박제. 이 산출 단계가 FR-010 의 "drift 발견 시 정정" 요구를 자동 충족.

**Rationale**:
- `diff -rq` 는 텍스트/바이너리 무관 byte 비교만 보고 (not line-level). 이 단계에서 `Files differ` 행이 modified, `Only in restored-src` 가 cc-only DELETE, `Only in tui/src/` 가 KOSMOS-only ADDITIONS 후보.
- byte-identical 후보는 `diff -rq` 결과에 등장하지 않은 매칭 파일들. `comm` 으로 set 차집합으로 추출.
- SDK-import-only-diff 후보는 modified set 의 부분집합으로, 별도 R-3 절차로 가려냄.
- 모든 list 는 `LC_ALL=C sort` 로 환경 비의존 정렬 → 시드 사용시 reproducibility 보장.

**Alternatives considered**:
- **(rejected) `git diff --no-index`**: 두 디렉토리가 같은 repo 가 아니어도 작동하지만, 결과 형식이 patch-style 이라 enumeration 보다 line-diff 분석에 적합. 본 단계는 file-set 추출이 1차 목적이라 `diff -rq` 가 단순.
- **(rejected) Python `os.walk` + `hashlib`**: 더 정밀하지만 50 sample 검증은 Phase 0 가 아니라 Phase 1 spot-check 에서 하면 충분. enumeration 만 위해 Python 인프라 끌고오는 건 과잉.
- **(rejected) `rsync --dry-run --checksum`**: hash 비교 가능하지만 출력 파싱이 까다롭고 BSD/GNU rsync 차이가 있어 reproducibility 약함.

---

## R-2 — Byte-identical 표본 50 추출 (재현 가능)

**Question**: 1,531 (또는 R-1 재계측 결과) 모집단에서 50 random sample 을 어떻게 추출하면 (a) 재현 가능, (b) 환경 비의존, (c) 분류 산출물에 plaintext 박제 가능한가?

**Decision**: Python stdlib `random.Random(2292)` 시드 사용. 시드 값은 Epic 번호 `2292` 로 의미 부여. 모집단 list 는 R-1 산출물 (`data/enumerated-keep-1531.txt`) 의 정렬된 순서에서 sample. 50 sample list 와 시드 모두 산출물 plaintext appendix 에 박제 → 시드 유실 시에도 plaintext 가 절대 reference.

**Rationale**:
- `random.Random(seed)` 은 Python 3.x 보장 stable algorithm (Mersenne Twister) — Python 버전 무관 동일 시드 → 동일 sample.
- 시드 = `2292` 는 Epic 번호로 self-document.
- plaintext 박제로 reproducibility 가 시드 보존 의존을 벗어남 (FR-006 + spec.md edge case).
- 50 표본은 1,531 모집단 대비 ≈3.27% — 50/50 match 시 Wilson score 95% lower bound ≈ 92.9% parity. spec.md SC-002 의 표현 ("≥94% parity") 은 보수적이므로 본 산출물에서 정확한 통계로 정정 (50/50 match → 95% 신뢰도 ≥ 92.9% parity, 문구만 `delegation-flow-design.md` 식 보수 표현 채택 가능).
- 표본 수를 더 늘리려면 spec.md Deferred Items 표의 "표본 50 → 100" 항목 트리거.

**Alternatives considered**:
- **(rejected) shuf -n 50 -seed 2292**: GNU shuf 의 `--random-source` 는 `/dev/urandom` 대체로 시드 가능하지만 BSD shuf (macOS 기본) 미지원. 환경 의존 발생.
- **(rejected) 무작위 시드 (시간 기반)**: reproducibility 위반.
- **(rejected) 전수 검증 (1,531 모두)**: 1 시간 내 완료 가능하지만 산출물 크기가 ≈30 배 폭증. 첫 audit 는 표본으로 신뢰 구간만 확보, 표본에서 mismatch 발견 시에만 전수 escalation.

---

## R-3 — SDK-import-only-diff 73 검증 알고리즘

**Question**: 73 후보 파일이 진짜 import-line 만 다른지 어떻게 효율적으로 검증?

**Decision**: 각 파일 쌍 (`tui/src/X` vs `restored-src/src/X`) 에 대해 `diff` 출력에서 import 관련 라인을 필터링 후 잔여 diff hunk 가 비어있는지 확인. import 라인 패턴 = `^[+-]\s*(import|from|export\s+\*\s+from|export\s*\{[^}]*\}\s+from)\b`. 잔여 diff 가 비어있으면 import-only 확정, 아니면 reclassify-to-modified.

**Rationale**:
- TypeScript `import` / `re-export` 문법 한정 패턴. SDK swap (`@anthropic-ai/...` → `@kosmos/...`) 은 import line 1-2 줄에 국한된다는 cc-source-scope-audit § 1.1 가설을 직접 검증.
- 잔여 diff 검사로 false-positive 방지 — 만약 본문에도 변경이 있으면 반드시 modified 로 분류 ([FR-008](spec.md#requirements)).
- 단순 grep 이라 reproducibility 와 환경 의존성 모두 무난.

**Alternatives considered**:
- **(rejected) AST diff (ts-morph 등)**: 정확하지만 신규 의존성 도입 (AGENTS.md 하드 룰 위반). + audit 1 회용 비용 대비 비효율.
- **(rejected) Manual review 73 개 each**: 시간 소모 + 비재현. grep 스크립트가 한 번 결정해주면 검증자가 sample 만 spot-check 하면 충분.

---

## R-4 — 212 Modified 파일 분류 휴리스틱 (Legitimate / Cleanup-needed / Suspicious)

**Question**: 212 파일을 어떻게 자동 라벨링 하나? 100% 자동은 아니지만 80% 휴리스틱 + 20% 수동 검토면 산출물 제출 가능.

**Decision**: 3 시그널 결합으로 1 차 자동 분류 후 Lead 가 2 차 수동 검토.

| 시그널 | Legitimate 단서 | Cleanup-needed 단서 | Suspicious 단서 |
|---|---|---|---|
| **(a) 디렉토리 패턴** | `i18n/`, `ipc/`, `theme/`, `observability/`, `ssh/` (KOSMOS 인프라) — KEEP 후보가 modified 로 잘못 분류된 경우 reclassify | `services/api/claude.ts`, `services/api/sonnet.ts`, `services/api/anthropic.ts` (Spec 1633 잔재) | 기타 — 추가 검토 필요 |
| **(b) Git history** | `git log --follow` 첫 커밋이 KOSMOS spec id (`feat/NNNN-...`) 매핑 가능 | `Spec 1633` 기간 (2026-04-23 ~ 2026-04-28) 내 마지막 변경 + 후속 cleanup 미완 | author/메시지에서 추적 불가 (예: 단순 `chore` / `refactor` 만) |
| **(c) Import scan** | `@kosmos/...` import / 한국어 i18n key / EXAONE 모델 ID 등 KOSMOS-only 토큰 존재 | `claude.ts` / `Anthropic` / `claude-code-style` 잔재 import | KOSMOS 도 CC 도 아닌 외부 의존 또는 dead-code 감지 |

자동 분류 알고리즘 (`scripts/classify-modified.py`):
1. (a) 디렉토리 매칭 — KOSMOS 인프라 디렉토리 매칭이면 Legitimate, Spec 1633 알려진 잔재 path 매칭이면 Cleanup-needed.
2. (b) `git log --pretty='%H %s' -- <file>` 으로 마지막 5 commit 의 spec id grep — 매핑 가능하면 Legitimate.
3. (c) 본문 grep — `@anthropic-ai/`, `claude.ts`, `verifyApiKey` 등 알려진 잔재 토큰이 있으면 Cleanup-needed; 없으면 (a)+(b) 결과 따름.
4. 위 3 개 시그널 모두 결정짓지 못하는 파일 = Suspicious.

Lead 의 2 차 수동 검토는 Suspicious + 일부 Legitimate sample (각 5–10 개) 만 대상으로 산출물 검수.

**Rationale**:
- KOSMOS 의 known cleanup 잔재 path 와 토큰 list (`docs/spec-1633-status` + `MEMORY.md § project_tui_anthropic_residue` + `project_frame_schema_dead_arms`) 가 이미 grounded-truth 제공 → 휴리스틱 base 무난.
- spec history 매핑은 KOSMOS 의 `feat/NNNN-...` branch 컨벤션 덕에 grep 으로 충분.
- 100% 자동 분류 목표는 비현실 — Suspicious 는 본질적으로 "휴리스틱이 결정 못한 파일" 이므로 산출물의 정의에 부합.

**Alternatives considered**:
- **(rejected) 모든 파일 Lead 수동 검토 212 회**: 시간 비현실 (≈1 분/파일 × 212 = 3.5h, 시그널 수집 포함하면 1 일).
- **(rejected) LLM 자동 분류**: 비결정적, reproducibility 약함, audit 산출물 신뢰성 저하.
- **(rejected) 단일 시그널 (예: git log 만)**: 디렉토리 패턴이 강력한 신호인데 무시하면 오분류 다수.

---

## R-5 — 산출물 형식 (markdown 단일 파일 vs 다중 파일)

**Question**: `cc-parity-audit.md` 가 ≈800–1,200 행 예상되는데, 단일 파일 vs 분할?

**Decision**: 단일 markdown 파일 + 분할 raw data appendix. 메인 doc `cc-parity-audit.md` 는 사람-읽기용 narrative + 분류 표. raw data (50 spot-check 결과 / 73 import diff 결과 / 212 분류 표 본문) 는 `data/*.json` 으로 별도. markdown 표 cell 에 `data/foo.json#L42` 식 deep link 를 둔다.

**Rationale**:
- 단일 파일이 사용자 검토 (사인오프) 동선 짧음.
- raw data 분리로 markdown 본문이 읽기 가능한 길이 (≈800 행) 유지.
- JSON appendix 는 도구 (`jq`) 로 후속 Epic 의 task 입력 변환에 직접 사용 가능 → SC-004 (Suspicious list standalone 추출) 충족.

**Alternatives considered**:
- **(rejected) 표 포함 모두 markdown 단일**: 212 행 표 + 50 표본 + 73 검증 = ≈1,500 행, 사람이 GitHub UI 에서 스크롤 길어짐.
- **(rejected) 디렉토리 분할 (audit/ / data/ / scripts/)**: 분류 산출물이 너무 분산되어 사인오프 검토 동선 길어짐.

---

## R-6 — Reproducibility 보증 (FR-006 / SC-005)

**Question**: 독립 reviewer 가 audit 를 재실행했을 때 "동일 sample 또는 통계적으로 동등한 결과" 가 어떤 의미인가? 어떻게 박제하나?

**Decision**: 두 단계 박제 — (1) 명령 sequence 를 `quickstart.md` + `scripts/*.sh|*.py` 로 idempotent 박제, (2) 결정적 산출물 (50 표본 list, 73 import-diff 결과) 를 plaintext appendix 로 박제. Reviewer 는 (a) 명령 재실행으로 reproducibility, 또는 (b) plaintext 표본을 spot-check 로 확인 — 둘 중 하나로 검증.

**Rationale**:
- audit 는 1 회용 산출물이라 "동일 sample 재현" 은 시드 + 모집단 결정성 만으로 충분.
- 명령 sequence + plaintext 박제 조합은 시드 유실 / 환경 차이 모두 커버.
- "통계적으로 동등" 정의 = 50/50 match 결과의 Wilson score 95% interval lower bound 가 80% 이상이면 동등 — 산출물 본문에 명시.

**Alternatives considered**:
- **(rejected) Docker 컨테이너로 환경 박제**: 과잉. audit 는 stdlib + diff/grep 만 사용.
- **(rejected) 시드 명시 없이 plaintext 만 박제**: reviewer 가 다른 시드로 재추출하면 불일치 — 동일 sample 재현 불가.

---

## Constitution Re-check (post-research)

R-1~R-6 모두 신규 의존성 0 건, source 변경 0 라인, KOSMOS-invented permission classification 도입 0 건. Constitution 전 항목 PASS 유지. Phase 1 진입 가능.
