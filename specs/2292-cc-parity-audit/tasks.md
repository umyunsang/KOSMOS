---
description: "Task list for Epic α — CC Parity Audit (Initiative #2290)"
---

# Tasks: CC Parity Audit (Epic α · #2292)

**Input**: Design documents from `/specs/2292-cc-parity-audit/`
**Prerequisites**: spec.md, plan.md, research.md, data-model.md, quickstart.md (모두 있음; contracts/ 는 의도적 skip per plan.md)
**Tests**: 본 Epic 은 audit 산출물 자체에 대한 self-validation 만 수행 (산출물 row 수 / hash 일치율 / read-only invariant). 별도 unit/integration test 코드는 없음 — 산출물 파일이 evidence.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Different file / no incomplete dependency
- **[Story]**: US1 (modified 분류), US2 (50 spot-check), US3 (73 import-diff)
- 모든 경로는 repo root (`/Users/um-yunsang/KOSMOS`) 기준 상대경로

## Path Conventions

- Output dir: `specs/2292-cc-parity-audit/{scripts,data}/`
- Read-only inputs: `tui/src/`, `.references/claude-code-sourcemap/restored-src/src/`
- Read-only invariant: 본 Epic 의 어떤 task 도 위 두 입력 디렉토리 + `specs/2292-cc-parity-audit/` 외부의 어떤 파일도 수정하지 않는다 (FR-007 / SC-006)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 산출물 디렉토리 + Python venv 설정 (이미 프로젝트 baseline 있으면 skip)

- [X] T001 [P] Create `specs/2292-cc-parity-audit/scripts/` and `specs/2292-cc-parity-audit/data/` directories with `.gitkeep` files
- [X] T002 [P] Add `specs/2292-cc-parity-audit/scripts/_common.sh` shared helpers (repo root resolution, KOSMOS_DIR / CC_DIR constants, `LC_ALL=C` enforcement) — sourced by all R-step shell scripts

---

## Phase 2: Foundational — R1 File Enumeration (Blocking Prerequisites)

**Purpose**: 5 카테고리 파일 list 산출. US1·US2·US3 모두 본 단계 산출 (`data/enumerated-*.txt`) 에 의존하므로 반드시 선행.

**⚠️ CRITICAL**: T003 완료 전 어떤 user story task 도 진입 불가.

- [X] T003 Implement `specs/2292-cc-parity-audit/scripts/enumerate-files.sh` — `find` + `diff -rq` + `comm` + `LC_ALL=C sort` 로 `data/enumerated-{keep-byte-identical,import-candidate,modified,kosmos-only,cc-only}.txt` 5 파일 산출 (quickstart.md § R1 + research.md § R-1 구현)
- [X] T004 Run T003 and assert produced row counts vs cc-source-scope-audit.md baseline (1,531 / 73 / 212 / 274 / 68); record actual numbers + drift delta in `specs/2292-cc-parity-audit/data/enumeration-summary.json` for FR-010 정정 input

**Checkpoint**: `data/enumerated-*.txt` 5 파일 + `enumeration-summary.json` 박제 완료. user story 병렬 진입 가능.

---

## Phase 3: User Story 1 — Modified File Justification Audit (Priority: P1) 🎯 MVP

**Goal**: 212 modified 파일 (T003 산출 기준 실 숫자) 100% 를 `Legitimate / Cleanup-needed / Suspicious` 셋 중 하나로 분류해 후속 Epic β/δ 의 task 입력으로 transfer 가능한 list 산출.

**Independent Test**: `jq 'length' data/modified-212-classification.json` == 모집단 크기 (T004 actual count) AND `jq '[.[] | .classification] | unique' data/modified-212-classification.json` == `["Cleanup-needed", "Legitimate", "Suspicious"]` 정확히. AND `jq '[.[] | select(.classification == "Suspicious" and .notes == null)] | length'` == 0.

### Implementation for User Story 1

