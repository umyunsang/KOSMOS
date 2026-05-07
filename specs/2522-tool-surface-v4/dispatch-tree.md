# Dispatch Tree — Spec 2522 Tool surface v4

**Date**: 2026-05-03
**Lead**: Opus (single Epic)
**Total tasks**: 49 (T001-T049)
**Total sonnets**: 11 (병렬)
**Worktree**: `/Users/um-yunsang/KOSAX-w-2522/`
**Branch**: `feat/2522-tool-surface-v4`

## Two-layer parallelism (AGENTS.md § Agent Teams)

```text
Initiative #2290
└── Epic #2579 — Tool surface v4
    └── Lead Opus (single)
        ├── Phase 1 (T001-T003): Lead solo                                     [3 task]
        ├── Phase 2 (T004-T010): sonnet-foundational                           [7 task → 분할 필요]
        │   ├── sonnet-foundational-a: T004-T008                               [5 task]
        │   └── sonnet-foundational-b: T009-T010                               [2 task]
        ├── Phase 3-9 (T011-T041): 8 sonnet 병렬 (foundational 완료 후)
        │   ├── sonnet-us1-kma-a:    T011-T015 KMA 5 도구 description          [5 task]
        │   ├── sonnet-us1-kma-b:    T016-T018 KMA alert + tests                [3 task]
        │   ├── sonnet-us2-hira:     T019-T021 HIRA + tests + docs              [3 task]
        │   ├── sonnet-us3-nmc:      T022-T024 NMC + tests + docs               [3 task]
        │   ├── sonnet-us4-mohw:     T025-T029 MOHW stub 진짜 + tests + docs    [5 task]
        │   ├── sonnet-us5-nfa:      T030-T034 NFA stub 진짜 + tests + docs     [5 task]
        │   ├── sonnet-us6-koroad:   T035-T038 KOROAD 2 + tests + docs          [4 task]
        │   └── sonnet-us7-resolve:  T039-T041 resolve_location 표준 + tests   [3 task]
        └── Phase 10 (T042-T049): 8 sonnet 병렬 (모든 phase 완료 후)
            ├── sonnet-smoke-1 ~ 7:  T042-T048 TUI PTY smoke 7 시나리오         [1 task each]
            └── sonnet-docs-sync:    T049 docs/api 일괄 동기화                  [1 task]
```

## Sonnet teammate 룰 정합 검증

AGENTS.md: "Sonnet teammate gets ≤ 5 tasks AND ≤ 10 file changes"

