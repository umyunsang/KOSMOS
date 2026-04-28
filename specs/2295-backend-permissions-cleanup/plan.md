# Implementation Plan: Backend Permissions Cleanup + AdapterRealDomainPolicy (Epic δ)

**Branch**: `2295-backend-permissions-cleanup` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/2295-backend-permissions-cleanup/spec.md`

## Summary

Initiative #2290 의 네 번째 Epic (β/γ 와 병렬 가능). `src/kosmos/permissions/` 의 ~20 KOSMOS-invented Spec 033 잔재 파일을 모두 제거하고, Spec 035 영수증 ledger 7 파일은 보존. 동시에 `AdapterRealDomainPolicy` 라는 단일 표준 Pydantic v2 모델을 신설해 18 어댑터의 metadata 를 KOSMOS-invented 권한 분류에서 "기관 published 정책 URL 의 cite" 형태로 옮긴다.

기술 접근:
- (a) `src/kosmos/permissions/` 의 잔재 파일 ~20 개 importer 추적 (`grep -r "from kosmos.permissions" src/ tests/`) → importer cleanup 후 잔재 파일 삭제 (memory `feedback_no_stubs_remove_or_migrate`)
- (b) Spec 035 receipt set 7 파일 (`ledger / action_digest / hmac_key / canonical_json / audit_coupling / ledger_verify / otel_emit / otel_integration`) 은 보존하되 docstring 으로 use case + Spec 035 인용
- (c) `src/kosmos/tools/models.py` 에 `AdapterRealDomainPolicy` Pydantic v2 모델 추가 — `frozen=True`, `extra="forbid"`, 4 필드 type-annotated, 모든 str 필드 non-empty validator
- (d) 18 어댑터 (KOROAD ×2 + KMA ×6 + HIRA + NMC + NFA119 + MOHW + 6 mocks) 의 metadata 에서 금지 필드 (`auth_level / pipa_class / is_personal_data / dpa_reference / is_irreversible / requires_auth`) 제거 + `policy: AdapterRealDomainPolicy` 인스턴스 추가
- (e) 각 어댑터의 `policy.real_classification_url` 에 기관 published 정책 URL — 검증 가능한 것은 실 URL, 불확실한 것은 placeholder + `# TODO: verify URL` 마커 + spec.md Deferred Items 추적
- (f) `__init__.py` 가 Spec 035 receipt 모듈만 export 하도록 정정 (잔재 모듈 export 줄 제거)
- (g) `pytest` baseline 비교 → NEW failure 0 검증
- (h) Constitution II 금지 토큰 grep gate 0-residue 검증

모든 작업은 `/Users/um-yunsang/KOSMOS-w-2295/` worktree 에서 수행. main / Epic β worktree 와 file conflict 없음 — 본 Epic 은 Python `src/kosmos/` 만 다룸.

## Technical Context

**Language/Version**: Python 3.12+ (existing project baseline; 본 Epic 은 version bump 없음).
**Primary Dependencies**: 기존 — `pydantic >= 2.13` (frozen models + Literal + ConfigDict, 이미 사용), `pydantic-settings >= 2.0` (env catalog), `httpx >= 0.27` (async HTTP, 어댑터 base), `opentelemetry-sdk` + `opentelemetry-semantic-conventions` (Spec 021 spans), `pytest` + `pytest-asyncio` (test stack). **신규 runtime dependency 0** (AGENTS.md hard rule + spec FR-008 invariant).
**Storage**: 본 Epic 은 in-memory + filesystem-only — Spec 035 receipt ledger (`~/.kosmos/memdir/user/consent/`) 등 기존 storage 구조 변경 없음.
**Testing**: `uv run pytest` (existing). 본 Epic 은 (i) `AdapterRealDomainPolicy` 의 schema validation 단위 테스트 1~2 개 추가, (ii) 18 어댑터 metadata import smoke test (registry boot) 추가, (iii) 잔재 파일을 import 하던 dead test 는 함께 삭제. NEW failure 0 의 baseline 비교 게이트 적용.
**Target Platform**: Linux container (CI), macOS / Linux dev. Python 3.12+ runtime.
**Project Type**: Backend Python cleanup + 신규 모델 1 + 18 metadata 마이그레이션. 신규 모듈 0 (모든 신규 코드는 `src/kosmos/tools/models.py` 의 기존 파일에 추가).
**Performance Goals**: 본 Epic 은 정리 + 모델 추가라 별도 perf goal 없음. `uv run pytest` < 5 min (기존 baseline). `ToolRegistry` boot 시 18 어댑터 metadata 검증 < 1 s.
**Constraints**: read-only 입력 디렉토리 = `.references/claude-code-sourcemap/restored-src/src/`. Constitution II 금지 토큰 잔존 0. 신규 dependency 0.
**Scale/Scope**: ~20 잔재 파일 deletion + 8 receipt 파일 보존 + 1 모델 신설 + 18 어댑터 metadata 마이그레이션 = 약 47 file 변경 대상. 예상 commit 수 5~8. 예상 라인 변경: -1,500 ~ -2,500 (대부분 잔재 deletion) / +200 ~ +400 (모델 + 18 metadata 추가).

