# Feature Specification: CC Parity Audit (Epic α)

**Feature Branch**: `2292-cc-parity-audit`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "Epic α — `.references/claude-code-sourcemap/restored-src/` 와의 KOSMOS TUI parity 를 read-only audit 로 입증하고, 212 modified 파일을 후속 Epic 입력으로 분류한다."
**Authority** (cite in every downstream artefact):
- `AGENTS.md § CORE THESIS` — KOSMOS = AX-infrastructure callable-channel client (3차 thesis canonical)
- `specs/1979-plugin-dx-tui-integration/cc-source-scope-audit.md § 1.1, § 1.2, § 3 (Phase α)` — 1,531 / 73 / 212 / 274 / 68 분류표가 본 Epic 의 base scope
- `specs/1979-plugin-dx-tui-integration/delegation-flow-design.md § 12` — final canonical architecture (mock 어댑터 reference shape 의존)
- `.references/claude-code-sourcemap/restored-src/` — CC 2.1.88 byte-identical source-of-truth (research-only)

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Modified File Justification Audit (Priority: P1)

KOSMOS Lead (Opus) 와 후속 Epic 팀이 본 Epic 산출물을 입력으로 받아 Epic β (#2293, KOSMOS-original UI residue cleanup) 와 Epic δ (#2295, 백엔드 permissions 정리) 의 작업 범위를 결정해야 한다. 그러기 위해 `tui/src/` 하위 212 modified 파일 each 가 (a) KOSMOS-needed 정당한 변경인지, (b) 잔재 정리 필요 항목인지, (c) 추가 audit 가 필요한 의심 변경인지 단일 스프레드시트형 분류로 묶여 있어야 한다.

**Why this priority**: Initiative #2290 의 Epic β·δ 가 본 분류 결과 없이 진입하면 cleanup 범위가 모호해 잘못 삭제하거나 정당 변경을 회귀시킬 위험이 있다. 분류 산출물이 곧 후속 Epic 의 task 입력이다.

**Independent Test**: 사용자가 `cc-parity-audit.md § Modified Files` 표를 열었을 때 212행 모두가 `Legitimate / Cleanup-needed / Suspicious` 중 정확히 하나로 분류되어 있고, 각 행이 reference (CC source-of-truth 경로 또는 KOSMOS spec id) 를 인용하면 통과.

**Acceptance Scenarios**:

1. **Given** Epic α 산출물 `cc-parity-audit.md`, **When** 사용자가 `Modified Files` 표를 검토, **Then** 212 행 100% 가 세 분류 중 하나로 라벨링되어 있고 빈 셀이 없다.
2. **Given** 동일 산출물, **When** 사용자가 `Suspicious` 필터를 적용, **Then** 의심 파일만으로 구성된 별도 list 가 Epic β/δ task 입력으로 추출된다.
3. **Given** Suspicious 파일 1개, **When** 사용자가 행을 펼침, **Then** 변경 요약 + KOSMOS spec 인용 + "왜 의심인가" 사유 한 줄이 포함되어 있다.

---

### User Story 2 — Byte-Identical Parity Spot-Check (Priority: P2)

KOSMOS 의 핵심 invariant 는 "1,604 KEEP 파일이 진짜 CC 와 byte-identical 이다" 이다. 이 invariant 가 시간에 따라 drift 했을 가능성을 검증하기 위해, `tui/src/` 의 1,531 byte-identical 후보 파일 중 무작위 50 개 표본을 hash 비교로 검증한다. 표본 결과는 reproducibility script 와 함께 문서화되어, 향후 누구나 다른 시드로 재검증할 수 있어야 한다.

**Why this priority**: parity invariant 가 깨졌다면 Epic β·γ·δ 모두 잘못된 base 를 가정한다. 표본 추출은 빠르게 신뢰 구간을 제공한다.

**Independent Test**: spot-check 표를 열어 50 행 hash diff 컬럼이 모두 `match` 이거나, 불일치 행이 별도 escalation list 로 분리되어 있으면 통과.

**Acceptance Scenarios**:

1. **Given** 1,531 byte-identical 후보, **When** audit 실행, **Then** 50 개 무작위 표본이 추출되고 각 파일에 대해 (KOSMOS path, CC source path, hash 일치 여부) 가 기록된다.
2. **Given** 표본 결과, **When** 불일치 파일이 발견, **Then** 해당 파일은 `Modified` 카테고리로 reclassify 되어 User Story 1 분류 표에 합류한다.
3. **Given** 표본 결과, **When** 다른 사용자가 reproducibility 절차 (commands + seed) 를 따라 재실행, **Then** 동일 sample set 또는 동일 통계가 재현된다.

---

### User Story 3 — SDK-Import-Only-Diff Verification (Priority: P3)

`cc-source-scope-audit.md § 1.1` 은 73 파일이 "SDK import 1-2줄만 다르고 본문은 byte-identical" 이라고 주장한다. Epic α 는 이 73 파일 전체를 grep 으로 확인해 import 외 본문 변경이 없음을 증명한다.

**Why this priority**: 73 파일은 KOSMOS-internal SDK 경로 (`@kosmos/...` vs `@anthropic/...` 등) 만 바뀐 것으로 추정되어 Epic β·γ 작업 우선순위가 가장 낮다. 본 검증으로 73 파일을 사실상 KEEP 군에 합산할 수 있게 된다.

**Independent Test**: 73 파일 verification 표가 열려 각 행이 `import-only diff confirmed` 또는 `re-classified to Modified` 로 표기되어 있으면 통과.

**Acceptance Scenarios**:

1. **Given** 73 SDK-import-only-diff 후보, **When** audit 실행, **Then** 각 파일에 대해 (변경된 import 라인 목록, 본문 diff 존재 여부) 가 기록된다.
2. **Given** 본문 diff 가 발견된 파일, **When** 추가 검사, **Then** 해당 파일은 Modified 카테고리로 reclassify 된다.

---

### Edge Cases

- **무작위 표본이 모두 일치한다고 1,531 전수 일치를 보장하지 못한다**: 산출물은 신뢰 구간 (예: "50/50 match → 95% 신뢰도로 ≥94% parity") 을 명시하고, reproducibility script 로 추후 재검증 경로를 보장한다.
- **modified 파일 변경 사유를 git blame 으로도 못 찾는 경우**: 해당 행은 자동으로 `Suspicious` 로 분류하고 Epic β/δ 에서 추가 investigation 을 수행한다.
- **CC 원본 경로가 `restored-src` 에 존재하지 않는 KOSMOS-only 파일이 modified 카테고리에 잘못 포함된 경우**: audit 실행 중 발견되면 KOSMOS-only ADDITIONS (274) 카테고리로 reclassify 하고 본 Epic 범위에서 제외한다.
- **표본 추출 시드가 유실된 경우**: audit 산출물에 시드와 표본 list 를 plaintext 로 박제하여 향후 reproducibility 가 시드 보존에 의존하지 않도록 한다.
- **Audit 중 source file 을 실수로 수정한 경우**: pre-commit guard (existing project hooks) 가 block 한다. 산출물 외 변경은 PR 단계에서 거부된다.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Audit 산출물은 `tui/src/` 하위 212 modified 파일 100% 를 정확히 한 분류 (`Legitimate`, `Cleanup-needed`, `Suspicious`) 로 라벨링해야 한다. 빈 셀 또는 다중 라벨 금지.
- **FR-002**: Audit 산출물은 1,531 byte-identical 후보 중 무작위 50 개 이상의 표본을 추출하고, 각 표본에 대해 (KOSMOS path, CC source path, hash match 여부) 를 기록해야 한다.
- **FR-003**: Audit 산출물은 73 SDK-import-only-diff 파일 100% 를 검증하고, 각 파일이 진짜 import-only diff 인지 (또는 본문 diff 가 존재해 reclassify 되었는지) 명시해야 한다.
- **FR-004**: Modified 파일 분류 표의 각 행은 (a) CC source-of-truth 경로 또는 (b) KOSMOS spec id (예: `Spec 1633`, `Spec 287`) 중 적어도 하나의 reference 를 인용해야 한다.
- **FR-005**: Audit 산출물은 `Suspicious` 분류만으로 구성된 standalone list 섹션을 가지며, 후속 Epic β (#2293) 또는 Epic δ (#2295) 의 task 입력으로 직접 transfer 가능해야 한다.
- **FR-006**: Audit 절차 (50 표본 추출 + hash 비교 + grep 검증) 는 reproducibility 를 보장하기 위해 (a) 명시적 시드 또는 (b) 실행된 명령 sequence 와 함께 산출물에 박제되어야 한다.
- **FR-007**: Audit 실행 동안 `specs/2292-cc-parity-audit/` 외부의 어떤 source file 도 수정되지 않아야 한다 (read-only invariant).
- **FR-008**: 표본 또는 73 검증 중 본문 diff 가 발견된 파일은 자동으로 modified 분류 표로 reclassify 되어 FR-001 분류를 받아야 한다.
- **FR-009**: Audit 산출물은 종합 섹션에서 7-Phase plan (`cc-source-scope-audit.md § 3`) 기준 다음 Epic 진입 readiness 를 명시해야 한다 (예: "Epic β 진입 가능 — Suspicious 14건 transfer / Epic δ 진입 가능 — Suspicious 7건 transfer").
- **FR-010**: Audit 산출물은 base scope 표 (1,531 / 73 / 212 / 274 / 68) 의 숫자가 audit 시점에도 유효한지 재계측한 결과를 명시해야 한다 (drift 발견 시 산출물 본문에서 정정).

### Key Entities

- **AuditEntry** (modified file 1 행): `kosmos_path`, `cc_source_path`, `classification` (Legitimate / Cleanup-needed / Suspicious), `change_summary` (한 줄), `reference_citation` (CC 경로 또는 KOSMOS spec id), `notes` (선택, suspicious 사유).
- **SpotCheckSample** (byte-identical 표본 1 행): `kosmos_path`, `cc_source_path`, `hash_match` (true/false), `sampling_seed_or_method`.
- **ImportDiffEntry** (SDK import 73 검증 1 행): `kosmos_path`, `cc_source_path`, `import_lines_changed` (요약), `body_diff_present` (true/false), `reclassified_to_modified` (true/false).
- **SuspiciousTransferList**: `Suspicious` 분류 행을 별도로 추출한 list. Epic β 또는 Epic δ task 본문에 직접 paste 가능한 형태.
- **ReproducibilityProcedure**: 표본 추출 명령, hash 비교 명령, grep 검증 명령 sequence + 시드 또는 표본 plaintext.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `cc-parity-audit.md` 의 modified 파일 표가 212 행 100% 분류 완료 (빈 셀 0).
- **SC-002**: byte-identical 표본이 ≥ 50 개 추출되고, hash 일치율이 산출물에 명시적 수치 (예: "50/50 match" 또는 "48/50 match, 2 reclassified") 로 기록.
- **SC-003**: 73 SDK-import-only-diff 파일 100% 가 검증되고 본문 diff 존재 여부가 행마다 명시.
- **SC-004**: `Suspicious` 분류 list 가 standalone 섹션으로 추출 가능하며, Epic β (#2293) 와 Epic δ (#2295) 의 task 본문에 paste 했을 때 추가 가공 없이 사용 가능.
- **SC-005**: 독립 reviewer 가 산출물의 reproducibility 절차를 따라 실행했을 때 동일 표본 또는 통계적으로 동등한 결과를 얻을 수 있다.
- **SC-006**: PR diff 가 `specs/2292-cc-parity-audit/` 외부에서 0 라인 변경 (read-only invariant).
- **SC-007**: 7-Phase plan 의 Phase α exit criteria ("산출물: cc-parity-audit.md", "위험: 0") 충족 — 사용자 사인오프로 confirm.

---

## Assumptions

- `.references/claude-code-sourcemap/restored-src/` 가 CC 2.1.88 byte-identical source-of-truth 라는 프로젝트 invariant 를 본 Epic 도 그대로 신뢰한다 (`AGENTS.md § Hard rules`).
- `cc-source-scope-audit.md § 1.1, § 1.2` 의 1,531 / 73 / 212 / 274 / 68 분류 숫자가 본 Epic 시작 시점에서도 유효하다 (drift 가 발견되면 산출물 본문에서 재계측).
- 표본 추출은 50 개로 충분한 첫 신뢰 구간을 제공한다 (1,531 모집단 대비 ≈3.3% 표본). 더 강한 보증이 필요할 경우 후속 Epic 에서 표본 확장.
- modified 파일의 변경 사유 추적은 `git log` + `git blame` 과 KOSMOS spec history (`specs/`, `docs/`) 로 충분하다. 추적 불가 항목은 자동으로 Suspicious 분류.
- Audit 은 단일 스프린트 (≈1 week) 내 1 명의 Lead (Opus) 가 API Tester (Sonnet) teammate 와 병렬 실행으로 완료 가능 (Phase α 추정 1 sprint).
- 산출물은 markdown 형식이며, 표는 GitHub Flavored Markdown 으로 렌더링된다 (별도 dashboard 도구 없음).

---

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **소스 파일 수정**: Epic α 는 read-only audit. 어떤 `tui/src/`, `src/kosmos/` 파일도 수정하지 않는다. 수정은 Epic β·γ·δ·ε·ζ·η 에서 처리.
- **백엔드 Python (`src/kosmos/`) audit**: 본 Epic 은 `tui/src/` parity 만 다룬다. 백엔드 cleanup 은 Epic δ (#2295) 와 `cc-source-scope-audit.md § 2` 가 담당.
- **KOSMOS-only ADDITIONS (274 파일) audit**: 본 Epic 은 KEEP (1,604) + Modified (212) 만 다룬다. KOSMOS-only 파일 검토는 Epic β 의 6 검토 후보 (Monitor / ReviewArtifact / SuggestBackgroundPR / Tungsten / VerifyPlanExecution / Workflow) 등에 분산.
- **CC-only DELETE (68 파일) audit**: 이미 의도적으로 삭제된 항목. 재검증 없음.
- **Mock 어댑터 디자인 또는 5-primitive align**: Epic γ (#2294) 와 Epic ε (#2296) 가 담당.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Suspicious 파일 실제 수정 (Spec 1633 잔재 등) | 본 Epic 은 read-only audit; 수정은 분류 결과를 받은 후 후속 Epic 의 일 | Epic β (#2293) — KOSMOS-original UI residue cleanup | #2293 |
| 백엔드 `permissions/` 25 파일 정리 + AdapterRealDomainPolicy 모델 | TUI parity 만 본 Epic 범위 | Epic δ (#2295) — Backend permissions/ cleanup | #2295 |
| 5-primitive 를 CC `Tool.ts` 인터페이스에 정확 align | parity 입증 후 진행 | Epic γ (#2294) — 5-primitive align | #2294 |
| AX-infrastructure mock 어댑터 신설 | 본 Epic 은 audit only | Epic ε (#2296) — AX-infrastructure mock adapters | #2296 |
| End-to-end smoke + 정책 매핑 문서 | 후속 Epic 산출물 의존 | Epic ζ (#2297) — E2E smoke + policy mapping | #2297 |
| System prompt rewrite | optional, 마지막 Epic | Epic η (#2298) — System prompt rewrite | #2298 |
| 표본 50 개 → 100 개 확장 (더 강한 신뢰 구간) | 첫 표본 결과가 의심스러울 때만 필요 | TBD (조건부) | #2319 |
