# `kosmos-plugin-template` staging

> **In-tree staging area** — `examples/plugin-template-staging/` 의 컨텐츠는
> 외부 repo `kosmos-plugin-store/kosmos-plugin-template` 와 byte-equal 한
> source-of-truth 입니다 (T016).

이 staging 은 다음 명령의 emit 결과와 byte-equal:

```sh
uv run python -m kosmos.plugins.cli_init my_plugin \
  --tier live --layer 1 --no-pii \
  --out examples/plugin-template-staging
```

`cli_init.py` / `plugin-init.ts` 수정 후 위 명령으로 재생성하고 외부 repo 동기화 push.
