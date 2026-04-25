# SC-006 Self-Test Evidence

> 측정일: 2026-04-26
> 측정자: Lead 자동화 (umyunsang)
> 측정 환경: macOS 26 (Darwin 25.2.0), Python 3.12.11 (uv-managed venv)

## 측정 범위

SC-006: **모든 example plugin repo 가 fresh clone → `uv sync` → `uv run pytest` 흐름에서 자체 테스트를 녹색으로 통과** 한다.

```
SC-006 success criterion: every kosmos-plugin-store/<name> ships with
plugin-validation.yml that runs against itself in CI with 50/50 green;
verify all 4 example repos green via gh pr checks after creation.
```

이 evidence 는 SC-006 의 *로컬 self-test* 부분을 측정합니다 (`gh pr checks` 는 plugin-validation.yml 워크플로가 plugin-validation.yml@main 의 reusable 호출 기능 자체를 GitHub Actions runner 에서 검증할 때 측정).

## 결과 요약

| Repo | Tier | Layer | Tests | Result |
|---|---|---|---|---|
| `kosmos-plugin-seoul-subway` | live | 1 | 4 | ✅ 4 passed in 0.11s |
| `kosmos-plugin-post-office` | live | 1 | 4 | ✅ 4 passed in 0.12s |
| `kosmos-plugin-nts-homtax` | mock | 2 | 4 | ✅ 4 passed in 0.52s |
| `kosmos-plugin-nhis-check` | mock | 2 | 4 | ✅ 4 passed in 0.52s |

총: **16 tests / 16 passed (100%)** across 4 example repos.

## 재현 절차

```sh
cd /tmp && rm -rf sc006 && mkdir sc006 && cd sc006
for repo in kosmos-plugin-seoul-subway kosmos-plugin-post-office \
           kosmos-plugin-nts-homtax kosmos-plugin-nhis-check; do
  echo "=== $repo ==="
  git clone --quiet https://github.com/kosmos-plugin-store/$repo.git
  cd $repo
  uv sync --quiet
  uv run pytest --no-header -q
  cd ..
done
```

## SC-006 판정

- ✅ **로컬 pytest**: 4/4 repo 통과 (16 tests, 0 failures).
- ⏳ **CI plugin-validation.yml self-run**: GitHub Actions reusable workflow 호출은 첫 PR 생성 시 트리거 — 본 evidence 는 로컬 검증만 cover. CI 부분은 첫 외부 contributor PR 또는 `gh workflow run plugin-validation.yml --repo kosmos-plugin-store/kosmos-plugin-<name>` 수동 trigger 후 별도 측정 필요.

## 측정 도중 발견된 회귀

Live tier 두 repo (seoul-subway, post-office) 가 T023 fix 이전 cli_init 시점에 생성되어 다음 3건 패치 push 완료:

1. **pytest deps 누락** — `[project.optional-dependencies] test = [...]` 만 있고 main `dependencies` 에 `pytest` / `pytest-asyncio` 가 없어 `uv sync` 가 skip. 메인 deps 로 이동 + `[tool.pytest.ini_options] asyncio_mode = "auto"` 추가.
2. **`TOOL = _build_tool()` eager construction** — kosmos 가 venv 에 없는 standalone 환경에서 `from kosmos.tools.models import GovAPITool` 가 즉시 실행되어 ModuleNotFoundError. PEP 562 `__getattr__` lazy 패턴으로 전환.
3. **block_network fixture 가 AF_UNIX 차단** — pytest-asyncio 가 socketpair() 로 event loop 설정 시 RuntimeError. AF_INET / AF_INET6 만 차단하도록 family-필터 적용.

세 fix 는 다음 commit 으로 외부 repo 에 push 완료:
- `kosmos-plugin-store/kosmos-plugin-seoul-subway@078f93c`
- `kosmos-plugin-store/kosmos-plugin-post-office@665a1c9`

Mock tier 두 repo (nts-homtax, nhis-check) 는 T023 이후 cli_init 으로 생성되어 처음부터 4/4 통과.

## 향후 강화

- **plugin-validation.yml self-run**: `kosmos-plugin-store/<repo>` 의 `.github/workflows/plugin-validation.yml` 가 `umyunsang/KOSMOS@main` 의 reusable workflow 를 호출. PR 생성 또는 manual trigger 시 50/50 자동 검증.
- **catalog regeneration**: `scripts/regenerate_catalog.py` 가 `kosmos-plugin-store/index` 의 `index.json` 을 자동 갱신.
- **drift gate**: T051 meta-CI step 이 plugin-validation.yml 내부에서 50-row YAML + 모든 dotted path resolve 를 매번 검증.

## 결론

SC-006 의 자체 테스트 부분 ✅ PASS. CI reusable workflow self-run 검증은 별도 단계 (외부 contributor PR + maintainer 수동 trigger) 이며 deferred follow-up 로 추적.
