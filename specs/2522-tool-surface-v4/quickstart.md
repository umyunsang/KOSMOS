# Phase 1 Quickstart: Tool surface v4

**Date**: 2026-05-03
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Data Model**: [data-model.md](./data-model.md)

## Purpose

v4 의 단일 Epic 근본 해결 (13 도구 description 갈아엎기 + chain 의존성 제거 + 2 stub 진짜 구현 + 6 단순 fix + resolve_location 출력 표준화) 의 end-to-end 검증 가이드. 4 시민 발화 시나리오 (Layer 4 PTY smoke + pytest live) 통과가 v4 implementation 의 acceptance.

## Prerequisites

- UMMAYA worktree: `/Users/um-yunsang/UMMAYA-w-2522/` (이미 생성됨)
- `UMMAYA_DATA_GO_KR_API_KEY` (KMA / HIRA / NMC / NFA / MOHW / KOROAD 통합 키, `.env`)
- `UMMAYA_KAKAO_API_KEY` (resolve_location 의 Kakao 백엔드)
- `UMMAYA_FRIENDLI_TOKEN` (K-EXAONE on FriendliAI tier 1)
- `uv sync --frozen` 실행됨
- `bun --cwd tui install` 실행됨

## 4 시나리오 (User Story P1-P3 acceptance)

### 시나리오 1: 부산 날씨 (P1, Spec 2521 회귀 fix)

```bash
# pytest live
cd /Users/um-yunsang/UMMAYA-w-2522
uv run pytest tests/tools/kma/test_kma_current_observation_v4.py::test_busan_live -m live -v

# TUI PTY smoke
bash specs/2522-tool-surface-v4/scripts/smoke-busan-weather.expect

# 기대 결과:
# - kma_current_observation 단일 호출 (or autonomous turn 1 resolve_location, turn 2 KMA)
# - invalid_params 에러 0
# - 응답: 부산 광역 기온 / 강수 / 풍속
```

**검증 포인트**:
- description 의 17 광역시도 표 (`부산=(98,76)`) 보고 LLM 가 nx/ny 직접 채움
- 시민 발화 "부산 날씨" → 어댑터 input 의 nx=98, ny=76 정확
- UMMAYA 가 cross-domain chain 강제 안 함 (LLM 자율 결정)

### 시나리오 2: 강남구 병원 (P2)

```bash
uv run pytest tests/tools/hira/test_hospital_search_v4.py::test_gangnam_live -m live -v
bash specs/2522-tool-surface-v4/scripts/smoke-gangnam-hospital.expect

# 기대 결과:
# - LLM autonomous: turn 1 = resolve_location("강남구") → lat=37.517, lon=127.047
# - turn 2 = hira_hospital_search(yPos=37.517, xPos=127.047, radius=2000)
# - 병원 명단 응답
```

**검증 포인트**:
- HIRA 어댑터의 `_type=json` 정정 동작 (이전: type=json → XML)
- description 의 xPos/yPos 명명 quirk 명시 (xPos=경도, yPos=위도)
- `_type=json` param 의 정확한 wire format

### 시나리오 3: 서울 응급실 (P2)

```bash
uv run pytest tests/tools/nmc/test_emergency_search_v4.py::test_seoul_live -m live -v
bash specs/2522-tool-surface-v4/scripts/smoke-seoul-er.expect

# 기대 결과:
# - LLM autonomous: turn 1 = resolve_location("서울"), turn 2 = nmc_emergency_search(lat, lon, limit=3)
# - 응급실 명단 + 가용 병상 (hvgc, hvec) + 신선도 (hvidate)
```

**검증 포인트**:
- 한국어 query param URL encoding 자동화 (`httpx.params={}` dict — 이전 string interpolation 시 HTTP 400)
- Spec 023 freshness gate 동작 (5분 임계, stale_data 에러 정상)

### 시나리오 4: 임신·출산 복지 (P3, MOHW stub 진짜 구현)

```bash
uv run pytest tests/tools/mohw/test_welfare_eligibility_search_v4.py::test_imsin_chulsan_live -m live -v
bash specs/2522-tool-surface-v4/scripts/smoke-imsin-welfare.expect

# 기대 결과:
# - LLM 가 description 의 7 enum 표 보고 lifeArray=007 채움
# - mohw_welfare_eligibility_search(life_array="007", search_wrd="출산")
# - 어댑터 내부에서 callTp=L + srchKeyCode=003 자동 주입
# - 21건 이상 복지서비스 응답
```

**검증 포인트**:
- handle() 진짜 구현 (이전 Layer3GateViolation stub)
- camelCase wire param (`lifeArray`) — pydantic input 의 snake_case (`life_array`) 와 분리
- `callTp=L` + `srchKeyCode=003` 자동 주입 (LLM 에 노출 X)

## 추가 시나리오 (P3)

### 시나리오 5: 강남소방서 구급통계 (NFA stub 진짜 구현)

```bash
# NFA wire param 명세 P4 implementation 후 확정. 현재 placeholder.
uv run pytest tests/tools/nfa119/test_emergency_info_service_v4.py::test_gangnam_119_live -m live -v
```

### 시나리오 6: 서울 강남구 교통사고 (KOROAD 2+3-digit 정정)

```bash
uv run pytest tests/tools/koroad/test_accident_search_v4.py::test_gangnam_2023_live -m live -v
# 기대: siDo="11", guGun="680" (2+3 digit, 4-digit 1100/1116 X)
```

### 시나리오 7: chain 의존성 없이 자율 호출 (P2)

```bash
# models.py:577 정정 후 LLM 이 chain 강제받지 않는지 검증
uv run pytest tests/tools/test_chain_independence_v4.py -v
```

## TUI smoke setup

```bash
cd /Users/um-yunsang/UMMAYA-w-2522
bash scripts/tui-tmux-capture.sh \
  specs/2522-tool-surface-v4/frames-busan-weather \
  specs/2522-tool-surface-v4/scripts/smoke-busan-weather.expect

# Layer 4 PTY 는 매 시나리오 별 frames/ 디렉토리 생성
# Lead Opus 가 frames/*.txt 전수 read 로 검증 (memory feedback_pty_log_full_inspection)
```

## Acceptance criteria

| 시나리오 | pytest live | TUI smoke | docs/api 동기화 |
|---|---|---|---|
| 부산 날씨 (P1) | PASS | frames-busan-weather/ | docs/api/kma/current_observation.md |
| 강남구 병원 (P2) | PASS | frames-gangnam-hospital/ | docs/api/hira/hospital_search.md |
| 서울 응급실 (P2) | PASS | frames-seoul-er/ | docs/api/nmc/emergency_search.md |
| 임신·출산 복지 (P3) | PASS | frames-imsin-welfare/ | docs/api/mohw/welfare_eligibility_search.md |
| 강남소방서 (P3) | PASS | frames-gangnam-119/ | docs/api/nfa119/emergency_info_service.md |
| 서울 강남구 사고 (P3) | PASS | frames-gangnam-accident/ | docs/api/koroad/accident_search.md |
| chain 독립 (P2) | PASS | (별도 unit 테스트) | (N/A — code-only) |

전 7 시나리오 PASS = SC-001~SC-008 충족 = v4 acceptance.
