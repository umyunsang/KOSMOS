# Quickstart Timing Evidence (SC-001)

> 측정일: 2026-04-25
> 측정자: Lead 자동화 (umyunsang)
> 측정 환경: macOS 26 (Darwin 25.2.0), Python 3.12.11, uv 0.9.4, git 2.x
> 측정 위치: 로컬 (`/tmp/timing-test/`), fresh clone per run

## 측정 범위

`specs/1636-plugin-dx-5tier/quickstart.md` 의 9 단계 중 **자동화 가능한 단계 1-2** (clone + uv sync + scaffold pytest) 를 5회 fresh clone 으로 실측. 단계 3-9 (편집 + 로컬 검증 + push) 는 사람 시간이라 측정 대상이 아니며, quickstart.md 의 시간 예산 (총 31분) 으로 산정.

## 자동화된 측정값

| 단계 | 평균 (초) | quickstart.md 예산 | 격차 |
|---|---|---|---|
| clone | ~0.9 | (단계 1, 60초) | -98.5% |
| uv sync (cold cache) | ~0.3 ~ 0.6 | (단계 2 의 30초) | -99% |
| pytest (scaffold green) | ~1.4 | (단계 2 의 5초) | -72% |
| **단계 1+2 합계** | **~2.5초** | **240초** | **-99% (96× 여유)** |

> 노트: cold cache 측정에서도 `uv sync` 가 0.3초 이내였습니다 — host 머신에 이미 pydantic / httpx / pytest 가 캐시되어 있기 때문. 첫 사용자 첫 실행은 약 30 - 60 초 소요 예상 (quickstart.md 예산 그대로).

## Wall-clock 단계별 예산 (quickstart.md 정정)

```
단계 1 — 템플릿 복제              실측 1초 → 예산 60초 (안전 여유)
단계 2 — 의존성 + scaffold 테스트  실측 2초 → 예산 180초 (안전 여유)
단계 3 — 아키텍처 읽기            예산 300초 (사람 시간 — 측정 외)
단계 4 — manifest 편집            예산 180초 (사람 시간)
단계 5 — schema 편집              예산 300초 (사람 시간)
단계 6 — adapter 편집             예산 480초 (사람 시간)
단계 7 — 테스트 업데이트          예산 180초 (사람 시간)
단계 8 — 로컬 검증 (50-item)      예산 120초 (Phase 6 이후)
단계 9 — push + PR                예산 60초 (사람 시간)
```

총 31분 = 1860초. 자동화 단계 (1+2+8) 합계 2.5초 + ~120초 (50-item 검증, Phase 6 이후) → **사람 시간 1738초 (29분) 가 SC-001 success budget**.

## 재현 절차

```sh
cd /tmp && rm -rf timing-test && mkdir timing-test && cd timing-test
T0=$(python3 -c 'import time;print(time.time())')
git clone https://github.com/kosmos-plugin-store/kosmos-plugin-template.git my-plugin
T1=$(python3 -c 'import time;print(time.time())')
cd my-plugin
uv sync --quiet
T2=$(python3 -c 'import time;print(time.time())')
uv run pytest --no-header
T3=$(python3 -c 'import time;print(time.time())')
python3 -c "
clone=float('$T1')-float('$T0'); sync=float('$T2')-float('$T1')
test=float('$T3')-float('$T2'); total=float('$T3')-float('$T0')
print(f'clone={clone:.2f}s sync={sync:.2f}s test={test:.2f}s TOTAL={total:.2f}s')
"
```

## 검증 결과

```
clone:    0.85s
uv sync:  0.27s
pytest:   1.38s
TOTAL:    2.49s
```

scaffold pytest 결과:
```
collected 2 items
tests/test_adapter.py ..  [100%]
============================== 2 passed in 0.52s ===============================
```

## SC-001 판정

- ✅ 자동화 단계 (1+2): 2.49초 / 240초 예산 → **PASS**
- 📋 사람 단계 (3-7, 9): quickstart.md 예산 표 신뢰 → 후속 baseline 측정시 (T071) 외부 기여자 1인 onboarding 으로 검증 예정.
- 📋 단계 8 (50-item 로컬 검증): Phase 6 (US4) T047 / T051 완료 후 측정 가능 — 현 시점 N/A.

**총 결론**: SC-001 자동화 부분은 통과. 사람 단계는 Phase 6 / Phase 8 의 외부 기여자 baseline 측정으로 최종 확정.

## 발견된 issue 및 수정사항

quickstart timing 측정 도중 발견한 scaffold 회귀 3건은 모두 `cli_init.py` / `plugin-init.ts` 본문에 fix 후 외부 template repo 에 sync 완료:

1. **hatch wheel target 누락** — `[tool.hatch.build.targets.wheel] packages = ["plugin_<name>"]` 추가. `uv sync` 실패 → 0초 만에 abort 되던 이슈.
2. **TOOL eager construction** — `from kosmos.tools.models import GovAPITool` 가 모듈 import 시점에 실행되어 standalone 환경에서 `ModuleNotFoundError`. PEP 562 `__getattr__` lazy 전환.
3. **block_network autouse fixture 가 asyncio 차단** — AF_INET / AF_INET6 만 차단하도록 family-필터 적용. AF_UNIX socketpair 통과 → pytest-asyncio 동작.

세 fix 는 모두 cli_init / plugin-init 템플릿 정합성 PR 에 포함되어 외부 template repo 에 push 완료 (`kosmos-plugin-store/kosmos-plugin-template@main`).
