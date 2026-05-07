# research-stdio-ordering.md

**Spec**: 2522-tool-surface-v4
**Task**: T010 — ORDERING 지시 정합 검증 (코드 변경 X, future task note)
**Date**: 2026-05-02

---

## 1. 현재 ORDERING 지시 발화 조건

파일: `src/ummaya/ipc/stdio.py:846` (`_build_available_adapters_suffix`)

```python
needs_kma_grid = "nx" in required and "ny" in required
if needs_kma_grid:
    lines.append(
        "  [ORDERING] nx/ny 는 KMA 격자 좌표 — 이 도구 호출 전에 반드시"
        " resolve_location(query='<지역명>') 을 먼저 호출해 nx/ny 를 받아야 합니다."
    )
```

**발화 조건**: 해당 어댑터의 `input_schema_json.required` 에 `"nx"` 와 `"ny"` 가 둘 다
포함된 경우에만 emit.

**현재 발화 대상 도구** (T010 시점 registry 기준):

| tool_id | nx 필수 | ny 필수 | ORDERING emit |
|---|---|---|---|
| `kma_current_observation` | YES | YES | YES |
| `kma_short_term_forecast` | YES | YES | YES |
| `kma_ultra_short_term_forecast` | YES | YES | YES |
| `kma_pre_warning` | NO | NO | NO |
| `kma_weather_alert_status` | NO | NO | NO |
| `kma_forecast_fetch` | NO (lat/lon) | NO | NO |
| `koroad_accident_hazard_search` | NO | NO | NO |
| `nfa119_*` | NO | NO | NO |

즉 현재는 KMA nx/ny 도구 3종에만 ORDERING 지시가 emit 된다.

---

## 2. ORDERING 지시와 5-섹션 골격의 관계

Phase 3+ 에서 description 5-섹션 골격이 적용되면:

- **섹션 4 (Domain quirk)**: KMA nx/ny 도구에 대해 "nx/ny 는 KMA 격자 좌표"
  사실을 명시.
- **섹션 5 (Self-contained declaration)**: "이 도구는 self-contained —
  chain 을 강제하지 않음. 필요 시 LLM 이 자율 결정."

5-섹션 description 이 도구에 적용된 후에는 `_build_available_adapters_suffix`
의 ORDERING 블록은 **중복** 이 된다. description 의 llm_description 필드가 suffix
에 이미 emit 되기 때문 (line 827-833, `c.llm_description` 블록).

---

## 3. 권장 후속 작업 — Phase 10 Polish (deferred)

**타이밍**: 모든 도구의 description 5-섹션 골격 적용이 완료된 후
(Phase 3 US1-KMA + Phase 4-9 나머지 도구 완료 시점).

**권장 방식 A — 전체 제거** (가장 단순):

```python
# stdio.py:843-851 — Phase 10 polish 때 제거 대상
# needs_kma_grid = "nx" in required and "ny" in required
# if needs_kma_grid:
#     lines.append("  [ORDERING] ...")
```

Phase 3 US1 T018 unit test 에서 이미 "ORDERING 지시 부재" 검증이
추가될 예정 (`test_v4_unit.py:T018`). 5-섹션 description 이 적용된 도구는
해당 unit test 가 ORDERING emit 을 금지 조건으로 assert 한다.

**권장 방식 B — Conditional skip** (점진적 migration 중 안전):

```python
# description 에 "self-contained" 키워드가 있으면 ORDERING emit skip
needs_kma_grid = "nx" in required and "ny" in required
already_self_contained = "self-contained" in (c.llm_description or "").lower()
if needs_kma_grid and not already_self_contained:
    lines.append(
        "  [ORDERING] nx/ny 는 KMA 격자 좌표 — 이 도구 호출 전에 반드시"
        " resolve_location(query='<지역명>') 을 먼저 호출해 nx/ny 를 받아야 합니다."
    )
```

Phase 3-9 migration 중간에 도구별로 5-섹션 적용 시점이 다르므로,
migration 완료 전 과도기에는 방식 B 가 더 안전하다.

---

## 4. 결론 (T010)

- **현재 코드 변경 X**: ORDERING 블록은 현 시점에서 3 KMA 도구의 유일한
  ordering signal 이므로 유지 필요.
- **Phase 3 US1 T018**: `test_v4_unit.py` 에서 5-섹션 description 적용 도구
  대상 ORDERING 부재 assert 추가 — conditional skip (방식 B) 구현 트리거.
- **Phase 10 Polish**: 모든 도구 5-섹션 적용 완료 후 방식 A (전체 제거) 실행.