- [X] T005 [US1] Implement `specs/2292-cc-parity-audit/scripts/classify-modified.py` — research.md § R-4 의 3 시그널 휴리스틱 (디렉토리 패턴 / git history / import scan) 자동 분류. 알려진 잔재 path + 토큰 list (`@anthropic-ai/`, `claude.ts`, `verifyApiKey`, `services/api/sonnet.ts`, `services/api/anthropic.ts`, `utils/permissions/`) 를 스크립트 상단 상수 박제
- [X] T006 [US1] Run T005 to produce `specs/2292-cc-parity-audit/data/modified-212-classification.json` (data-model.md § AuditEntry 스키마); 자동 분류 결과 + 시그널 raw (`signals` 필드) 박제
- [X] T007 [US1] Lead 수동 검토 — `Suspicious` 행 100% + `Legitimate / Cleanup-needed` 표본 5–10% 를 검수해 `notes` 필드 채우고 오분류 정정. 추가로 US2 / US3 의 staging 파일 (`spot-check-reclassify-pending.json` / `import-verify-reclassify-pending.json`) 이 존재하면 entry 를 `modified-212-classification.json` 으로 합류 후 동일 검수 절차 적용. 결과를 `modified-212-classification.json` 에 in-place 갱신
- [X] T008 [US1] Generate `specs/2292-cc-parity-audit/data/suspicious-transfer.json` — Suspicious 부분집합을 data-model.md § SuspiciousTransferList 라우팅 룰 (services/api/* → Epic β #2293, src/kosmos/permissions/* → out-of-scope, 그 외 → uncategorized) 로 분류
- [X] T009 [US1] Compose `specs/2292-cc-parity-audit/cc-parity-audit.md § Modified Files` 섹션 — JSON → markdown 표 변환, deep-link 셀에 `data/modified-212-classification.json#L<row>` 박제

**Checkpoint**: US1 단독으로 산출물 검증 가능 — Modified Files 표 + Suspicious Transfer List 두 섹션이 자기-완결.

---

## Phase 4: User Story 2 — Byte-Identical Parity Spot-Check (Priority: P2)

**Goal**: byte-identical 모집단 (T003 산출, ≈1,531) 에서 시드 `2292` 로 50 random sample 추출 + sha256 비교 → 산출물 표 + plaintext 박제.

**Independent Test**: `jq 'length' data/spot-check-results.json` == 50 AND 모든 행의 `sampling_seed` == 2292 AND markdown 표가 50 행을 plaintext 로 self-contained 박제 (시드 유실 방어).

### Implementation for User Story 2

- [X] T010 [P] [US2] Implement `specs/2292-cc-parity-audit/scripts/spot-check-50.py` — `random.Random(2292).sample(population, 50)` 으로 `data/enumerated-keep-byte-identical.txt` 에서 추출 후 각 파일의 `sha256` 양쪽 비교 (data-model.md § SpotCheckSample 스키마)
- [X] T011 [US2] Run T010 to produce `specs/2292-cc-parity-audit/data/spot-check-results.json` (50 entry) ; `hash_match == false` 행 발견시 staging 파일 `specs/2292-cc-parity-audit/data/spot-check-reclassify-pending.json` 에 reclassify entry 박제 (T007 Lead 검토 단계에서 `modified-212-classification.json` 으로 합류)
- [X] T012 [US2] Compose `specs/2292-cc-parity-audit/cc-parity-audit.md § Spot-Check (50)` 섹션 — JSON → markdown 표 + Wilson score 95% lower bound 신뢰 구간 본문 명시 (research.md § R-2 의 50/50 match → ≥92.9% parity 표현)

**Checkpoint**: US2 단독으로 산출물 검증 가능 — Spot-Check (50) 섹션이 시드 + 표본 + hash 결과 self-contained.

---

## Phase 5: User Story 3 — SDK-Import-Only-Diff Verification (Priority: P3)

**Goal**: 73 후보 파일 (T003 산출) each 가 진짜 import-line 만 다른지 grep 으로 검증 → 본문 diff 발견시 modified 로 reclassify.

**Independent Test**: `jq 'length' data/import-verify-results.json` == 73 AND markdown 표 73 행 each 가 `import-only diff confirmed` 또는 `re-classified to Modified` 명시.

### Implementation for User Story 3

- [X] T013 [P] [US3] Implement `specs/2292-cc-parity-audit/scripts/verify-import-diff.sh` — research.md § R-3 의 import-line regex (`^[+-]\s*(import|from|export\s+\*\s+from|export\s*\{[^}]*\}\s+from)\b`) 필터 후 잔여 diff 가 비어있는지 검증
- [X] T014 [US3] Run T013 to produce `specs/2292-cc-parity-audit/data/import-verify-results.json` (73 entry, data-model.md § ImportDiffEntry 스키마) ; `body_diff_present == true` 행은 자동으로 `reclassified_to_modified = true` 설정 + staging 파일 `specs/2292-cc-parity-audit/data/import-verify-reclassify-pending.json` 에 reclassify entry 박제 (T007 Lead 검토 단계에서 `modified-212-classification.json` 으로 합류)
- [X] T015 [US3] Compose `specs/2292-cc-parity-audit/cc-parity-audit.md § Import-only Diff (73)` 섹션 — JSON → markdown 표

**Checkpoint**: US3 단독으로 산출물 검증 가능 — Import-only Diff 섹션이 self-contained.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 단편 산출물 (US1–US3) 을 final deliverable `cc-parity-audit.md` 단일 markdown 으로 조립 + read-only invariant 자기 검증 + Phase α exit criteria 충족.

- [X] T016 [P] Implement `specs/2292-cc-parity-audit/scripts/compose-audit-md.py` — US1·US2·US3 산출 markdown 섹션 + plan.md / research.md 발췌 narrative 헤더 + Suspicious Transfer List + Drift Notes (T004 결과 기반) 를 `cc-parity-audit.md` 단일 파일로 조립
- [X] T017 Run T016 to produce final `specs/2292-cc-parity-audit/cc-parity-audit.md` ; assert `grep -c '^| ' cc-parity-audit.md` 합산이 (실 modified count + 50 + 73 + Suspicious Transfer 행 수) 와 일치
- [X] T018 Generate `specs/2292-cc-parity-audit/data/repro-manifest.json` — quickstart.md § ReproducibilityProcedure 의 4 step (R1.enumerate / R2.spot-check / R3.import-verify / R4.classify) 정형화 (data-model.md § ReproducibilityProcedure 스키마)
- [X] T019 Self-validate read-only invariant — `git status --short -- ':!specs/2292-cc-parity-audit'` 출력이 비어있는지 확인 (FR-007 / SC-006). 비어있지 않으면 외부 변경 revert 후 원인 조사 + audit 재실행
- [X] T020 Update Phase α exit criteria status — `cc-parity-audit.md` 의 종합 섹션에 7-Phase plan 기준 다음 Epic 진입 readiness 명시 (FR-009): "Epic β #2293 진입 가능 — Suspicious N건 transfer / Epic δ #2295 N건 / uncategorized N건"

**Checkpoint**: `cc-parity-audit.md` 가 사용자 사인오프 가능 상태 — 212 modified 분류 + 50 spot-check + 73 import-diff + Suspicious Transfer + Drift Notes + 다음 Epic readiness 모두 self-contained.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 의존성 없음 — 즉시 시작 가능 (T001 / T002 병렬)
- **Foundational (Phase 2 — R1)**: Setup 완료 후 시작; T003 → T004 순차
- **User Stories (Phase 3–5)**: T004 완료 후 진입; **US1 / US2 / US3 병렬 가능** (서로 다른 산출 JSON, 입력 list 만 공유)
- **Polish (Phase 6)**: US1·US2·US3 완료 후 시작 (T016 → T017 → T018 → T019 → T020 순차)

### User Story Dependencies

- **US1 (P1)**: T004 완료 후 시작 가능. US2/US3 와 독립.
- **US2 (P2)**: T004 완료 후 시작 가능. US1 와 독립. 단, T011 의 reclassify 후처리는 T006 산출 JSON 을 in-place 갱신 → US1 의 T006 보다 늦게 실행되어야 함 (또는 T011 의 reclassify 결과를 별도 staging file 로 분리해 T007 직전에 합류). 본 Epic 에서는 후자 채택 — `data/spot-check-reclassify-pending.json` 으로 staging.
- **US3 (P3)**: T004 완료 후 시작 가능. US1/US2 와 독립. T014 의 reclassify 후처리도 동일 staging 패턴.

### Within Each User Story

- 스크립트 작성 → 실행 → markdown 섹션 조립 순.
- US1 만 Lead 수동 검토 단계 (T007) 포함 — 자동 분류만으로는 Suspicious 사유 (`notes`) 가 채워지지 않으므로 필수.

### Parallel Opportunities

- T001, T002 병렬 (다른 파일).
- T010, T013, T016 병렬 (다른 스크립트 파일; T010 / T013 은 T004 가 끝나면 즉시, T016 은 US1–US3 완료 후).
- US1 (T005–T009) / US2 (T010–T012) / US3 (T013–T015) 세 user story 자체가 독립 — 3 명의 teammate (혹은 Sonnet 병렬) 가 동시 진입 가능.

---

## Parallel Example: User Stories 1 / 2 / 3 동시 진입 (T004 직후)

```bash
# Foundation 완료 후 세 user story 동시 시작:
Task: "Implement classify-modified.py + run + compose markdown" → US1 (T005–T009)
Task: "Implement spot-check-50.py + run + compose markdown"      → US2 (T010–T012)
Task: "Implement verify-import-diff.sh + run + compose markdown" → US3 (T013–T015)
```

세 산출 JSON 이 모두 모이면 Phase 6 (T016 onwards) 진입.

---

## Implementation Strategy

### MVP First (User Story 1 단독)

1. Phase 1 Setup → Phase 2 Foundational (T001–T004) 완료
2. Phase 3 US1 (T005–T009) 만 실행 — 212 modified 분류 + Suspicious Transfer List 산출
3. **STOP and VALIDATE**: `cc-parity-audit.md § Modified Files` 단독으로 Epic β #2293 의 task 입력으로 사용 가능한지 확인
4. Demo / 사용자 사인오프 (MVP 단계)

US2 / US3 는 P1 산출물 사인오프 후 incremental delivery.

### Incremental Delivery

1. Setup + Foundational → 5 카테고리 list 박제
2. US1 → Modified Files 분류 (MVP 사인오프)
3. US2 → Spot-Check 50 → parity invariant 보강
4. US3 → Import-only Diff 73 → 73 파일을 사실상 KEEP 군에 합산
5. Polish → final markdown + read-only invariant + Phase α exit

### Parallel Team Strategy

- Lead (Opus) → 본 Epic plan/review/Lead 수동 검토 (T007), Polish (T016–T020)
- Teammate (Sonnet, API Tester role) → Phase 2 (T003–T004) + 세 user story 자동화 스크립트 (T005, T010, T013) 병렬 작성

---

## Notes

- 총 task 수 = **20** (≪ 90 cap, GitHub Sub-Issues API v2 제한 준수)
- 본 Epic 은 source code 0 라인 변경 — 모든 task 산출물은 `specs/2292-cc-parity-audit/` 내부
- T007 Lead 수동 검토는 자동 분류 신뢰성 보강 단계 — 자동 분류만으로 Suspicious `notes` 가 채워지지 않아 spec.md Story 1.3 의 acceptance scenario 충족 불가
- 시드 = `2292` (Epic 번호) 는 quickstart.md / data-model.md / 본 tasks.md 모두 동일 — reproducibility 보증
- 분류/검증 스크립트는 모두 `specs/2292-cc-parity-audit/scripts/_common.sh` 헬퍼 sourced — DRY 유지
- audit 1 회 실행 총 runtime ≈5 분 (quickstart.md § 6 추정)
- US1 의 reclassify staging (T011 / T014 → T007) 은 in-place 충돌 회피 패턴 — 세 user story 의 병렬 안전 보장
