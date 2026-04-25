# `kosmos-plugin-template` staging

> **In-tree staging area** — `examples/plugin-template-staging/` 의 컨텐츠는
> 외부 repo `kosmos-plugin-store/kosmos-plugin-template` (`is_template: true`)
> 와 byte-equal 한 source-of-truth 입니다 (T016).

## 동기화

이 staging 은 다음 명령의 emit 결과와 byte-equal:

```sh
uv run python -m kosmos.plugins.cli_init my_plugin \
  --tier live --layer 1 --no-pii \
  --out examples/plugin-template-staging
```

`cli_init.py` / `plugin-init.ts` 의 템플릿 문자열을 수정한 경우 위 명령으로
staging 을 재생성하고 외부 repo 도 함께 push:

```sh
cp -R examples/plugin-template-staging/. /tmp/kosmos-plugin-template/
cd /tmp/kosmos-plugin-template
git add -A && git commit -m 'sync template'
git push
```

## "Use this template" 워크플로

GitHub 의 "Use this template" 는 literal copy — placeholder substitution 없음.
사용자는 다음 절차를 따릅니다:

1. <https://github.com/kosmos-plugin-store/kosmos-plugin-template> 의
   "Use this template" → 새 repo 생성 (`kosmos-plugin-<your-id>` 형식)
2. 클론 후 `my_plugin` 식별자 일괄 치환 (sed/git mv) — README.md 절차 참조
3. 또는 `kosmos plugin init <your_id> --non-interactive ...` 으로 처음부터 스캐폴딩.

추후 CI snapshot guard 추가 가능 (Phase 8).