## Constitution Check

*GATE: Phase 0 진입 전 통과 필수. Phase 1 종료 후 재검토.*

| Principle | 적용 여부 | 평가 |
|---|---|---|
| **I. Reference-Driven Development** | ✅ 직접 적용 | cleanup target + 모델 신설 패턴은 Spec 1979 cc-source-scope-audit § 2.3.1, § 2.3.2 + delegation-flow-design § 12 + domain-harness-design § 3.2 에서 도출. spec.md 가 5+ reference 박제. |
| **II. Fail-Closed Security (NON-NEGOTIABLE)** | ✅ 직접 강제 | 본 Epic 의 핵심 동인. Constitution II 금지 토큰 (`pipa_class / auth_level / permission_tier / is_personal_data / is_irreversible / requires_auth / dpa_reference`) 잔재 0 회 잔존을 grep gate 로 코드 레벨 enforce. 신규 모델 `AdapterRealDomainPolicy` 가 Constitution II 의 "기관 정책 cite only" 원칙을 codify. |
| **III. Pydantic v2 Strict Typing (NON-NEGOTIABLE)** | ✅ 직접 강제 | 신규 `AdapterRealDomainPolicy` 모델이 Pydantic v2 frozen + extra="forbid" 패턴 적용. 모든 필드 type-annotated, `Any` 0 회. 18 어댑터 마이그레이션도 Pydantic v2 인스턴스. |
| **IV. Government API Compliance** | ✅ 간접 (인용) | 본 Epic 은 어댑터 metadata 마이그레이션의 골격 — 실 정책 URL 검증은 Deferred Items 로 추적. 신규 어댑터 추가 0, live API 호출 0. |
| **V. Policy Alignment** | ✅ 간접 (cite) | `AdapterRealDomainPolicy` 가 Korea AI Action Plan Principle 8 (cross-ministry citizen services) + 9 (Open API + OpenMCP) 의 "기관이 정책 published 하면 KOSMOS 가 cite" 흐름을 codify. PIPA 영향 없음 (citizen data flow 변경 0). |
| **VI. Deferred Work Accountability** | ✅ 적용 | spec.md `Deferred to Future Work` 표 3 항목 — 1 개는 NEEDS TRACKING (조건부 — placeholder 0 이면 자연 close), 2 개는 #2296 / #2297 매핑. 본문 grep 결과 unregistered "future epic / Phase [2+] / v2 / deferred to" 패턴 0 건. |

**결론**: PASS. Constitution 위반 0 건. Complexity Tracking 표 비움.

## Project Structure

### Documentation (this feature)

