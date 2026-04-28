# Implementation Plan: CC Parity Audit (Epic α)

**Branch**: `2292-cc-parity-audit` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/2292-cc-parity-audit/spec.md`

## Summary

Initiative #2290 의 첫 Epic. `tui/src/` 의 1,604 KEEP (1,531 byte-identical + 73 SDK-import-only-diff) 와 212 modified 파일에 대해 read-only audit 를 실행해, 후속 Epic β/γ/δ 의 task 입력이 될 분류 표를 산출한다. 코드 변경 0 건. 산출물은 `cc-parity-audit.md` 하나 + 표본/검증 raw data appendix + 재실행 가능한 procedure 스크립트.

기술적 접근: (a) `diff -rq` 로 `tui/src/` vs `.references/claude-code-sourcemap/restored-src/src/` 의 매칭 파일을 분류, (b) `sha256sum` 으로 byte-identical 무결성 spot-check (50 random sample, 시드 = `2292`), (c) `diff` 결과 line-pattern 분석으로 SDK-import-only-diff 73 검증, (d) 212 modified 파일은 `git log`/`git blame` + 디렉토리 패턴 + import scan 의 3 시그널로 `Legitimate / Cleanup-needed / Suspicious` 분류. 모든 절차는 `specs/2292-cc-parity-audit/scripts/` 하위 idempotent shell 스크립트로 박제 (산출물 외 source 변경 0 라인 invariant 유지).

## Technical Context

**Language/Version**: Bash (POSIX) + Python 3.12+ (이미 프로젝트 baseline) — audit 스크립트는 stdlib 만 사용, 신규 의존성 0
**Primary Dependencies**: 시스템 바이너리만 — `diff`, `sha256sum` (또는 `shasum -a 256`, macOS), `git`, `find`, `grep`. Python stdlib `random`, `hashlib`, `pathlib`, `json`. 신규 런타임 의존성 0 (AGENTS.md 하드 룰).
**Storage**: 산출물은 markdown + 보조 JSON appendix 만. `specs/2292-cc-parity-audit/` 디렉토리 내부에만 기록. CC restored-src 와 KOSMOS `tui/src/` 는 read-only 입력.
**Testing**: 산출물 자체에 대한 자기 검증 — (a) `Modified Files` 표 행 수 = 212 (`wc -l` 기반 assertion), (b) `SuspiciousTransferList` 추출 결과가 표의 `Suspicious` 행과 1:1, (c) reproducibility 스크립트 재실행 시 동일 표본 set 재현.
**Target Platform**: macOS / Linux dev 환경 (Bash + GNU coreutils 또는 BSD coreutils 호환). CI 의존성 없음 (audit 는 로컬 머신에서 1 회 실행).
**Project Type**: Documentation deliverable — `tui/src/` 와 `.references/claude-code-sourcemap/restored-src/src/` 두 디렉토리에 대한 read-only audit. Source code modification 없음.
**Performance Goals**: full audit (1,884 + 2,090 ≈ 4,000 파일 diff 비교) 1 시간 내 완료. spot-check 50 hash 비교는 수 초.
**Constraints**: read-only invariant (FR-007/SC-006) — `specs/2292-cc-parity-audit/` 외부 0 라인 변경. 모든 결과 reproducibility (FR-006/SC-005) — 시드 `2292` + 명령 sequence 박제.
**Scale/Scope**: 입력 모집단 = `tui/src/` 의 2,090 파일 + restored-src 의 1,884 파일. 산출 분류 = 1,531 + 73 + 212 + 274 + 68 = 2,158 라인 분류 표 (cc-source-scope-audit.md § 0). 산출 markdown 단일 파일 ≈ 800–1,200 행 예상.

## Constitution Check

*GATE: Phase 0 진입 전 통과 필수. Phase 1 종료 후 재검토.*

| Principle | 적용 여부 | 평가 |
|---|---|---|
| **I. Reference-Driven Development** | ✅ 직접 적용 | 본 Epic 의 본질이 reference (`restored-src`) 와의 parity 입증. spec.md 가 4 개 reference (AGENTS.md § CORE THESIS, cc-source-scope-audit.md § 1.1/1.2/3, delegation-flow-design.md § 12, restored-src) 를 박제. plan.md 도 같은 4 개 인용. 추가 escalation 없음. |
| **II. Fail-Closed Security** | ✅ 적용 (read-only 형태) | 본 Epic 은 어댑터 정책을 발명하지 않음. Audit 결과로 KOSMOS 가 임의 추가한 `5-mode spectrum / pipa_class / auth_level / permission_tier` 등의 잔재가 발견되면 Suspicious 로 분류해 Epic δ (#2295) 로 transfer. |
| **III. Pydantic v2 Strict Typing** | N/A | 신규 도구 어댑터 없음. 산출물은 markdown. JSON appendix 도 schema 강제 대상 아님. |
| **IV. Government API Compliance** | N/A | live API 호출 없음. 어댑터 신설 없음. 픽스처 변경 없음. |
| **V. Policy Alignment** | N/A | 시민 데이터 흐름 신규 없음. PIPA 영향 없음. |
| **VI. Deferred Work Accountability** | ✅ 적용 | spec.md `Deferred to Future Work` 표에 7 항목 — 6 개는 Epic β/γ/δ/ε/ζ/η (#2293–#2298) 로 추적, 1 개는 조건부 `NEEDS TRACKING` (`/speckit-taskstoissues` 가 해소). spec 본문에 unregistered "future epic / Phase [2+] / v2 / deferred to" 패턴 0 건 (Phase 0 grep 검증). |

**결론**: PASS. Constitution 위반 0 건. Complexity Tracking 표 비움.

## Project Structure

### Documentation (this feature)

```text
specs/2292-cc-parity-audit/
├── spec.md                  # ✅ /speckit-specify 산출물 (이미 작성됨)
├── plan.md                  # ✅ 본 파일 (/speckit-plan 산출물)
├── research.md              # ✅ Phase 0 산출물 (/speckit-plan)
├── data-model.md            # ✅ Phase 1 산출물 (/speckit-plan)
├── quickstart.md            # ✅ Phase 1 산출물 (/speckit-plan)
├── contracts/               # ❌ skip — 본 Epic 은 외부 인터페이스 없음
├── checklists/
│   └── requirements.md      # ✅ /speckit-specify 산출물
├── tasks.md                 # ⏳ /speckit-tasks 산출물 (다음 단계)
└── cc-parity-audit.md       # 🎯 /speckit-implement 최종 산출물 (Epic α deliverable)
```

추가 산출물 (implement 단계):

```text
specs/2292-cc-parity-audit/
├── scripts/
│   ├── enumerate-files.sh        # tui/src/ vs restored-src 매칭 list 산출
│   ├── spot-check-50.py          # 시드=2292 으로 byte-identical 50 표본 추출 + sha256
│   ├── verify-import-diff.sh     # 73 SDK-import-only-diff 본문 변경 여부 검증
│   └── classify-modified.py      # 212 modified 파일 분류 보조 스크립트
└── data/
    ├── enumerated-keep-1531.txt  # 표본 추출 모집단 (deterministic 정렬)
    ├── enumerated-import-73.txt  # 73 검증 대상 list
    ├── enumerated-modified-212.txt
    ├── spot-check-results.json   # 50 표본 hash diff 결과
    └── import-verify-results.json
```

### Source Code (repository root)

```text
# 본 Epic 은 source code 0 라인 변경. 입력 디렉토리는 read-only.
tui/src/                                                     # KOSMOS TUI (읽기 전용 입력)
.references/claude-code-sourcemap/restored-src/src/          # CC 2.1.88 source-of-truth (읽기 전용 입력, AGENTS.md § Do not touch)
specs/2292-cc-parity-audit/                                  # 모든 산출물의 유일한 출력 위치
```

**Structure Decision**: 본 Epic 은 "documentation + audit 스크립트" 조합으로 구성된 read-only deliverable. KOSMOS 의 web-service / library / CLI 프로젝트 카테고리 어디에도 속하지 않음. 따라서 plan-template 의 Option 1/2/3 트리는 사용하지 않고, `specs/2292-cc-parity-audit/` 단일 디렉토리만 변경. `tui/src/` 와 `restored-src/src/` 는 입력으로만 읽힘 — `find` + `diff` + `sha256sum` 으로 비교만 수행하고 absolute import-graph 를 만들지 않음.

## Complexity Tracking

> **Constitution Check 가 PASS 이므로 본 표는 비워둠.**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | (n/a) | (n/a) |
