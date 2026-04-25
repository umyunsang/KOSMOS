# SC-008 Baseline Evidence

> 측정일: 2026-04-26
> 측정자: Lead 자동화 (umyunsang)

## SC-008 정의

```
SC-008 success criterion: external-contributor count post-merge ≥ 1
within 3 months of plugin DX 5-tier shipping. Baseline: 0 external
contributors at merge time.
```

## 현재 baseline (Pre-merge)

`umyunsang/KOSMOS` repo 의 `main` 브랜치 기여자 (2026-04-26 기준):

```
$ git log --format='%an' main | sort -u
Copilot
dependabot[bot]
umyunsang
```

- **Human external contributors**: **0** (Copilot은 PR 리뷰 봇, dependabot은 의존성 업데이트 봇 — 둘 다 자동화 도구이며 plugin 작성과 무관).
- **Plugin-store external repos** (`kosmos-plugin-store/<name>`) commit 작성자:
  - `kosmos-plugin-template`: umyunsang only
  - `kosmos-plugin-seoul-subway`: umyunsang only
  - `kosmos-plugin-post-office`: umyunsang only
  - `kosmos-plugin-nts-homtax`: umyunsang only
  - `kosmos-plugin-nhis-check`: umyunsang only
  - `kosmos-plugin-store/index`: umyunsang only

**Baseline: 0** external contributors at the moment Spec 1636 P5 ships.

## 측정 절차 (3개월 후 재측정)

```sh
# 측정일 = merge_date + 90 days
MERGE_DATE="2026-04-XX"  # actual PR merge date
SINCE="${MERGE_DATE} +0 days"
UNTIL="${MERGE_DATE} +90 days"

# Plugin-store repos
for repo in $(gh repo list kosmos-plugin-store --json name --limit 200 --jq '.[].name'); do
  echo "=== $repo ==="
  gh api repos/kosmos-plugin-store/$repo/commits \
    --paginate \
    --jq '.[] | select(.author.login != null) | .author.login' \
    | sort -u
done

# KOSMOS repo
gh api repos/umyunsang/KOSMOS/commits \
  --paginate \
  --jq '.[].author.login' \
  | sort -u
```

## SC-008 PASS 기준

- 3개월 내 (2026-04-XX → 2026-07-XX) 위 측정에서 **umyunsang 외 1인 이상의 GitHub 사용자** 가 다음 중 하나를 수행:
  - `kosmos-plugin-store/<name>` 신규 repo 생성 (`gh repo create --template kosmos-plugin-store/kosmos-plugin-template`).
  - 기존 plugin repo 에 PR merge.
  - `umyunsang/KOSMOS` 의 `docs/plugins/`, `src/kosmos/plugins/`, `tests/fixtures/plugin_validation/` 영역에 PR merge.

## 추적 방법

`scripts/regenerate_catalog.py` 가 plugin-store 의 모든 repo 를 walk 하여 `index.json` 을 갱신. 새 repo 가 자동 발견되며, repo 의 owner / contributor 가 GitHub UI 에서 확인 가능.

추가 자동화: 향후 `gh-actions/external-contributor-count.yml` (deferred — 본 epic 범위 외) workflow 가 매월 1일 위 측정을 자동 실행 + Discussion 에 결과 post 가능.

## 결론

**Baseline: 0 external contributors** at 2026-04-26. Re-measure 90 days post-merge for SC-008 verdict.