```text
specs/2295-backend-permissions-cleanup/
├── spec.md                       # ✅ /speckit-specify 산출물
├── plan.md                       # ✅ 본 파일
├── research.md                   # ✅ Phase 0 산출물
├── data-model.md                 # ✅ Phase 1 산출물 — AdapterRealDomainPolicy 스키마 정형화
├── quickstart.md                 # ✅ Phase 1 산출물 — 잔재 deletion + 18 마이그레이션 절차
├── checklists/
│   └── requirements.md           # ✅ /speckit-specify 산출물
├── tasks.md                      # ⏳ /speckit-tasks 산출물
├── adapter-migration-log.md      # 🎯 implement 단계 — 18 어댑터 마이그레이션 진척표
├── baseline-pytest.txt           # 🎯 implement 직전 pytest 결과
└── after-pytest.txt              # 🎯 implement 후 pytest 결과
```

### Source Code (repository root)

```text
# 본 Epic 은 src/kosmos/ 하위 변경 — TUI 변경 0.
src/kosmos/
├── permissions/                       ← DELETE ~20 잔재 + KEEP 7 receipt + UPDATE __init__.py
│   ├── aal_backstop.py                ← DELETE (Spec 033 잔재)
│   ├── adapter_metadata.py            ← DELETE (Spec 033 잔재 — 새 모델로 대체)
│   ├── bypass.py                      ← DELETE
│   ├── cli.py                         ← DELETE
│   ├── credentials.py                 ← DELETE
│   ├── killswitch.py                  ← DELETE
│   ├── mode_bypass.py                 ← DELETE
│   ├── mode_default.py                ← DELETE
│   ├── models.py                      ← DELETE (KOSMOS-invented enums)
│   ├── modes.py                       ← DELETE
│   ├── pipeline.py                    ← DELETE
│   ├── pipeline_v2.py                 ← DELETE
│   ├── prompt.py                      ← DELETE
│   ├── rules.py                       ← DELETE
│   ├── session_boot.py                ← DELETE
│   ├── synthesis_guard.py             ← DELETE
│   ├── steps/                         ← DELETE 디렉토리 전체
│   ├── ledger.py                      ← KEEP (Spec 035)
│   ├── action_digest.py               ← KEEP
│   ├── hmac_key.py                    ← KEEP
│   ├── canonical_json.py              ← KEEP
│   ├── audit_coupling.py              ← KEEP
│   ├── ledger_verify.py               ← KEEP
│   ├── otel_emit.py                   ← KEEP
│   ├── otel_integration.py            ← KEEP
│   └── __init__.py                    ← UPDATE: Spec 035 receipt 모듈만 export
├── tools/
│   ├── models.py                      ← UPDATE: AdapterRealDomainPolicy 추가
│   ├── koroad/*.py                    ← UPDATE: 2 어댑터 metadata 마이그레이션
│   ├── kma/*.py                       ← UPDATE: 6 어댑터 metadata 마이그레이션
│   ├── hira/*.py                      ← UPDATE: 1 어댑터
│   ├── nmc/*.py                       ← UPDATE: 1 어댑터
│   ├── nfa119/*.py                    ← UPDATE: 1 어댑터
│   ├── mock/barocert/                 ← UPDATE: 1 mock 어댑터
│   ├── mock/cbs/                      ← UPDATE
│   ├── mock/data_go_kr/               ← UPDATE
│   ├── mock/mydata/                   ← UPDATE
│   ├── mock/npki_crypto/              ← UPDATE
│   └── mock/omnione/                  ← UPDATE
└── tools/registry.py                  ← UPDATE if needed (Spec 1979 정리 영향)

tests/                                  # 잔재 import 하던 test 삭제 + 모델 schema test 추가
.references/claude-code-sourcemap/restored-src/  # 읽기 전용
specs/2295-backend-permissions-cleanup/  # 산출물 디렉토리
```

**Structure Decision**: 본 Epic 은 "잔재 파일 deletion + 단일 모델 추가 + 18 metadata 마이그레이션" 패턴. 신규 디렉토리 0, 신규 모듈 0 (모델은 기존 `tools/models.py` 에 추가). plan-template 의 Option 1 (Single project) 에 가까움 — `src/kosmos/permissions/` 는 receipt-only 디렉토리로 축소되고, `src/kosmos/tools/models.py` 가 어댑터 정책 표현의 단일 진실원이 됨.

## Complexity Tracking

> **Constitution Check 가 PASS 이므로 본 표는 비워둠.**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | (n/a) | (n/a) |
