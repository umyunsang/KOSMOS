# `kosmos-plugin-template` staging

> **이 디렉토리는 in-tree staging area 입니다.** 외부 GitHub repo
> `kosmos-plugin-store/kosmos-plugin-template` 으로 push 되기 전, 컨텐츠를
> KOSMOS repo 내부에서 review 하기 위한 임시 위치입니다 (T016).

## 왜 staging 인가?

Migration tree § B8 에 따라 플러그인 5-tier DX 의 Template (Tier 1) 은
독립 repo (`kosmos-plugin-store/kosmos-plugin-template`) 에 위치합니다.
하지만 `kosmos-plugin-store` GitHub org 는 무료 org 생성 정책상
GitHub 웹 UI 에서만 생성 가능 (`gh` CLI 미지원).

이 staging 폴더는 다음 목적으로 존재합니다:

1. **Review** — 외부 repo 가 만들어지기 전, 템플릿 컨텐츠를 in-tree 로
   검토 가능.
2. **Single source of truth** — `src/kosmos/plugins/cli_init.py` 와
   `tui/src/commands/plugin-init.ts` 의 emit 결과가 이 staging 과
   byte-equal 한지 CI 에서 검증 가능 (snapshot 패턴).
3. **One-shot migration** — org 생성 후 다음 명령으로 외부 repo 부트스트랩
   가능:
   ```sh
   gh repo create kosmos-plugin-store/kosmos-plugin-template \
     --public --license=apache-2.0 \
     --source=examples/plugin-template-staging --push
   ```

## 컨텐츠 동기화

이 staging 은 `kosmos-plugin-init my_plugin --tier live --layer 1 --no-pii` 의
emit 결과와 byte-equal 합니다. 동기화 절차:

```sh
rm -rf examples/plugin-template-staging
uv run python -m kosmos.plugins.cli_init my_plugin \
  --tier live --layer 1 --no-pii \
  --out examples/plugin-template-staging
# 이 README.staging.md 는 위 명령의 결과에 포함되지 않으므로 별도 보관.
```

`cli_init.py` / `plugin-init.ts` 의 템플릿 문자열을 수정한 경우 위 절차로
staging 을 재생성하세요.

## "Use this template" 사용법 (외부 repo 가 생성된 후)

GitHub 의 "Use this template" 버튼은 literal copy — placeholder substitution
없음. 따라서 사용자는 다음 절차를 따릅니다:

1. <https://github.com/kosmos-plugin-store/kosmos-plugin-template> 의
   "Use this template" → "Create a new repository"
2. 새 repo 이름: `kosmos-plugin-<your-plugin-name>` (예: `kosmos-plugin-busan-bike`)
3. 로컬 클론 후 placeholder 이름 (`my_plugin`) 을 일괄 치환:
   ```sh
   git clone https://github.com/<your-org>/kosmos-plugin-busan-bike
   cd kosmos-plugin-busan-bike

   # 디렉토리 + 식별자 일괄 rename
   git mv plugin_my_plugin plugin_busan_bike
   sed -i '' 's/my_plugin/busan_bike/g' \
     manifest.yaml \
     plugin_busan_bike/*.py \
     tests/test_adapter.py \
     tests/fixtures/*.json \
     pyproject.toml \
     README.ko.md README.en.md
   git mv tests/fixtures/plugin.my_plugin.lookup.json \
          tests/fixtures/plugin.busan_bike.lookup.json
   ```
4. `manifest.yaml` 의 search hint / Layer / PII 필드 자신의 플러그인에 맞게 수정.
5. `uv sync && uv run pytest` 로 녹색 확인.
6. PR 으로 push.

대안: `kosmos plugin init busan_bike --non-interactive --tier live --layer 1 --no-pii`
로 새 디렉토리에 처음부터 스캐폴딩하면 rename 절차 불필요 (TUI 또는 Python
fallback 모두 사용 가능).

## 다음 단계 (CI 동기화)

추후 `tests/snapshots/test_template_staging_parity.py` 를 추가해
`cli_init.py` / `plugin-init.ts` 의 emit 과 이 staging 이 drift 하면 CI 가
fail 하도록 가드 가능. (Phase 8 polish 단계)