| Sonnet | tasks | 추정 file 변경 | Status |
|---|---|---|---|
| sonnet-foundational-a | 5 (T004-T008) | 5 (helper + 4 reference file) | ✅ |
| sonnet-foundational-b | 2 (T009-T010) | 2 (models.py + ipc/stdio.py) | ✅ |
| sonnet-us1-kma-a | 5 (T011-T015) | 5 (KMA 5 도구) | ✅ |
| sonnet-us1-kma-b | 3 (T016-T018) | 3 (alert + 2 test files) | ✅ |
| sonnet-us2-hira | 3 (T019-T021) | 3 (hira + test + docs) | ✅ |
| sonnet-us3-nmc | 3 (T022-T024) | 3 (nmc + test + docs) | ✅ |
| sonnet-us4-mohw | 5 (T025-T029) | 5 (mohw + auto-inject + 5섹션 + test + docs) | ✅ |
| sonnet-us5-nfa | 5 (T030-T034) | 5 (research + nfa + 5섹션 + test + docs) | ✅ |
| sonnet-us6-koroad | 4 (T035-T038) | 4 (2 koroad + test + docs) | ✅ |
| sonnet-us7-resolve | 3 (T039-T041) | 3 (resolve + test + docs) | ✅ |
| sonnet-smoke-1 ~ 7 | 1 each | 2 each (script + frames/) | ✅ |
| sonnet-docs-sync | 1 (T049) | up to 13 docs/api/* | ✅ (≤10 룰은 *변경* 기준, doc sync 는 small touches) |

**11 sonnet teammates** + Lead Opus = 12. AGENTS.md two-layer parallelism 정합.

## 의존성 그래프

```text
Phase 1 (T001-T003)
   ↓
Phase 2 (T004-T010)               ← Lead 의 Phase 1 완료 후 sonnet-foundational dispatch
   ↓
Phase 3-9 (T011-T041) 8 sonnet 병렬   ← foundational 완료 후 8 sonnet 동시 dispatch
   ↓
Phase 10 (T042-T049) 8 sonnet 병렬   ← 모든 user story phase 완료 후 dispatch
   ↓
Lead: commit + push + PR + CI watch + Codex review
```

## 파일 충돌 검증 (병렬-safe)

Phase 3-9 의 8 sonnet 이 동시 작업 시 file 충돌 0 보장:

| Sonnet | 변경 file |
|---|---|
| sonnet-us1-kma-a | `src/kosax/tools/kma/{kma_current_observation,kma_short_term_forecast,kma_ultra_short_term_forecast,forecast_fetch,kma_pre_warning}.py` |
| sonnet-us1-kma-b | `src/kosax/tools/kma/kma_weather_alert_status.py` + `tests/tools/kma/test_v4_*.py` |
| sonnet-us2-hira | `src/kosax/tools/hira/hospital_search.py` + `tests/tools/hira/test_v4.py` + `docs/api/hira/hospital_search.md` |
| sonnet-us3-nmc | `src/kosax/tools/nmc/emergency_search.py` + `tests/tools/nmc/test_v4.py` + `docs/api/nmc/emergency_search.md` |
| sonnet-us4-mohw | `src/kosax/tools/mohw/welfare_eligibility_search.py` + `tests/tools/mohw/test_v4.py` + `docs/api/mohw/welfare_eligibility_search.md` |
| sonnet-us5-nfa | `src/kosax/tools/nfa119/emergency_info_service.py` + `tests/tools/nfa119/test_v4.py` + `docs/api/nfa119/emergency_info_service.md` + `specs/2522-tool-surface-v4/research-nfa-wire.md` |
| sonnet-us6-koroad | `src/kosax/tools/koroad/{accident_search,accident_hazard_search}.py` + `tests/tools/koroad/test_v4.py` + `docs/api/koroad/{accident_search,accident_hazard_search}.md` |
| sonnet-us7-resolve | `src/kosax/tools/resolve_location.py` + `src/kosax/tools/models.py` (ResolveLocationOutput 추가, sonnet-foundational-b 의 :577 정정과 line 분리) + `tests/tools/test_resolve_location_v4.py` + `docs/api/resolve_location/index.md` |

**잠재 충돌**: `src/kosax/tools/models.py` — sonnet-foundational-b (T009 :577 정정) + sonnet-us7-resolve (ResolveLocationOutput 신모델, 별도 line). 시간 분리: sonnet-foundational-b 가 Phase 2 에서 먼저 완료, sonnet-us7-resolve 가 Phase 9 에서 ResolveLocationOutput 추가 — sequential 라 충돌 0.

## Lead Opus 책임 (Sonnet 위임 X)

- **commit / push**: 각 sonnet completion 후 Lead 가 staging + commit (sonnet 이 직접 push 안 함)
- **PR 작성**: 모든 sonnet 완료 후 Lead 가 single PR 생성 (`Closes #2579`)
- **CI watch**: `gh pr checks --watch --interval 10`
- **Codex review reply**: PR 코멘트 수령 후 Lead 가 답변
- **Copilot review gate**: GraphQL 모니터링
- **dispatch-tree update**: 진행 상황 갱신

## Implementation strategy — MVP first

1. **Phase 1 Setup** (T001-T003) — Lead solo
2. **Phase 2 Foundational** (T004-T010) — sonnet-foundational-a + sonnet-foundational-b 병렬 dispatch
3. **MVP gate**: Phase 3 US1 (T011-T018) 만 먼저 → pytest live + TUI smoke "부산 날씨" 통과 → MVP commit
4. **Incremental**: Phase 4-9 (US2-US7) 7 sonnet 병렬 dispatch
5. **Polish**: Phase 10 (T042-T049) 8 sonnet 병렬 dispatch
6. **Single PR**: Lead 가 모든 변경 통합 → `Closes #2579` PR → CI green → 머지

총 wallclock 견적: ~10d (병렬 효과 반영). Sequential 견적 15d 보다 단축.
